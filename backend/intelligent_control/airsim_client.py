"""AirSim Multirotor Client Wrapper for UAV State and Velocity Control.

Separates AirSim RPC calls from the RL and Fuzzy Safety algorithms.
Handles connection verification, API control lifecycle, safe takeoff/landing,
NED position/velocity queries, and bounded velocity execution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

from backend.intelligent_control.config import AirSimConfig

logger = logging.getLogger(__name__)


class AirSimConnectionError(RuntimeError):
    """Raised when connection or communication with the AirSim server fails."""


@dataclass
class UAVKinematicState:
    """UAV kinematic state in AirSim NED coordinates (metres, m/s)."""
    north: float
    east: float
    down: float
    vn: float
    ve: float
    vd: float
    timestamp_ns: int = 0
    is_landed: bool = False


class AirSimUAVClient:
    """Wrapper around `airsim.MultirotorClient` with explicit lifecycle management."""

    def __init__(self, config: Optional[AirSimConfig] = None) -> None:
        self.config = config or AirSimConfig()
        self._client = None
        self._connected = False
        self._api_control_enabled = False
        self._armed = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        """Connect to the configured AirSim server and confirm the connection."""
        try:
            import airsim
        except ImportError as exc:
            raise AirSimConnectionError(
                "The 'airsim' Python package is not installed in the current environment."
            ) from exc

        try:
            self._client = airsim.MultirotorClient(
                ip=self.config.ip,
                port=self.config.port,
                timeout_value=int(self.config.timeout_sec),
            )
            self._client.confirmConnection()
            # Verify RPC responsiveness via ping
            if not self._client.ping():
                raise AirSimConnectionError(
                    f"AirSim server at {self.config.ip}:{self.config.port} did not respond to ping."
                )
            self._connected = True
            logger.info("Connected to AirSim server at %s:%d", self.config.ip, self.config.port)
        except Exception as exc:
            self._connected = False
            self._client = None
            raise AirSimConnectionError(
                f"Failed to connect to AirSim simulator at {self.config.ip}:{self.config.port}: {exc}"
            ) from exc

    def enable_api_control(self) -> None:
        """Enable API control for the configured vehicle."""
        self._require_connection()
        try:
            self._client.enableApiControl(True, vehicle_name=self.config.vehicle_name)
            self._api_control_enabled = True
            logger.info("Enabled API control for vehicle '%s'", self.config.vehicle_name)
        except Exception as exc:
            raise AirSimConnectionError(f"Failed to enable API control: {exc}") from exc

    def arm_and_takeoff(self, altitude_m: Optional[float] = None) -> None:
        """Arm the multirotor and take off to the configured safe altitude."""
        self._require_connection()
        if not self._api_control_enabled:
            self.enable_api_control()

        target_alt = float(altitude_m if altitude_m is not None else self.config.takeoff_altitude_m)
        target_down = -abs(target_alt)
        try:
            self._client.armDisarm(True, vehicle_name=self.config.vehicle_name)
            self._armed = True
            self._client.takeoffAsync(
                timeout_sec=self.config.timeout_sec,
                vehicle_name=self.config.vehicle_name,
            ).join()
            self._client.moveToZAsync(
                z=target_down,
                velocity=min(2.0, self.config.default_velocity_mps),
                timeout_sec=self.config.timeout_sec,
                vehicle_name=self.config.vehicle_name,
            ).join()
            logger.info("Vehicle '%s' armed and reached altitude %.2f m", self.config.vehicle_name, target_alt)
        except Exception as exc:
            raise AirSimConnectionError(f"Failed during arm_and_takeoff: {exc}") from exc

    def get_kinematic_state(self) -> UAVKinematicState:
        """Retrieve current NED position and velocity from AirSim."""
        self._require_connection()
        try:
            state = self._client.getMultirotorState(vehicle_name=self.config.vehicle_name)
            kin = state.kinematics_estimated
            pos = kin.position
            vel = kin.linear_velocity
            is_landed = getattr(state, "landed_state", 0) == 0
            return UAVKinematicState(
                north=float(pos.x_val),
                east=float(pos.y_val),
                down=float(pos.z_val),
                vn=float(vel.x_val),
                ve=float(vel.y_val),
                vd=float(vel.z_val),
                timestamp_ns=int(getattr(state, "timestamp", 0)),
                is_landed=bool(is_landed),
            )
        except Exception as exc:
            raise AirSimConnectionError(f"Failed to retrieve UAV kinematic state: {exc}") from exc

    def move_by_velocity_ned(
        self,
        vn: float,
        ve: float,
        vd: float,
        duration_sec: float = 0.25,
        join: bool = False,
    ) -> None:
        """Execute a velocity command in AirSim NED coordinates."""
        self._require_connection()
        try:
            future = self._client.moveByVelocityAsync(
                vx=float(vn),
                vy=float(ve),
                vz=float(vd),
                duration=float(duration_sec),
                vehicle_name=self.config.vehicle_name,
            )
            if join:
                future.join()
        except Exception as exc:
            raise AirSimConnectionError(f"Failed to execute moveByVelocityAsync: {exc}") from exc

    def hover_and_stop(self) -> None:
        """Command immediate zero-velocity hover for controlled stopping."""
        if not self._connected or self._client is None:
            return
        try:
            self._client.moveByVelocityAsync(
                vx=0.0,
                vy=0.0,
                vz=0.0,
                duration=1.0,
                vehicle_name=self.config.vehicle_name,
            ).join()
            self._client.hoverAsync(vehicle_name=self.config.vehicle_name).join()
        except Exception as exc:
            logger.warning("Failed during hover_and_stop: %s", exc)

    def land_and_release(self) -> None:
        """Stop, land safely, disarm, and release API control."""
        if not self._connected or self._client is None:
            return
        try:
            self.hover_and_stop()
            self._client.landAsync(
                timeout_sec=self.config.timeout_sec,
                vehicle_name=self.config.vehicle_name,
            ).join()
        except Exception as exc:
            logger.warning("Exception while landing vehicle: %s", exc)
        finally:
            try:
                if self._armed:
                    self._client.armDisarm(False, vehicle_name=self.config.vehicle_name)
                    self._armed = False
                if self._api_control_enabled:
                    self._client.enableApiControl(False, vehicle_name=self.config.vehicle_name)
                    self._api_control_enabled = False
            except Exception as exc:
                logger.warning("Exception releasing API control: %s", exc)
            self._connected = False

    @property
    def raw_client(self):
        """Return underlying airsim.MultirotorClient for sensor module access."""
        self._require_connection()
        return self._client

    def _require_connection(self) -> None:
        if not self._connected or self._client is None:
            raise AirSimConnectionError("AirSimUAVClient is not connected to an AirSim server.")
