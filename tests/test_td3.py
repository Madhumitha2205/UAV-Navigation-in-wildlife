"""Unit tests for TD3 networks, action bounds, training updates, reward function, and checkpoints."""

from pathlib import Path
import numpy as np
import torch
import pytest

from backend.intelligent_control.actor_network import ActorNetwork
from backend.intelligent_control.config import TD3Config, VehicleLimitsConfig
from backend.intelligent_control.critic_network import TwinCriticNetwork
from backend.intelligent_control.replay_buffer import ReplayBuffer
from backend.intelligent_control.reward_function import NavigationRewardFunction
from backend.intelligent_control.rl_environment import LightweightUAVEnv
from backend.intelligent_control.td3_agent import TD3Agent


def test_actor_and_critic_tensor_shapes():
    actor = ActorNetwork(state_dim=12, action_dim=3, hidden_dim=64, max_action=(5.0, 5.0, 2.0))
    critic = TwinCriticNetwork(state_dim=12, action_dim=3, hidden_dim=64)

    batch_s = torch.randn(8, 12)
    batch_a = actor(batch_s)
    assert batch_a.shape == (8, 3)
    assert torch.all(torch.abs(batch_a[:, :2]) <= 5.0 + 1e-5)
    assert torch.all(torch.abs(batch_a[:, 2]) <= 2.0 + 1e-5)

    q1, q2 = critic(batch_s, batch_a)
    assert q1.shape == (8, 1)
    assert q2.shape == (8, 1)
    q1_only = critic.q1(batch_s, batch_a)
    assert torch.allclose(q1, q1_only)


def test_td3_action_bounds_and_delayed_update(tmp_path: Path):
    cfg = TD3Config(state_dim=12, action_dim=3, hidden_dim=32, batch_size=8, policy_freq=2, seed=42)
    limits = VehicleLimitsConfig(max_velocity_xy_mps=4.5, max_velocity_z_mps=1.8)
    agent = TD3Agent(td3_config=cfg, limits_config=limits)
    assert not agent.is_trained

    state = np.random.uniform(-1.0, 1.0, size=(12,)).astype(np.float32)
    act = agent.select_action(state, add_noise=True)
    assert act.shape == (3,)
    assert abs(act[0]) <= 4.5 + 1e-5
    assert abs(act[1]) <= 4.5 + 1e-5
    assert abs(act[2]) <= 1.8 + 1e-5

    buf = ReplayBuffer(state_dim=12, action_dim=3, max_size=100, seed=42)
    for _ in range(16):
        s = np.random.uniform(-1, 1, size=12).astype(np.float32)
        a = np.random.uniform(-1, 1, size=3).astype(np.float32)
        ns = np.random.uniform(-1, 1, size=12).astype(np.float32)
        buf.add(s, a, ns, reward=1.0, done=False)

    # First step (total_it=1): critic updates, actor delayed (actor_loss == 0.0)
    step1 = agent.train_step(buf)
    assert step1["updated"] == 1.0
    assert step1["actor_loss"] == 0.0

    # Second step (total_it=2): both critic and actor update
    step2 = agent.train_step(buf)
    assert step2["updated"] == 1.0
    assert step2["actor_loss"] != 0.0
    assert agent.is_trained

    # Save and reload checkpoint
    ckpt_file = tmp_path / "td3_test.pt"
    agent.save_checkpoint(ckpt_file, extra_metadata={"test_run": True})
    assert ckpt_file.exists()
    assert ckpt_file.with_suffix(".meta.json").exists()

    reloaded = TD3Agent(td3_config=cfg, limits_config=limits)
    reloaded.load_checkpoint(ckpt_file)
    assert reloaded.is_trained
    assert reloaded.total_it == 2
    assert np.allclose(
        agent.select_action(state, add_noise=False),
        reloaded.select_action(state, add_noise=False),
        atol=1e-6,
    )


def test_deterministic_reward_and_anti_stationary():
    reward_fn = NavigationRewardFunction(max_speed_mps=5.0)

    # Moving closer to target in clear surroundings yields positive progress reward
    r_prog = reward_fn.compute(
        prev_distance_to_target_m=20.0,
        curr_distance_to_target_m=18.5,
        action_vel_xyz=(3.0, 0.0, 0.0),
        prev_action_vel_xyz=(2.8, 0.0, 0.0),
        closest_obstacle_dist_m=15.0,
    )
    assert r_prog.progress_term > 0.0
    assert r_prog.proximity_term == 0.0
    assert r_prog.total_reward > 0.0

    # Staying stationary away from target incurs step + stationary penalty (< 0)
    r_stat = reward_fn.compute(
        prev_distance_to_target_m=20.0,
        curr_distance_to_target_m=20.0,
        action_vel_xyz=(0.0, 0.0, 0.0),
        prev_action_vel_xyz=(0.0, 0.0, 0.0),
        closest_obstacle_dist_m=15.0,
    )
    assert r_stat.total_reward < -0.5

    # Collision incurs heavy negative penalty
    r_col = reward_fn.compute(
        prev_distance_to_target_m=10.0,
        curr_distance_to_target_m=9.8,
        action_vel_xyz=(2.0, 0.0, 0.0),
        prev_action_vel_xyz=(2.0, 0.0, 0.0),
        closest_obstacle_dist_m=0.0,
        has_collided=True,
    )
    assert r_col.collision_term == -100.0
    assert r_col.total_reward < -90.0


def test_lightweight_env_state_dimensions_and_termination():
    env = LightweightUAVEnv(seed=99)
    state = env.reset(start_pos=(0.0, 0.0, 15.0), waypoints=[(2.0, 0.0, 15.0)])
    assert state.shape == (12,)

    # Step directly toward nearby target until reached
    for _ in range(15):
        state, reward, done, info = env.step((4.0, 0.0, 0.0))
        assert state.shape == (12,)
        if done:
            break
    assert info["completed_mission"] is True
