
"""Adaptive Fuzzy Logic (AFL) Safety Layer for Reactive UAV Obstacle Avoidance.

Note on Research Integrity:
AFL is a reactive safety heuristic that blends TD3's desired velocity command with
a geometric repulsion and braking response based on distance and closing speed.
It does NOT provide a formal mathematical collision-avoidance guarantee under arbitrary
multi-obstacle dynamics or actuator saturation.

Fuzzy Variables & Membership Functions:
1. Obstacle Distance `d` (metres):
   - `CRITICAL`: Z-shaped / left-shoulder membership = 1.0 for d <= d_crit (default 2.5 m),
     decreasing linearly to 0.0 at d_near (default 4.25 m).
   - `NEAR`: Triangular membership centered at d_near = 0.5 * (d_crit + d_safe),
     rising from 0.0 at d_crit to 1.0 at d_near, falling to 0.0 at d_safe (default 6.0 m).
   - `SAFE`: S-shaped / right-shoulder membership = 0.0 for d <= d_near,
     rising linearly to 1.0 at d >= d_safe.

2. Closing Speed `v_close` (m/s, positive when approaching obstacle):
   - `RECEDING_OR_SLOW`: 1.0 for v_close <= v_slow (0.5 m/s), falling to 0.0 at v_mod (2.0 m/s).
   - `MODERATE`: Triangular centered at v_mod (2.0 m/s) between v_slow (0.5) and v_fast (3.5).
   - `FAST`: 0.0 for v_close <= v_mod (2.0 m/s), rising to 1.0 at v_close >= v_fast (3.5 m/s).

Fuzzy Rule Base (9 Mamdani/Sugeno rules mapping to singleton danger levels in [0, 1]):
- R1: IF d is CRITICAL AND v_close is FAST             THEN Danger = EXTREME (1.00)
- R2: IF d is CRITICAL AND v_close is MODERATE         THEN Danger = VERY_HIGH (0.92)
- R3: IF d is CRITICAL AND v_close is RECEDING_OR_SLOW THEN Danger = HIGH (0.80)
- R4: IF d is NEAR     AND v_close is FAST             THEN Danger = HIGH (0.75)
- R5: IF d is NEAR     AND v_close is MODERATE         THEN Danger = MEDIUM (0.50)
- R6: IF d is NEAR     AND v_close is RECEDING_OR_SLOW THEN Danger = LOW (0.25)
- R7: IF d is SAFE     AND v_close is FAST             THEN Danger = CAUTION (0.10)
- R8: IF d is SAFE     AND v_close is MODERATE         THEN Danger = CLEAR (0.00)
- R9: IF d is SAFE     AND v_close is RECEDING_OR_SLOW THEN Danger = CLEAR (0.00)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Sequence, Tuple

import numpy as np

from backend.intelligent_control.airsim_sensors import ObstacleObservation
from backend.intelligent_control.config import SafetyConfig, VehicleLimitsConfig


@dataclass
class SafetyInterventionResult:
    """Structured output returned by the Adaptive Fuzzy Logic Safety Layer."""

    original_action: Tuple[float, float, float]
    danger_level: float
    closest_obstacle_distance_m: float
    intervened: bool
    final_action: Tuple[float, float, float]
    reason: str
    rule_memberships: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AdaptiveFuzzySafetyLayer:
    """Reactive Adaptive Fuzzy Logic (AFL) safety layer for 3D UAV velocity commands."""

    def __init__(
        self,
        safety_config: Optional[SafetyConfig] = None,
        limits_config: Optional[VehicleLimitsConfig] = None,
    ) -> None:
        self.cfg = safety_config or SafetyConfig()
        self.cfg.validate()
        self.limits = limits_config or VehicleLimitsConfig()

        self.max_vel = np.array(
            [
                self.limits.max_velocity_xy_mps,
                self.limits.max_velocity_xy_mps,
                self.limits.max_velocity_z_mps,
            ],
            dtype=np.float64,
        )

    def compute_distance_memberships(self, distance_m: float) -> Dict[str, float]:
        """Compute fuzzy memberships {critical, near, safe} for obstacle distance d."""
        d_crit = float(self.cfg.critical_distance_m)
        d_safe = float(self.cfg.safe_distance_m)
        d_near = 0.5 * (d_crit + d_safe)
        d = float(distance_m)

        # CRITICAL (left-shoulder)
        if d <= d_crit:
            mu_crit = 1.0
        elif d >= d_near:
            mu_crit = 0.0
        else:
            mu_crit = (d_near - d) / max(d_near - d_crit, 1e-6)

        # NEAR (triangular)
        if d <= d_crit or d >= d_safe:
            mu_near = 0.0
        elif d <= d_near:
            mu_near = (d - d_crit) / max(d_near - d_crit, 1e-6)
        else:
            mu_near = (d_safe - d) / max(d_safe - d_near, 1e-6)

        # SAFE (right-shoulder)
        if d <= d_near:
            mu_safe = 0.0
        elif d >= d_safe:
            mu_safe = 1.0
        else:
            mu_safe = (d - d_near) / max(d_safe - d_near, 1e-6)

        return {
            "critical": float(np.clip(mu_crit, 0.0, 1.0)),
            "near": float(np.clip(mu_near, 0.0, 1.0)),
            "safe": float(np.clip(mu_safe, 0.0, 1.0)),
        }

    def compute_closing_speed_memberships(self, closing_speed_mps: float) -> Dict[str, float]:
        """Compute fuzzy memberships {slow, moderate, fast} for closing speed."""
        v_slow = float(self.cfg.membership.closing_slow_max_mps)
        v_mod = float(self.cfg.membership.closing_moderate_center_mps)
        v_fast = float(self.cfg.membership.closing_fast_min_mps)
        v = float(closing_speed_mps)

        # RECEDING_OR_SLOW
        if v <= v_slow:
            mu_slow = 1.0
        elif v >= v_mod:
            mu_slow = 0.0
        else:
            mu_slow = (v_mod - v) / max(v_mod - v_slow, 1e-6)

        # MODERATE
        if v <= v_slow or v >= v_fast:
            mu_mod = 0.0
        elif v <= v_mod:
            mu_mod = (v - v_slow) / max(v_mod - v_slow, 1e-6)
        else:
            mu_mod = (v_fast - v) / max(v_fast - v_mod, 1e-6)

        # FAST
        if v <= v_mod:
            mu_fast = 0.0
        elif v >= v_fast:
            mu_fast = 1.0
        else:
            mu_fast = (v - v_mod) / max(v_fast - v_mod, 1e-6)

        return {
            "slow": float(np.clip(mu_slow, 0.0, 1.0)),
            "moderate": float(np.clip(mu_mod, 0.0, 1.0)),
            "fast": float(np.clip(mu_fast, 0.0, 1.0)),
        }

    def evaluate_fuzzy_danger(
        self, distance_m: float, closing_speed_mps: float
    ) -> Tuple[float, Dict[str, float]]:
        """Evaluate 9-rule Sugeno fuzzy inference system to obtain danger level in [0, 1]."""
        d_mem = self.compute_distance_memberships(distance_m)
        v_mem = self.compute_closing_speed_memberships(closing_speed_mps)

        rules = [
            ("R1_crit_fast", d_mem["critical"] * v_mem["fast"], 1.00),
            ("R2_crit_mod", d_mem["critical"] * v_mem["moderate"], 0.92),
            ("R3_crit_slow", d_mem["critical"] * v_mem["slow"], 0.80),
            ("R4_near_fast", d_mem["near"] * v_mem["fast"], 0.75),
            ("R5_near_mod", d_mem["near"] * v_mem["moderate"], 0.50),
            ("R6_near_slow", d_mem["near"] * v_mem["slow"], 0.25),
            ("R7_safe_fast", d_mem["safe"] * v_mem["fast"], 0.10),
            ("R8_safe_mod", d_mem["safe"] * v_mem["moderate"], 0.00),
            ("R9_safe_slow", d_mem["safe"] * v_mem["slow"], 0.00),
        ]

        weighted_sum = sum(w * z for _, w, z in rules)
        weight_total = sum(w for _, w, _ in rules)
        danger = weighted_sum / max(weight_total, 1e-6)

        # Ensure critical distance strictly triggers high danger floor even if receding
        if distance_m <= self.cfg.critical_distance_m:
            penetration = (
                self.cfg.critical_distance_m - distance_m
            ) / max(self.cfg.critical_distance_m, 1e-6)
            danger = max(
                danger,
                min(1.0, 0.80 + 0.20 * max(0.0, penetration)),
            )

        diagnostics = {
            "mu_d_critical": d_mem["critical"],
            "mu_d_near": d_mem["near"],
            "mu_d_safe": d_mem["safe"],
            "mu_v_slow": v_mem["slow"],
            "mu_v_moderate": v_mem["moderate"],
            "mu_v_fast": v_mem["fast"],
        }

        return float(np.clip(danger, 0.0, 1.0)), diagnostics

    def filter_action(
        self,
        td3_action_xyz: Sequence[float],
        uav_vel_xyz: Sequence[float],
        obstacle_obs: Optional[ObstacleObservation],
    ) -> SafetyInterventionResult:
        """Filter the TD3-proposed velocity command through the Adaptive Fuzzy Logic safety layer."""
        raw_action = np.asarray(td3_action_xyz, dtype=np.float64)

        if raw_action.shape != (3,) or not np.all(np.isfinite(raw_action)):
            # Malformed action input -> emergency zero velocity
            return SafetyInterventionResult(
                original_action=(0.0, 0.0, 0.0),
                danger_level=1.0,
                closest_obstacle_distance_m=float("nan"),
                intervened=True,
                final_action=(0.0, 0.0, 0.0),
                reason="Invalid or non-finite TD3 proposed velocity command; emergency hover applied.",
                rule_memberships={},
            )

        orig_tuple = (float(raw_action[0]), float(raw_action[1]), float(raw_action[2]))
        clipped_td3 = np.clip(raw_action, -self.max_vel, self.max_vel)

        # Case 1: Missing or invalid sensor observation
        if (
            obstacle_obs is None
            or not obstacle_obs.is_valid
            or not math.isfinite(obstacle_obs.closest_distance_m)
            or obstacle_obs.closest_distance_m < 0.0
        ):
            caution_action = np.clip(
                clipped_td3 * self.cfg.sensor_invalid_fallback_speed_scale,
                -self.max_vel,
                self.max_vel,
            )
            return SafetyInterventionResult(
                original_action=orig_tuple,
                danger_level=0.5,
                closest_obstacle_distance_m=float("nan"),
                intervened=True,
                final_action=(
                    float(caution_action[0]),
                    float(caution_action[1]),
                    float(caution_action[2]),
                ),
                reason="Sensor observation missing or invalid; cautious speed reduction applied.",
                rule_memberships={},
            )

        dist = float(obstacle_obs.closest_distance_m)
        rep_vec = np.asarray(obstacle_obs.repulsion_unit_xyz, dtype=np.float64)

        if not np.all(np.isfinite(rep_vec)):
            rep_vec = np.zeros(3, dtype=np.float64)

        rep_norm = float(np.linalg.norm(rep_vec))

        if rep_norm > 1e-6:
            rep_unit = rep_vec / rep_norm
            unit_to_obs = -rep_unit
        else:
            # Conflicting or zero repulsion vector while obstacle is close -> construct lateral/upward escape
            rep_unit = np.array([0.0, 0.0, 1.0], dtype=np.float64)
            unit_to_obs = np.array([1.0, 0.0, 0.0], dtype=np.float64)

        # Effective closing speed combines actual UAV closing speed and desired TD3 velocity toward obstacle
        cmd_closing = float(np.dot(clipped_td3, unit_to_obs))
        effective_closing = max(float(obstacle_obs.closing_speed_mps), cmd_closing)

        danger, memberships = self.evaluate_fuzzy_danger(dist, effective_closing)

        # Case 2: Clear surroundings (outside safe distance and low danger)
        if dist >= self.cfg.safe_distance_m and danger < self.cfg.intervention_threshold:
            was_clipped = not np.allclose(raw_action, clipped_td3, atol=1e-5)

            return SafetyInterventionResult(
                original_action=orig_tuple,
                danger_level=danger,
                closest_obstacle_distance_m=dist,
                intervened=False,
                final_action=(
                    float(clipped_td3[0]),
                    float(clipped_td3[1]),
                    float(clipped_td3[2]),
                ),
                reason="Clear surroundings; TD3 command passed through."
                if not was_clipped
                else "Clear surroundings; TD3 command clipped to vehicle speed limits.",
                rule_memberships=memberships,
            )

        # Case 3: Active Fuzzy Safety Intervention (Near or Critical proximity)
        # Project out any velocity component of TD3 action that points toward the obstacle
        approaching_comp = float(np.dot(clipped_td3, unit_to_obs))

        if approaching_comp > 0.0:
            # Remove inward velocity proportional to danger (full removal in high/critical danger)
            removal_factor = min(1.0, danger * 1.25)
            safe_tangent_td3 = (
                clipped_td3
                - removal_factor * approaching_comp * unit_to_obs
            )
        else:
            safe_tangent_td3 = clipped_td3.copy()

        # Construct lateral tangent + repulsion escape direction
        horiz_to_obs = np.array(
            [unit_to_obs[0], unit_to_obs[1], 0.0],
            dtype=np.float64,
        )
        horiz_norm = float(np.linalg.norm(horiz_to_obs))

        if horiz_norm > 1e-5:
            # Select the tangent that best aligns with the TD3 movement direction
            t1 = np.array(
                [-horiz_to_obs[1], horiz_to_obs[0], 0.0],
                dtype=np.float64,
            ) / horiz_norm
            t2 = -t1
            dot_diff = float(
                np.dot(clipped_td3, t1) - np.dot(clipped_td3, t2)
            )

            # Modification 2: remove the previous -1.5 selection bias
            lateral_tangent = t1 if dot_diff >= 0.0 else t2
        else:
            lateral_tangent = np.array([0.0, 1.0, 0.0], dtype=np.float64)

        # Combine direct radial repulsion with lateral steering and gentle upward clearance boost
        evasive_dir = 0.50 * rep_unit + 0.50 * lateral_tangent
        evasive_dir[2] += 0.12
        evasive_norm = float(np.linalg.norm(evasive_dir))

        if evasive_norm > 1e-6:
            evasive_dir = evasive_dir / evasive_norm

        repulsion_speed = danger * float(self.cfg.max_repulsion_speed_mps)
        safety_velocity = evasive_dir * repulsion_speed

        # Blend between TD3 tangent-filtered command and active evasive repulsion command
        if (
            dist <= self.cfg.critical_distance_m
            or danger >= self.cfg.emergency_brake_threshold
        ):
            # Critical proximity override: retain existing emergency behavior
            blend_alpha = max(0.75, danger)
            crit_dir = 0.80 * rep_unit + 0.20 * lateral_tangent
            crit_dir /= max(float(np.linalg.norm(crit_dir)), 1e-6)
            crit_vel = crit_dir * float(self.cfg.max_repulsion_speed_mps)

            blended = (
                (1.0 - blend_alpha) * safe_tangent_td3
                + blend_alpha * crit_vel
            )

            reason = (
                f"CRITICAL obstacle proximity (d={dist:.2f}m <= "
                f"{self.cfg.critical_distance_m:.2f}m, danger={danger:.2f}): "
                "emergency braking and repulsive evasion applied."
            )
        else:
            # Modification 3: scale the near-proximity safety command by blend_alpha
            blend_alpha = 0.50 * danger

            blended = (
                (1.0 - blend_alpha) * safe_tangent_td3
                + blend_alpha * safety_velocity
            )

            reason = (
                f"NEAR obstacle hazard (d={dist:.2f}m < "
                f"{self.cfg.safe_distance_m:.2f}m, danger={danger:.2f}): "
                "blended TD3 command with fuzzy repulsive steering."
            )

        final_cmd = np.clip(blended, -self.max_vel, self.max_vel)

        return SafetyInterventionResult(
            original_action=orig_tuple,
            danger_level=danger,
            closest_obstacle_distance_m=dist,
            intervened=True,
            final_action=(
                float(final_cmd[0]),
                float(final_cmd[1]),
                float(final_cmd[2]),
            ),
            reason=reason,
            rule_memberships=memberships,
        )
