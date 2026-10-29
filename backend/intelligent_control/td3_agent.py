"""Twin Delayed Deep Deterministic Policy Gradient (TD3) Agent in PyTorch.

Implements:
- Actor network & target actor
- Twin critic networks (Q1, Q2) & target critics
- Target policy smoothing regularization
- Delayed policy (actor) updates every `policy_freq` critic updates
- Polyak soft target updates (`tau`)
- Explicit `is_trained` metadata tracking so an untrained model cannot silently control AirSim
- Full checkpoint saving and loading with configuration provenance
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, Optional, Sequence
import numpy as np
import torch
import torch.nn.functional as F

from backend.intelligent_control.actor_network import ActorNetwork
from backend.intelligent_control.config import TD3Config, VehicleLimitsConfig
from backend.intelligent_control.critic_network import TwinCriticNetwork
from backend.intelligent_control.replay_buffer import ReplayBuffer


class TD3Agent:
    """TD3 reinforcement learning agent for continuous 3D UAV velocity control."""

    def __init__(
        self,
        td3_config: Optional[TD3Config] = None,
        limits_config: Optional[VehicleLimitsConfig] = None,
        device: str = "cpu",
    ) -> None:
        self.cfg = td3_config or TD3Config()
        self.limits = limits_config or VehicleLimitsConfig()
        self.device = torch.device(device)

        self.set_seed(self.cfg.seed)

        self.max_action_np = np.array(
            [
                self.limits.max_velocity_xy_mps,
                self.limits.max_velocity_xy_mps,
                self.limits.max_velocity_z_mps,
            ],
            dtype=np.float32,
        )
        self.max_action_tensor = torch.as_tensor(self.max_action_np, device=self.device).view(1, -1)

        self.actor = ActorNetwork(
            state_dim=self.cfg.state_dim,
            action_dim=self.cfg.action_dim,
            hidden_dim=self.cfg.hidden_dim,
            max_action=self.max_action_np,
        ).to(self.device)
        self.actor_target = copy.deepcopy(self.actor).to(self.device)
        self.actor_optimizer = torch.optim.Adam(self.actor.parameters(), lr=self.cfg.actor_lr)

        self.critic = TwinCriticNetwork(
            state_dim=self.cfg.state_dim,
            action_dim=self.cfg.action_dim,
            hidden_dim=self.cfg.hidden_dim,
        ).to(self.device)
        self.critic_target = copy.deepcopy(self.critic).to(self.device)
        self.critic_optimizer = torch.optim.Adam(self.critic.parameters(), lr=self.cfg.critic_lr)

        self.total_it: int = 0
        self.trained_episodes: int = 0
        self.is_trained: bool = False
        self.training_mode: bool = True

    def set_seed(self, seed: int) -> None:
        self.seed = int(seed)
        self.rng = np.random.default_rng(self.seed)
        torch.manual_seed(self.seed)

    def set_eval_mode(self, eval_mode: bool = True) -> None:
        """Toggle between evaluation mode (deterministic) and training mode."""
        self.training_mode = not eval_mode
        if eval_mode:
            self.actor.eval()
            self.critic.eval()
        else:
            self.actor.train()
            self.critic.train()

    def select_action(
        self,
        state: Sequence[float],
        add_noise: bool = False,
        noise_scale: Optional[float] = None,
    ) -> np.ndarray:
        """Select a bounded 3D velocity command [vx, vy, vz] for a 12D state vector."""
        s = np.asarray(state, dtype=np.float32)
        if s.shape != (self.cfg.state_dim,):
            raise ValueError(f"Expected state dimension ({self.cfg.state_dim},), got {s.shape}.")

        state_tensor = torch.as_tensor(s, dtype=torch.float32, device=self.device).unsqueeze(0)
        with torch.no_grad():
            action = self.actor(state_tensor).cpu().numpy().flatten()

        if add_noise:
            sigma = float(noise_scale if noise_scale is not None else self.cfg.exploration_noise)
            noise = self.rng.normal(0.0, sigma, size=self.cfg.action_dim).astype(np.float32) * self.max_action_np
            action = action + noise

        return np.clip(action, -self.max_action_np, self.max_action_np).astype(np.float32)

    def train_step(
        self,
        replay_buffer: ReplayBuffer,
        batch_size: Optional[int] = None,
    ) -> Dict[str, float]:
        """Perform one TD3 optimization step from the replay buffer."""
        bsize = int(batch_size if batch_size is not None else self.cfg.batch_size)
        if len(replay_buffer) < bsize:
            return {"critic_loss": 0.0, "actor_loss": 0.0, "updated": 0.0}

        self.total_it += 1
        state, action, next_state, reward, done = replay_buffer.sample(bsize)

        with torch.no_grad():
            # Target policy smoothing: add clipped Gaussian noise scaled by max_action
            raw_noise = torch.randn_like(action) * self.cfg.policy_noise
            clipped_noise = torch.clamp(raw_noise, -self.cfg.noise_clip, self.cfg.noise_clip)
            scaled_noise = clipped_noise * self.max_action_tensor

            next_action = torch.clamp(
                self.actor_target(next_state) + scaled_noise,
                -self.max_action_tensor,
                self.max_action_tensor,
            )

            # Clipped double Q-learning target
            target_q1, target_q2 = self.critic_target(next_state, next_action)
            target_q = torch.min(target_q1, target_q2)
            target_q = reward + (1.0 - done) * self.cfg.gamma * target_q

        current_q1, current_q2 = self.critic(state, action)
        critic_loss = F.mse_loss(current_q1, target_q) + F.mse_loss(current_q2, target_q)

        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.critic.parameters(), max_norm=1.0)
        self.critic_optimizer.step()

        actor_loss_val = 0.0
        # Delayed policy updates
        if self.total_it % self.cfg.policy_freq == 0:
            actor_loss = -self.critic.q1(state, self.actor(state)).mean()
            self.actor_optimizer.zero_grad()
            actor_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.actor.parameters(), max_norm=1.0)
            self.actor_optimizer.step()
            actor_loss_val = float(actor_loss.item())

            # Soft update target networks
            self._soft_update(self.critic, self.critic_target, self.cfg.tau)
            self._soft_update(self.actor, self.actor_target, self.cfg.tau)

        self.is_trained = True
        return {
            "critic_loss": float(critic_loss.item()),
            "actor_loss": actor_loss_val,
            "updated": 1.0,
        }

    @staticmethod
    def _soft_update(source: torch.nn.Module, target: torch.nn.Module, tau: float) -> None:
        for param, target_param in zip(source.parameters(), target.parameters()):
            target_param.data.copy_(tau * param.data + (1.0 - tau) * target_param.data)

    def save_checkpoint(
        self,
        checkpoint_path: str | Path,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Save TD3 model weights, optimizer states, training flags, and configuration."""
        path = Path(checkpoint_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "actor_state_dict": self.actor.state_dict(),
            "actor_target_state_dict": self.actor_target.state_dict(),
            "critic_state_dict": self.critic.state_dict(),
            "critic_target_state_dict": self.critic_target.state_dict(),
            "actor_optimizer_state_dict": self.actor_optimizer.state_dict(),
            "critic_optimizer_state_dict": self.critic_optimizer.state_dict(),
            "total_it": self.total_it,
            "trained_episodes": self.trained_episodes,
            "is_trained": self.is_trained,
            "td3_config": self.cfg.__dict__,
            "limits_config": self.limits.__dict__,
            "extra_metadata": extra_metadata or {},
        }
        torch.save(payload, path)

        # Also save a human-readable companion metadata JSON file alongside the checkpoint
        meta_path = path.with_suffix(".meta.json")
        meta = {
            "checkpoint_file": path.name,
            "total_it": self.total_it,
            "trained_episodes": self.trained_episodes,
            "is_trained": self.is_trained,
            "td3_config": self.cfg.__dict__,
            "limits_config": self.limits.__dict__,
            "extra_metadata": extra_metadata or {},
        }
        with meta_path.open("w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        return path

    def load_checkpoint(self, checkpoint_path: str | Path) -> Dict[str, Any]:
        """Load TD3 model weights and training metadata from checkpoint file."""
        path = Path(checkpoint_path)
        if not path.exists():
            raise FileNotFoundError(f"TD3 checkpoint not found: {path}")

        payload = torch.load(path, map_location=self.device, weights_only=False)
        self.actor.load_state_dict(payload["actor_state_dict"])
        self.actor_target.load_state_dict(payload["actor_target_state_dict"])
        self.critic.load_state_dict(payload["critic_state_dict"])
        self.critic_target.load_state_dict(payload["critic_target_state_dict"])
        if "actor_optimizer_state_dict" in payload:
            self.actor_optimizer.load_state_dict(payload["actor_optimizer_state_dict"])
        if "critic_optimizer_state_dict" in payload:
            self.critic_optimizer.load_state_dict(payload["critic_optimizer_state_dict"])

        self.total_it = int(payload.get("total_it", 0))
        self.trained_episodes = int(payload.get("trained_episodes", 0))
        self.is_trained = bool(payload.get("is_trained", False))
        return payload
