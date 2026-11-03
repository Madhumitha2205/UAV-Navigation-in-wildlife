# AirSim + Unreal Engine System Audit Report (`PHASE 1`)

**Project:** UAV Navigation in Wildlife
**Workspace:** `C:\Users\madhu\OneDrive\Desktop\UAV-Navigation-in-wildlife`
**Audit Date:** 2026-11-02

---

## 1. Actual Hardware Details

All hardware parameters below were directly queried from the local machine via `nvidia-smi`, Windows Registry (`HKLM\HARDWARE\DESCRIPTION\System\CentralProcessor\0`, `HKLM\SYSTEM\CurrentControlSet\Control\Class`), and Win32 `GlobalMemoryStatusEx` / `shutil.disk_usage`:

| Component | Detected Value | Verification Source / Notes |
|---|---|---|
| **CPU Model** | AMD Ryzen 7 5800HS with Radeon Graphics | Registry `ProcessorNameString` (16 logical processors / 8 cores) |
| **Installed Physical RAM** | **15.40 GB** usable (16 GB physical; ~3.04 GB free at audit time) | Win32 `GlobalMemoryStatusEx` |
| **Dedicated GPU** | **NVIDIA GeForce RTX 2050** (Laptop GPU, WDDM) | `nvidia-smi` & Windows Display Adapter Registry (`0000`) |
| **Dedicated GPU VRAM** | **4096 MiB (4.0 GB)** | `nvidia-smi` (`0MiB / 4096MiB` in use at idle, 30W TGP cap) |
| **Integrated GPU** | AMD Radeon(TM) Graphics | Windows Display Adapter Registry (`0001`, Driver `31.0.21916.2001`) |
| **NVIDIA Driver Version** | **566.07** (Windows internal `32.0.15.6607`, supports up to **CUDA 12.7**) | `nvidia-smi` & Windows Uninstall Registry |
| **DirectX Version** | **DirectX 12** (Registry `4.09.00.0904`) | `HKLM\SOFTWARE\Microsoft\DirectX` |
| **Operating System** | **Windows 10/11 Home Single Language** (Version `25H2`, Build `10.0.26200.9711`, 64-bit `AMD64`) | `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion` & Python `platform` |
| **Disk Space (`C:\`)** | **20.71 GB free** of 329.02 GB total | `shutil.disk_usage('C:\\')` — **Critically low for Unreal Engine installation** |
| **Disk Space (`D:\`)** | **127.62 GB free** of 146.48 GB total | `shutil.disk_usage('D:\\')` — **Sufficient for prebuilt AirSim environments and/or Unreal Engine** |

> **Note on Sandbox WMI Restriction:** `Get-CimInstance` returned `Access to a CIM resource was not available to the client` inside the terminal sandbox, and `C:\Users\madhu\Documents` / `Downloads` are outside the default workspace sandbox ACL. Hardware, OS, RAM, DirectX, GPU, and disk metrics were verified using `nvidia-smi`, Win32 kernel APIs (`ctypes.windll.kernel32.GlobalMemoryStatusEx`), `shutil.disk_usage`, and `winreg`.

---

## 2. Installed Software and Versions

| Software / Component | Status | Installed Version / Path |
|---|---|---|
| **Git** | **Installed** | `git version 2.49.0.windows.1` (`C:\Program Files\Git\cmd\git.EXE`) |
| **Python (Project `.venv`)** | **Installed & Working** | `Python 3.11.9` (`C:\Users\madhu\OneDrive\Desktop\UAV-Navigation-in-wildlife\.venv\Scripts\python.exe`) |
| **Python (System)** | **Installed** | `Python 3.11.9` (`AppData\Local\Programs\Python\Python311`) & `Python 3.13.2` |
| **AirSim Python Client (`airsim`)** | **Installed in `.venv`** | `1.8.1` (with `msgpack-rpc-python==0.4.1`, `msgpack-python==0.5.6`, `tornado==4.5.3`) |
| **PyTorch (`torch`)** | **Installed in `.venv`** | `2.15.0+cpu` (CPU-only build) |
| **NumPy / Matplotlib / OpenCV** | **Installed in `.venv`** | `numpy==2.4.4`, `matplotlib==3.10.9`, `opencv-contrib-python==5.0.0.93` |
| **Pytest** | **Installed in `.venv`** | `pytest==9.1.1` |
| **NVIDIA Graphics Driver & PhysX** | **Installed** | Driver `566.07` (CUDA `12.7`), PhysX `9.21.0713` |
| **MSVC C++ Runtime Redistributables** | **Installed** | Visual C++ 2012, 2013, and v14 (2015–2022) Redistributables (`14.51.36247`) |
| **Epic Games Launcher** | **NOT Installed** | Absent from `C:\Program Files`, `C:\Program Files (x86)`, `C:\ProgramData\Epic`, `D:\`, and Windows Uninstall Registry |
| **Unreal Engine** | **NOT Installed** | Absent from system drives and Windows Uninstall Registry |
| **Visual Studio IDE / C++ Build Tools** | **NOT Installed** | `vswhere.exe`, `cl.exe`, `msbuild.exe`, and `cmake.exe` are not installed (only VS Code and CodeBlocks MinGW exist) |
| **AirSim 3D Simulator Binaries** | **NOT Installed** | No prebuilt AirSim environment (`Blocks`, `AirSimNH`, `Africa`, `LandscapeMountains`) or Unreal project exists on `C:\` or `D:\` |

---

## 3. Missing Dependencies

1. **Rendered 3D AirSim Simulator Application (Required):**
   - Currently, only the Python RPC client library (`airsim==1.8.1`) is installed. No 3D Unreal Engine + AirSim simulator executable (which opens the 3D window and listens on TCP `127.0.0.1:41451`) is present on the machine.
2. **AirSim `settings.json` Configuration File (Required):**
   - AirSim reads its vehicle (`SimpleFlight`), sensor (`LidarSensor1`), and camera configuration from `C:\Users\madhu\Documents\AirSim\settings.json`. This file does not exist yet.
3. **Trained TD3 Model Checkpoint (Required for `--mode airsim`):**
   - `models/` is currently empty (`[]`). `td3_main.py` and `MotionController` explicitly verify that `models/td3_wildlife_uav.pt` exists and has `is_trained == True` before permitting `airsim` or `dry-run` execution.
4. **(Conditional) Unreal Engine 4.27 + Visual Studio 2022 C++ Build Tools:**
   - Only required if building a custom Unreal Engine project or compiling the AirSim C++ plugin from source. **Not required** if running an official prebuilt AirSim v1.8.1 Windows environment binary (e.g., `Blocks` or `AirSimNH` / `LandscapeMountains`), which already packages the compiled Unreal Engine 4.27 runtime and AirSim v1.8.1 server.

---

## 4. Existing Project Verification & Compatibility

The existing codebase was inspected without modification and verified by running `.\.venv\Scripts\python.exe -m pytest -v` (**51 passed, 1 skipped in 20.50s**):

- **AirSim API Usage (`backend/intelligent_control/airsim_client.py` & `airsim_sensors.py`):**
  - Uses `airsim.MultirotorClient(ip="127.0.0.1", port=41451, timeout_value=10)`.
  - Calls `confirmConnection()`, `ping()`, `enableApiControl(True, vehicle_name="SimpleFlight")`, `armDisarm(True, vehicle_name="SimpleFlight")`, `takeoffAsync()`, `moveToZAsync()`, `getMultirotorState()`, `moveByVelocityAsync()`, `hoverAsync()`, `landAsync()`, `simGetCollisionInfo()`, and `getLidarData(lidar_name="LidarSensor1", vehicle_name="SimpleFlight")`.
- **Expected Connection & Sensor Settings (`configs/controller_config.json`):**
  - Server: `127.0.0.1:41451`
  - Vehicle Name: `"SimpleFlight"`
  - LiDAR Sensor Name: `"LidarSensor1"`
  - Takeoff Altitude: `15.0` m
  - Default Velocity: `3.0` m/s
- **Expected Checkpoint Location:**
  - `models/td3_wildlife_uav.pt` (with companion `models/td3_wildlife_uav.meta.json`).
- **Coordinate System (`backend/intelligent_control/coordinate_transform.py`):**
  - **Global Planner Frame (`ENU_ALT_UP`):** $X = \text{East}$, $Y = \text{North}$, $Z = \text{Altitude (+Up)}$ in metres.
  - **AirSim Frame (`NED`):** $\text{North} = +Y_{\text{planner}}$, $\text{East} = +X_{\text{planner}}$, $\text{Down} = -Z_{\text{planner}}$.
  - Bi-directional conversion is already implemented and tested for positions, velocities, route waypoints, and obstacles.
- **Controller Execution Modes (`td3_main.py`):**
  - `--mode train`: Trains TD3 across the 5-stage curriculum in `LightweightUAVEnv` (`150` episodes default: `5 stages × 30 episodes/stage`) and saves `models/td3_wildlife_uav.pt`.
  - `--mode dry-run`: Runs `MissionRunner` in the local kinematic backend and saves `logs/dry_run_result.json`.
  - `--mode evaluate`: Runs multi-seed evaluation across Configs A, B, and C, outputting `logs/evaluation_summary.csv`, `logs/evaluation_trials.csv`, `outputs/trajectory_comparison.png`, and `outputs/metrics_comparison.png`.
  - `--mode airsim`: Connects to live AirSim server at `127.0.0.1:41451`, executes the trained TD3 policy with Adaptive Fuzzy Safety, lands safely in a `finally` block, and writes `logs/airsim_mission_result.json`.

---

## 5. Potential Incompatibilities & Hardware Constraints

1. **Critical `C:\` Drive Space Constraint (20.71 GB Free):**
   - Installing Epic Games Launcher + Unreal Engine 4.27 (~45–60 GB) + Visual Studio 2022 C++ Build Tools (~8–15 GB) on `C:\` **will fail due to insufficient disk space**.
   - **Solution:** Any large simulator binaries or Unreal Engine installations **must** be placed on `D:\` (**127.62 GB free**).
2. **RTX 2050 Laptop GPU (4 GB VRAM, 30W TGP):**
   - Heavy photogrammetry environments (such as `Africa` or high-resolution UE5 scenes) can exceed 4 GB VRAM and cause severe frame drops or DirectX `D3D11`/`D3D12` out-of-memory crashes.
   - Launching the simulator in windowed mode (`-ResX=1280 -ResY=720 -windowed`) or using lightweight official AirSim v1.8.1 environments (`Blocks` or `AirSimNH` / `LandscapeMountains`) is strongly recommended to keep VRAM usage well under 4 GB and maintain stable FPS.
3. **Unreal Engine 5 Incompatibility with Official Microsoft AirSim:**
   - Microsoft archived official AirSim at **v1.8.1**, which strictly targets **Unreal Engine 4.27**. Attempting to build official `microsoft/AirSim` against Unreal Engine 5.x fails without third-party forks (such as Colosseum).
4. **System RAM Availability (~3.04 GB Free at Audit Time):**
   - Out of 15.40 GB total RAM, ~12.36 GB was in use by background applications during the audit. Running Unreal Engine / AirSim requires ~2–4 GB of RAM, so closing unnecessary background tabs/apps before launching the 3D simulator is advised.

---

## 6. Recommended Installation Approach

We have two viable paths to get a rendered 3D Unreal Engine + AirSim environment running on this laptop:

### Option A (Recommended — Fast, Official Prebuilt Unreal Engine 4.27 + AirSim v1.8.1 Binary on `D:\`)
- Download the official Microsoft AirSim **v1.8.1 Windows prebuilt Unreal Engine 4.27 environment binary** (such as `Blocks.zip` ~270 MB or `AirSimNH.zip` ~1.5 GB / `LandscapeMountains.zip` ~1.7 GB) directly from the official GitHub release (`https://github.com/microsoft/AirSim/releases/tag/v1.8.1-windows`) onto `D:\AirSimEnvironments\`.
- Configure `C:\Users\madhu\Documents\AirSim\settings.json` with `"SimMode": "Multirotor"`, vehicle `"SimpleFlight"`, and sensor `"LidarSensor1"` (`"SensorType": 6`, `"Enabled": true`) to match `configs/controller_config.json`.
- **Why this is best for your hardware:**
  - It is a real, rendered 3D Unreal Engine 4.27 + AirSim v1.8.1 application with full physics, collision detection, camera sub-windows, and 3D LiDAR raycasting.
  - Requires **< 2 GB of disk space** on `D:\` (preserving `C:\` completely).
  - Runs smoothly at 60 FPS on an **NVIDIA GeForce RTX 2050 (4 GB VRAM)** without needing 60+ GB for the full Unreal Editor + Visual Studio C++ compiler toolchain.

### Option B (Full Editor + Source Build — Epic Games Launcher + Unreal Engine 4.27.2 + Visual Studio 2022 on `D:\`)
- Install Epic Games Launcher + **Unreal Engine 4.27.2** onto `D:\EpicGames\UE_4.27` (~55 GB) and **Visual Studio 2022 Build Tools** (Desktop development with C++, MSVC v143, Windows 10/11 SDK) (~12 GB), then clone `microsoft/AirSim` (`v1.8.1`) on `D:\AirSim` and run `build.cmd` to compile the plugin and open `Blocks.uproject` inside the Unreal Editor.
- **Trade-offs:** Requires ~70–80 GB of disk space, 1–2 hours of download/compilation time, and uses significantly more RAM/VRAM when running inside the Unreal Editor compared to the packaged standalone Unreal binary in Option A.

---

## 7. Unresolved Issues Pending User Approval

1. **Choice between Option A (Prebuilt Official UE 4.27 + AirSim v1.8.1 3D Environment Binary on `D:\`) vs. Option B (Full Unreal Engine 4.27 Editor + Visual Studio 2022 Source Build on `D:\`).**
2. **Sandbox File Access for `C:\Users\madhu\Documents\AirSim\settings.json`:** Writing to `C:\Users\madhu\Documents\AirSim\settings.json` and downloading/launching the simulator on `D:\` will require running those specific commands outside the workspace sandbox (`BypassSandbox: true`) after your approval.
3. **TD3 Checkpoint Training:** `models/td3_wildlife_uav.pt` must be trained via `.\.venv\Scripts\python.exe td3_main.py --mode train` in Phase 9 before running Phase 10 (`--mode airsim`).
