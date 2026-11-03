# Complete AirSim Installation, Configuration & Verification Report (`PHASE 9`)

**Project:** UAV Navigation in Wildlife
**Repository:** `https://github.com/Madhumitha2205/UAV-Navigation-in-wildlife`
**Local Project Directory:** `C:\Users\madhu\OneDrive\Desktop\UAV-Navigation-in-wildlife`
**AirSim Environment Directory:** `D:\AirSimEnvironments\Blocks`
**Audit Report:** [reports/complete_airsim_installation_audit.md](file:///c:/Users/madhu/OneDrive/Desktop/UAV-Navigation-in-wildlife/reports/complete_airsim_installation_audit.md)

---

## A. Software Installation & Verification Table

| Component | Status | Version | Source |
|---|---|---|---|
| **AirSim Blocks** | **Installed & Verified** | `v1.8.1-windows` (Unreal Engine `4.27` packaged build; `259,463,081 bytes`, SHA-256 `47c526a5f0acff42c211d2479b9de9f10286a8162678ef19adc09040a23ca1db`) | Official Microsoft AirSim GitHub Release: [`https://github.com/microsoft/AirSim/releases/tag/v1.8.1-windows`](https://github.com/microsoft/AirSim/releases/tag/v1.8.1-windows) |
| **DirectX Legacy Runtime Files** | **Installed Locally & Verified** | Microsoft DirectX End-User Runtimes (June 2010) (`directx_Jun2010_redist.exe`, `100,275,120 bytes`, SHA-256 `053f76dcbb28802e23341b6a787e3b0791c0fa5c8d4d011b1044172dbf89c73b`, Valid Microsoft Corporation Authenticode Signature `2485A7AFA98E178CB8F30C9838346B514AEA4769`). Extracted 64-bit (`0x8664`) `X3DAudio1_7.dll`, `XAPOFX1_5.dll`, `D3DCompiler_43.dll`, and `xinput1_3.dll` locally into `Blocks\Binaries\Win64` (`C:\Windows\System32` untouched) | Official Microsoft Download Center: [`https://download.microsoft.com/download/8/4/A/84A35BF1-DAFE-4AE8-82AF-AD2AE20B6B14/directx_Jun2010_redist.exe`](https://www.microsoft.com/en-us/download/details.aspx?id=8109) |
| **Visual C++ Runtime** | **Pre-installed & Working (Unchanged)** | Microsoft Visual C++ v14 Redistributable (x64 & x86) `14.51.36247.0` (`MSVCP140.dll`, `VCRUNTIME140.dll`, `VCRUNTIME140_1.dll`) | System pre-installed ([Microsoft Official VC++ Redist](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)) |
| **NVIDIA Driver** | **Pre-installed & Working (Unchanged)** | `566.07` (CUDA `12.7`, NVIDIA GeForce RTX 2050 Laptop GPU, 4096 MiB VRAM) | System pre-installed (`nvidia-smi`) |
| **Python** | **Pre-installed & Working (Unchanged)** | `Python 3.11.9` (64-bit in `.venv`) | Local `.venv` (`C:\Users\madhu\OneDrive\Desktop\UAV-Navigation-in-wildlife\.venv\Scripts\python.exe`) |
| **AirSim Python Package** | **Pre-installed & Working (Unchanged)** | `airsim==1.8.1` (`msgpack-rpc-python==0.4.1`, `msgpack-python==0.5.6`, `tornado==4.5.3`, `pip check` passed) | Local `.venv` (`requirements.txt`) |
| **PyTorch** | **Pre-installed & Working (Unchanged)** | `torch==2.15.0+cpu` | Local `.venv` (`requirements.txt`) |

---

## B. Simulator Verification Table (`PHASE 4` & `PHASE 5`)

| Check | Result | Verification Evidence |
|---|---|---|
| **Blocks executable launches** | **PASS** | `D:\AirSimEnvironments\Blocks\Blocks\WindowsNoEditor\Blocks.exe -ResX=1280 -ResY=720 -windowed` launches and remains running (~466 MB RAM footprint) |
| **Unreal 3D environment visible** | **PASS** | `FlyingExampleMap` (`AirSimGameMode`) loads in a `1280x720` DirectX 11 window (`Blocks.log` confirms `Bringing World /Game/FlyingCPP/Maps/FlyingExampleMap.FlyingExampleMap up for play`) |
| **UAV visible** | **PASS** | `SimpleFlight` multirotor is spawned at `(0.000, 0.000, 0.671)` m NED in `SpringArmChase` view mode (`DefaultVehicleState: "Disarmed"`, `landed_state: 0`) |
| **AirSim API responds** | **PASS** | `confirmConnection()` and `ping() == True` (`Server Ver: 1`, `Client Ver: 1`) |
| **Port 41451 responds** | **PASS** | TCP socket connection to `127.0.0.1:41451` opens within 4 seconds of launching `Blocks.exe` |
| **SimpleFlight available** | **PASS** | `client.listVehicles()` returns `['SimpleFlight']`; `isApiControlEnabled('SimpleFlight') == False` (read-only) |
| **LiDAR sensor available** | **PASS** | `client.getLidarData('LidarSensor1', 'SimpleFlight')` responds with valid sensor frame timestamp `1793633387756264960` |
| **LiDAR returns actual points** | **PASS** | Returned **`2,110` valid finite 3D points** on first query (`distance range [1.49 m .. 49.81 m]`, sample point `(23.10, -12.51, -7.37)`) |

---

## C. Project Verification Table (`PHASE 6`, `PHASE 7`, `PHASE 8`)

| Check | Result | Verification Evidence |
|---|---|---|
| **Python dependencies valid** | **PASS** | `.\.venv\Scripts\python.exe -m pip check` → `No broken requirements found.` |
| **Existing tests pass** | **PASS (`52 passed`!)** | `.\.venv\Scripts\python.exe -m pytest -v -rs` → **`52 passed, 2 warnings in 26.64s`** (all 51 unit tests + `test_optional_live_airsim_connection` passed against the live simulator!) |
| **Global planner works** | **PASS** | `.\.venv\Scripts\python.exe main.py` → `Status: SUCCESS`, `Independent Validation: PASSED`, `Total Path Length: 294.85 meters`, exported `outputs/planned_route.json` |
| **Coordinate conversion verified** | **PASS** | Verified bi-directional `ENU_ALT_UP` ↔ `NED` position, altitude sign (`z_sign = -1.0`), velocity, route waypoint, and obstacle conversions (`test_coordinate_transform.py` all 4 tests `PASSED`) |
| **AirSim client connects** | **PASS** | Verified via both `scripts/verify_airsim_connection.py` (`PASS` on all 11 checks) and `AirSimUAVClient.connect()` in `test_optional_live_airsim_connection` (`PASSED`) |
| **TD3 checkpoint available** | **NOT YET CREATED (Expected)** | `models/td3_wildlife_uav.pt` does not exist yet (`models/` directory is empty). Per Phase 8 rules, training was not started automatically and remains a separate pending step. |
| **TD3 checkpoint loads** | **PENDING TRAINING** | Verified in `test_motion_controller.py::test_untrained_td3_policy_rejected` (`PASSED`) that `MotionController` and `td3_main.py` properly guard against running `--mode airsim` until `models/td3_wildlife_uav.pt` is trained. |

---

## D. Important Technical Finding Resolved During Phase 3 & Phase 4

1. **Why `Blocks.exe` Previously Waited Before Opening Port `41451`:**
   - On this Windows laptop, OneDrive redirects the Windows Shell `CSIDL_MYDOCUMENTS` known folder (`SHGetFolderPathW(NULL, CSIDL_MYDOCUMENTS, ...)`) to **`C:\Users\madhu\OneDrive\Documents`**.
   - AirSim's C++ `Settings::getUserDirectoryFullPath()` queries `CSIDL_MYDOCUMENTS` (`C:\Users\madhu\OneDrive\Documents\AirSim\settings.json`) rather than `%USERPROFILE%\Documents\AirSim\settings.json`.
   - When `C:\Users\madhu\OneDrive\Documents\AirSim\settings.json` only contained a default 114-byte stub without `"SimMode": "Multirotor"`, `Blocks.exe` paused at startup waiting for a manual Yes/No button click on the Car vs. Quadrotor prompt before opening port `41451`.
   - Backing up `C:\Users\madhu\OneDrive\Documents\AirSim\settings.json` to `settings.json.bak` and installing the validated `settings.json` in **both** `C:\Users\madhu\Documents\AirSim\settings.json` and `C:\Users\madhu\OneDrive\Documents\AirSim\settings.json` resolved this completely: `Blocks.exe` now boots directly into `Multirotor` mode with `SimpleFlight` and `LidarSensor1` and opens port `41451` in **4 seconds**.
2. **Phase 6 Integration Inspection Note (`airsim_client.py`):**
   - All existing project files (`td3_main.py`, `main.py`, `airsim_client.py`, `airsim_sensors.py`, `mission_runner.py`, `coordinate_transform.py`, `td3_agent.py`, `curriculum.py`) were inspected and **zero existing source files were modified**.
   - Minor observation for future reference: in `AirSimUAVClient.land_and_release()`, `self.hover_and_stop()` and `self._client.landAsync()` are called before checking `if self._api_control_enabled:`. During a read-only connection (such as `test_optional_live_airsim_connection()`), `self._api_control_enabled` is `False`, so AirSim safely ignores the hover/land RPC call and `test_optional_live_airsim_connection` passes without moving the UAV. No code rewrite was needed.

---

## E. Complete Inventory of Files Created, Modified, Downloaded, Backed Up, or Copied

### 1. Existing Project Source Files Modified
- **None (0 files modified).** All existing Python modules, tests, and configs (`requirements.txt`, `configs/controller_config.json`, `configs/default_environment.json`, `configs/safety_config.json`, `configs/sample_global_route.json`, `main.py`, `td3_main.py`, `backend/**`, `tests/**`) remain 100% untouched.

### 2. Newly Downloaded Official Archives on `D:\`
- `D:\AirSimEnvironments\Blocks.zip` (`259,463,081 bytes`, SHA-256 `47c526a5f0acff42c211d2479b9de9f10286a8162678ef19adc09040a23ca1db`) — Extracted to `D:\AirSimEnvironments\Blocks\`.
- `D:\AirSimEnvironments\DirectXRedist\directx_Jun2010_redist.exe` (`100,275,120 bytes`, SHA-256 `053f76dcbb28802e23341b6a787e3b0791c0fa5c8d4d011b1044172dbf89c73b`) — Extracted `.cab` files to `D:\AirSimEnvironments\DirectXRedist\extracted_cabs\` and 4 x64 DLLs to `D:\AirSimEnvironments\DirectXRedist\extracted_dlls_x64\`.

### 3. Verified 64-Bit Microsoft DirectX DLLs Copied Locally into `Blocks\Binaries\Win64`
- `D:\AirSimEnvironments\Blocks\Blocks\WindowsNoEditor\Blocks\Binaries\Win64\X3DAudio1_7.dll` (`24,920 bytes`, SHA-256 `9460709339701ad471a5cabe6365355f4d586dc4fcb86507c1331839dc555446`)
- `D:\AirSimEnvironments\Blocks\Blocks\WindowsNoEditor\Blocks\Binaries\Win64\XAPOFX1_5.dll` (`77,656 bytes`, SHA-256 `e47dcf74d50403b376c562e4121e359e5886e42fcc60b3fa8ba53e6826854c49`)
- `D:\AirSimEnvironments\Blocks\Blocks\WindowsNoEditor\Blocks\Binaries\Win64\D3DCompiler_43.dll` (`2,526,056 bytes`, SHA-256 `44c3a7e330b54a35a9efa015831392593aa02e7da1460be429d17c3644850e8a`)
- `D:\AirSimEnvironments\Blocks\Blocks\WindowsNoEditor\Blocks\Binaries\Win64\xinput1_3.dll` (`107,368 bytes`, SHA-256 `756cad002e1553cfa1a91ebe8c1b9380ffabe0b4b1916c4a4db802396ddfbef8`)

### 4. Configuration Files & Backups
- Backup: `C:\Users\madhu\Documents\AirSim\settings.json.bak` (`1,158 bytes`)
- Backup: `C:\Users\madhu\OneDrive\Documents\AirSim\settings.json.bak` (`114 bytes`)
- Active Config: `C:\Users\madhu\OneDrive\Documents\AirSim\settings.json` (`1,119 bytes`)
- Active Config (Mirror): `C:\Users\madhu\Documents\AirSim\settings.json` (`1,119 bytes`)
- Project Reference Copy: [configs/airsim_settings.json](file:///c:/Users/madhu/OneDrive/Desktop/UAV-Navigation-in-wildlife/configs/airsim_settings.json) (`1,119 bytes`)

### 5. New Verification Script & Reports Created in Project Workspace
- [scripts/verify_airsim_connection.py](file:///c:/Users/madhu/OneDrive/Desktop/UAV-Navigation-in-wildlife/scripts/verify_airsim_connection.py)
- [reports/airsim_system_audit.md](file:///c:/Users/madhu/OneDrive/Desktop/UAV-Navigation-in-wildlife/reports/airsim_system_audit.md)
- [reports/complete_airsim_installation_audit.md](file:///c:/Users/madhu/OneDrive/Desktop/UAV-Navigation-in-wildlife/reports/complete_airsim_installation_audit.md)
- [reports/complete_airsim_installation_report.md](file:///c:/Users/madhu/OneDrive/Desktop/UAV-Navigation-in-wildlife/reports/complete_airsim_installation_report.md)
- [docs/AIRSIM_VERSION_MATRIX.md](file:///c:/Users/madhu/OneDrive/Desktop/UAV-Navigation-in-wildlife/docs/AIRSIM_VERSION_MATRIX.md)
- [docs/AIRSIM_INSTALLATION_PLAN.md](file:///c:/Users/madhu/OneDrive/Desktop/UAV-Navigation-in-wildlife/docs/AIRSIM_INSTALLATION_PLAN.md)

---

## F. Final Status

### **1. READY — 3D simulator and read-only project connection verified.**

- The rendered 3D Unreal Engine `Blocks` environment (`D:\AirSimEnvironments\Blocks\Blocks\WindowsNoEditor\Blocks.exe -ResX=1280 -ResY=720 -windowed`) launches cleanly and is currently running on your desktop.
- The virtual `SimpleFlight` quadrotor UAV is visible in the 3D scene in a safe **Disarmed** state on the ground (`(0.000, 0.000, 0.671)` m NED) with green `LidarSensor1` debug laser points visible across the surrounding 3D blocks.
- [scripts/verify_airsim_connection.py](file:///c:/Users/madhu/OneDrive/Desktop/UAV-Navigation-in-wildlife/scripts/verify_airsim_connection.py) passed **all 11 read-only checks**, retrieving **`2,110` real 3D LiDAR points** (`1.49 m` to `49.81 m`) and collision telemetry (`Ground_6`).
- All **52 project pytest tests (`52 passed, 0 skipped`)** and `main.py` (`Status: SUCCESS`) passed without modifying any existing project code or `.venv` packages.
- **Next Separate Task (When You Are Ready):** Train the TD3 checkpoint (`models/td3_wildlife_uav.pt`) via `.\.venv\Scripts\python.exe td3_main.py --mode train` and then run the live autonomous flight mission (`--mode airsim`).
