"""TD3 Twin Critic Networks (PyTorch).

Implements two independent Q-value networks Q1(s, a) and Q2(s, a) to mitigate
overestimation bias in continuous control (clipped double Q-learning).
"""

from __future__ import annotations

from typing import Tuple
import torch
import torch.nn as nn


class TwinCriticNetwork(nn.Module):
    """Two independent Q-networks for TD3."""

    def __init__(
        self,
        state_dim: int = 12,
        action_dim: int = 3,
        hidden_dim: int = 128,
    ) -> None:
        super().__init__()
        self.state_dim = int(state_dim)
        self.action_dim = int(action_dim)
        self.hidden_dim = int(hidden_dim)
        in_dim = self.state_dim + self.action_dim

        self.q1_net = nn.Sequential(
            nn.Linear(in_dim, self.hidden_dim),
            nn.LayerNorm(self.hidden_dim),
            nn.ReLU(),
            nn.Linear(self.hidden_dim, self.hidden_dim),
            nn.LayerNorm(self.hidden_dim),
            nn.ReLU(),
            nn.Linear(self.hidden_dim, 1),
        )

        self.q2_net = nn.Sequential(
            nn.Linear(in_dim, self.hidden_dim),
            nn.LayerNorm(self.hidden_dim),
            nn.ReLU(),
            nn.Linear(self.hidden_dim, self.hidden_dim),
            nn.LayerNorm(self.hidden_dim),
            nn.ReLU(),
            nn.Linear(self.hidden_dim, 1),
        )
        self._init_weights()

    def _init_weights(self) -> None:
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.orthogonal_(m.weight, gain=1.0)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, state: torch.Tensor, action: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """Compute both Q1(s, a) and Q2(s, a)."""
        if state.dim() == 1:
            state = state.unsqueeze(0)
        if action.dim() == 1:
            action = action.unsqueeze(0)
        sa = torch.cat([state, action], dim=-1)
        return self.q1_net(sa), self.q2_net(sa)

    def q1(self, state: torch.Tensor, action: torch.Tensor) -> torch.Tensor:
        """Compute only Q1(s, a) for delayed actor policy gradient updates."""
        if state.dim() == 1:
            state = state.unsqueeze(0)
        if action.dim() == 1:
            action = action.unsqueeze(0)
        sa = torch.cat([state, action], dim=-1)
        return self.q1_net(sa)
