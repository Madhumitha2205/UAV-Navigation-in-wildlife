"""Unit tests for ReplayBuffer insertion, capacity wrap-around, and sampling."""

import numpy as np
import pytest

from backend.intelligent_control.replay_buffer import ReplayBuffer


def test_replay_buffer_insert_and_sample():
    buf = ReplayBuffer(state_dim=12, action_dim=3, max_size=50, seed=123)
    assert len(buf) == 0

    for i in range(30):
        s = np.full(12, float(i), dtype=np.float32)
        a = np.array([0.1 * i, -0.1 * i, 0.05], dtype=np.float32)
        ns = np.full(12, float(i + 1), dtype=np.float32)
        buf.add(s, a, ns, reward=float(i) * 0.5, done=(i == 29))

    assert len(buf) == 30
    states, actions, next_states, rewards, dones = buf.sample(batch_size=16)
    assert states.shape == (16, 12)
    assert actions.shape == (16, 3)
    assert next_states.shape == (16, 12)
    assert rewards.shape == (16, 1)
    assert dones.shape == (16, 1)


def test_replay_buffer_circular_overwrite():
    buf = ReplayBuffer(state_dim=12, action_dim=3, max_size=10, seed=7)
    for i in range(15):
        buf.add(np.zeros(12), np.zeros(3), np.ones(12), reward=float(i), done=False)
    assert len(buf) == 10
    assert buf.ptr == 5


def test_replay_buffer_dimension_validation():
    buf = ReplayBuffer(state_dim=12, action_dim=3, max_size=10)
    with pytest.raises(ValueError, match="Expected state shape"):
        buf.add(np.zeros(9), np.zeros(3), np.zeros(12), 0.0, False)
    with pytest.raises(ValueError, match="Expected action shape"):
        buf.add(np.zeros(12), np.zeros(2), np.zeros(12), 0.0, False)
