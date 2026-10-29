"""TD3 Actor Network (PyTorch).

Maps the 12-dimensional normalized navigation state vector to bounded 3D continuous
velocity commands [vx, vy, vz] using `tanh` activation scaled by vehicle speed limits.
"""

from __future__ import annotations

from typing import Sequence
import torch
import torch.nn as nn


class ActorNetwork(nn.Module):
    """Deterministic policy network for TD3 local UAV velocity control."""

    def __init__(
        self,
        state_dim: int = 12,
        action_dim: int = 3,
        hidden_dim: int = 128,
        max_action: Sequence[float] = (5.0, 5.0, 2.0),
    ) -> None:
        super().__init__()
        self.state_dim = int(state_dim)
        self.action_dim = int(action_dim)
        self.hidden_dim = int(hidden_dim)

        max_act_tensor = torch.as_tensor(max_action, dtype=torch.float32)
        if max_act_tensor.numel() == 1:
            max_act_tensor = max_act_tensor.repeat(self.action_dim)
        self.register_buffer("max_action", max_act_tensor.view(1, self.action_dim))

        self.net = nn.Sequential(
            nn.Linear(self.state_dim, self.hidden_dim),
            nn.LayerNorm(self.hidden_dim),
            nn.ReLU(),
            nn.Linear(self.hidden_dim, self.hidden_dim),
            nn.LayerNorm(self.hidden_dim),
            nn.ReLU(),
            nn.Linear(self.hidden_dim, self.action_dim),
            nn.Tanh(),
        )
        self._init_weights()

    def _init_weights(self) -> None:
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.orthogonal_(m.weight, gain=1.0)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
        # Small final layer initialization for smooth initial actions
        last_linear = self.net[-2]
        if isinstance(last_linear, nn.Linear):
            nn.init.uniform_(last_linear.weight, -3e-3, 3e-3)
            nn.init.uniform_(last_linear.bias, -3e-3, 3e-3)

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        if state.dim() == 1:
            state = state.unsqueeze(0)
            out = self.net(state) * self.max_action
            return out.squeeze(0)
        return self.net(state) * self.max_action
