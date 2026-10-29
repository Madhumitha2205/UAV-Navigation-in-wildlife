"""Experience Replay Buffer for Off-Policy TD3 Training.

Uses pre-allocated contiguous float32 NumPy arrays for low RAM footprint
and deterministic seeded mini-batch sampling.
"""

from __future__ import annotations

from typing import Sequence, Tuple
import numpy as np
import torch


class ReplayBuffer:
    """Fixed-capacity circular experience replay buffer."""

    def __init__(
        self,
        state_dim: int = 12,
        action_dim: int = 3,
        max_size: int = 25000,
        seed: int = 42,
        device: str = "cpu",
    ) -> None:
        if max_size <= 0:
            raise ValueError("max_size must be positive.")
        self.state_dim = int(state_dim)
        self.action_dim = int(action_dim)
        self.max_size = int(max_size)
        self.device = torch.device(device)
        self.rng = np.random.default_rng(seed)

        self.ptr = 0
        self.size = 0

        self.states = np.zeros((self.max_size, self.state_dim), dtype=np.float32)
        self.actions = np.zeros((self.max_size, self.action_dim), dtype=np.float32)
        self.next_states = np.zeros((self.max_size, self.state_dim), dtype=np.float32)
        self.rewards = np.zeros((self.max_size, 1), dtype=np.float32)
        self.dones = np.zeros((self.max_size, 1), dtype=np.float32)

    def __len__(self) -> int:
        return self.size

    def add(
        self,
        state: Sequence[float],
        action: Sequence[float],
        next_state: Sequence[float],
        reward: float,
        done: bool,
    ) -> None:
        """Insert a single transition (s, a, s', r, done) into the circular buffer."""
        s = np.asarray(state, dtype=np.float32)
        a = np.asarray(action, dtype=np.float32)
        ns = np.asarray(next_state, dtype=np.float32)
        if s.shape != (self.state_dim,) or ns.shape != (self.state_dim,):
            raise ValueError(f"Expected state shape ({self.state_dim},), got {s.shape} and {ns.shape}.")
        if a.shape != (self.action_dim,):
            raise ValueError(f"Expected action shape ({self.action_dim},), got {a.shape}.")

        self.states[self.ptr] = s
        self.actions[self.ptr] = a
        self.next_states[self.ptr] = ns
        self.rewards[self.ptr, 0] = float(reward)
        self.dones[self.ptr, 0] = 1.0 if done else 0.0

        self.ptr = (self.ptr + 1) % self.max_size
        self.size = min(self.size + 1, self.max_size)

    def sample(
        self, batch_size: int
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """Sample a batch of transitions as PyTorch tensors on the configured device."""
        if self.size == 0:
            raise RuntimeError("Cannot sample from an empty ReplayBuffer.")
        if batch_size <= 0:
            raise ValueError("batch_size must be positive.")

        indices = self.rng.integers(0, self.size, size=int(batch_size))
        return (
            torch.as_tensor(self.states[indices], device=self.device),
            torch.as_tensor(self.actions[indices], device=self.device),
            torch.as_tensor(self.next_states[indices], device=self.device),
            torch.as_tensor(self.rewards[indices], device=self.device),
            torch.as_tensor(self.dones[indices], device=self.device),
        )
