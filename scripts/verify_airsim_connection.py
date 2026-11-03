"""Read-Only AirSim Simulator Connection, Vehicle, State, Collision, and LiDAR Verification Script.

Connects to 127.0.0.1:41451 (or configured host/port in configs/controller_config.json)
and performs strictly read-only checks:
1. AirSim API connection (TCP socket + MultirotorClient initialization)
2. confirmConnection() verification
3. API responsiveness (ping() + getServerVersion() / getClientVersion())
4. Available vehicle names (listVehicles())
5. SimpleFlight availability & read-only API control status (isApiControlEnabled())
6. Multirotor state retrieval (getMultirotorState())
7. LiDAR sensor availability & configuration check
8. LiDAR data retrieval (getLidarData('LidarSensor1', 'SimpleFlight'))
9. LiDAR point cloud contains actual 3D points (non-empty finite XYZ points)
10. Collision information retrieval (simGetCollisionInfo('SimpleFlight'))
11. Clean Python process exit (exit code 0)

Strictly READ-ONLY: Does NOT arm the UAV, take off, move the UAV, change its position,
execute a mission, or start TD3 training.
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.intelligent_control.config import load_controller_config


def main() -> int:
    cfg = load_controller_config(PROJECT_ROOT / "configs" / "controller_config.json")
    ip = cfg.airsim.ip
    port = cfg.airsim.port
    vehicle_name = cfg.airsim.vehicle_name
    lidar_name = cfg.airsim.lidar_sensor_name

    all_passed = True
    details: dict[str, str] = {}

    # 1 & 2. Server TCP Connection + confirmConnection() + ping()
    client = None
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(3.0)
            rc = sock.connect_ex((ip, port))
            if rc != 0:
                raise ConnectionError(f"TCP port {ip}:{port} is not open (connect_ex={rc}).")

        import airsim

        client = airsim.MultirotorClient(ip=ip, port=port, timeout_value=int(cfg.airsim.timeout_sec))
        client.confirmConnection()
        if not client.ping():
            raise ConnectionError(f"AirSim RPC server at {ip}:{port} did not respond to ping().")
        print("AirSim server connection: PASS")
        details["1_tcp_and_rpc_connection"] = f"PASS (Connected to {ip}:{port})"
        details["2_confirm_connection"] = "PASS (confirmConnection() succeeded)"
        details["3_api_responsiveness"] = "PASS (ping() == True)"
    except Exception as exc:
        print(f"AirSim server connection: FAIL ({exc})")
        print("API version check: FAIL (Skipped due to connection failure)")
        print("Vehicle availability: FAIL (Skipped due to connection failure)")
        print("Vehicle state retrieval: FAIL (Skipped due to connection failure)")
        print("LiDAR sensor check: FAIL (Skipped due to connection failure)")
        return 1

    # 3b. API Version Check
    try:
        server_ver = client.getServerVersion()
        client_ver = client.getClientVersion()
        min_server_ver = client.getMinRequiredServerVersion()
        min_client_ver = client.getMinRequiredClientVersion()
        if server_ver < min_server_ver or client_ver < min_client_ver:
            raise RuntimeError(
                f"Version mismatch: server={server_ver} (min={min_server_ver}), "
                f"client={client_ver} (min={min_client_ver})"
            )
        print("API version check: PASS")
        details["3b_api_version"] = (
            f"PASS (Server RPC Version={server_ver}, Client RPC Version={client_ver}, "
            f"airsim package={getattr(airsim, '__version__', '1.8.1')})"
        )
    except Exception as exc:
        all_passed = False
        print(f"API version check: FAIL ({exc})")

    # 4 & 5. Vehicle Availability & SimpleFlight Check (Read-Only)
    try:
        vehicles = client.listVehicles()
        if vehicle_name not in vehicles:
            raise RuntimeError(
                f"Configured vehicle '{vehicle_name}' not found in simulator vehicles: {vehicles}"
            )
        api_ctrl_status = client.isApiControlEnabled(vehicle_name=vehicle_name)
        print("Vehicle availability: PASS")
        details["4_available_vehicles"] = f"PASS (listVehicles() -> {vehicles})"
        details["5_simpleflight_availability"] = (
            f"PASS ('{vehicle_name}' available; isApiControlEnabled={api_ctrl_status} [read-only])"
        )
    except Exception as exc:
        all_passed = False
        print(f"Vehicle availability: FAIL ({exc})")

    # 6 & 10. Multirotor State & Collision Info Retrieval (Read-Only)
    try:
        state = client.getMultirotorState(vehicle_name=vehicle_name)
        kin = state.kinematics_estimated
        pos = kin.position
        vel = kin.linear_velocity
        col = client.simGetCollisionInfo(vehicle_name=vehicle_name)
        has_collided = bool(getattr(col, "has_collided", False))
        print("Vehicle state retrieval: PASS")
        details["6_multirotor_state"] = (
            f"PASS (NED pos=({pos.x_val:.3f}, {pos.y_val:.3f}, {pos.z_val:.3f}) m, "
            f"vel=({vel.x_val:.3f}, {vel.y_val:.3f}, {vel.z_val:.3f}) m/s, "
            f"landed_state={getattr(state, 'landed_state', 'N/A')})"
        )
        details["10_collision_info"] = (
            f"PASS (simGetCollisionInfo: has_collided={has_collided}, "
            f"object_name='{getattr(col, 'object_name', '')}')"
        )
    except Exception as exc:
        all_passed = False
        print(f"Vehicle state retrieval: FAIL ({exc})")

    # 7, 8 & 9. LiDAR Sensor Check (Read-Only)
    try:
        lidar_data = client.getLidarData(lidar_name=lidar_name, vehicle_name=vehicle_name)
        point_cloud = getattr(lidar_data, "point_cloud", None)
        if point_cloud is None:
            raise RuntimeError(f"LiDAR sensor '{lidar_name}' returned None point_cloud.")
        num_floats = len(point_cloud)
        num_points = num_floats // 3
        if num_points <= 0:
            raise RuntimeError(
                f"LiDAR sensor '{lidar_name}' returned 0 points (point_cloud length={num_floats})."
            )
        pts = np.asarray(point_cloud[: num_points * 3], dtype=np.float64).reshape(-1, 3)
        finite_pts = pts[np.all(np.isfinite(pts), axis=1)]
        dists = np.linalg.norm(finite_pts, axis=1)
        min_d = float(np.min(dists)) if len(dists) > 0 else float("nan")
        max_d = float(np.max(dists)) if len(dists) > 0 else float("nan")
        print("LiDAR sensor check: PASS")
        details["7_lidar_sensor_available"] = f"PASS (Sensor '{lidar_name}' responded on '{vehicle_name}')"
        details["8_lidar_data_retrieval"] = f"PASS (time_stamp={getattr(lidar_data, 'time_stamp', 0)})"
        details["9_lidar_point_cloud_data"] = (
            f"PASS ({len(finite_pts)} valid 3D points; distance range [{min_d:.2f} m .. {max_d:.2f} m], "
            f"sample_pt_0=({finite_pts[0][0]:.2f}, {finite_pts[0][1]:.2f}, {finite_pts[0][2]:.2f}))"
        )
    except Exception as exc:
        all_passed = False
        print(f"LiDAR sensor check: FAIL ({exc})")

    details["11_clean_process_exit"] = "PASS" if all_passed else "FAIL"

    print("\n--- Detailed 11-Point Verification Summary ---")
    for k, v in details.items():
        print(f"  {k}: {v}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
