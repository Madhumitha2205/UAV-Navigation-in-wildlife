# Complete AirSim Installation, Configuration & Project Audit (`PHASE 1`)

**Project:** UAV Navigation in Wildlife
**Workspace:** `C:\Users\madhu\OneDrive\Desktop\UAV-Navigation-in-wildlife`
**AirSim Environment Directory:** `D:\AirSimEnvironments\Blocks`
**Audit Date:** 2026-11-02

---

## 1. Live Recheck of All 11 System & Project Items

Every item below was re-inspected directly on the machine without assuming prior state:

| # | Audit Item | Verified Current State | Evidence / Command Used |
|---|---|---|---|
| **1** | **Available Free Disk Space (`C:` & `D:`)** | **`C:\`: 20.69 GB free** of 329.02 GB total<br>**`D:\`: 126.64 GB free** of 146.48 GB total | `shutil.disk_usage('C:\\')` & `shutil.disk_usage('D:\\')` (`D:\` decreased by ~0.98 GB due to `Blocks.zip` + extracted `Blocks`) |
| **2** | **Available RAM** | **15.40 GB usable** (16 GB physical); **3.56 GB free** (`76%` memory load) at recheck time | Win32 `GlobalMemoryStatusEx` |
| **3** | **NVIDIA GPU & Driver** | **NVIDIA GeForce RTX 2050** (4096 MiB VRAM, `0 MiB` in use at idle, 41°C, 30W TGP cap)<br>Driver: **`566.07`** (CUDA Version **`12.7`**) | `nvidia-smi` |
| **4** | **Python & Virtual Environment** | **`Python 3.11.9`** at `C:\Users\madhu\OneDrive\Desktop\UAV-Navigation-in-wildlife\.venv\Scripts\python.exe` | `.\.venv\Scripts\python.exe --version` |
| **5** | **AirSim Python Package** | **`airsim==1.8.1`** installed in `.venv`; `pip check` reports **`No broken requirements found.`** | `.\.venv\Scripts\python.exe -m pip show airsim` & `pip check` |
| **6** | **Existing Visual C++ Redistributables** | **Installed & Working:**<br>- Microsoft Visual C++ v14 Redistributable (x64 & x86) `14.51.36247.0`<br>- Microsoft Visual C++ 2013 & 2012 Redistributables<br>- `MSVCP140.dll`, `VCRUNTIME140.dll`, `VCRUNTIME140_1.dll` all load cleanly | Windows Uninstall Registry & `ctypes.WinDLL` |
| **7** | **Existing DirectX Components** | **DirectX 12 (`d3d11.dll`, `d3d12.dll`, `dxgi.dll`, `d3dcompiler_47.dll`) installed.**<br>**Missing 4 legacy DirectX June 2010 x64 DLLs:** `X3DAudio1_7.dll`, `XAPOFX1_5.dll`, `D3DCOMPILER_43.dll`, `XINPUT1_3.dll` | PE Import Table analysis of `Blocks.exe` & `ctypes.WinDLL` (`0xC0000135` `STATUS_DLL_NOT_FOUND`) |
| **8** | **AirSim `Blocks` Files & Executables** | **Present & Verified on `D:\`:**<br>- Archive: `D:\AirSimEnvironments\Blocks.zip` (`259,463,081 bytes`, SHA-256 `47c526a5f0acff42c211d2479b9de9f10286a8162678ef19adc09040a23ca1db`)<br>- Wrapper EXE: `D:\AirSimEnvironments\Blocks\Blocks\WindowsNoEditor\Blocks.exe` (`144,896 bytes`)<br>- Main Binary: `D:\AirSimEnvironments\Blocks\Blocks\WindowsNoEditor\Blocks\Binaries\Win64\Blocks.exe` (`168,181,760 bytes`) | File size, SHA-256 checksum, and ZIP CRC verification against official GitHub Release `v1.8.1-windows` |
| **9** | **Existing AirSim Settings** | `C:\Users\madhu\Documents\AirSim\settings.json` (`1,158 bytes`) and `configs/airsim_settings.json` (`1,158 bytes`) exist, but currently contain `"DefaultVehicleState": "Armed"` and `"EnableCollisionPassthrogh": false` — **must be backed up and updated in Phase 3** so `"DefaultVehicleState": "Disarmed"` and only verified AirSim 1.8.1 settings are used. | Direct file inspection |
| **10** | **Project Dependencies & Tests** | `requirements.txt` dependencies (`numpy==2.4.4`, `matplotlib==3.10.9`, `torch==2.15.0+cpu`, `pytest==9.1.1`, `airsim==1.8.1`, `msgpack-rpc-python==0.4.1`, `tornado==4.5.3`) are intact; `51 passed, 1 skipped` | `pip check` & `pytest` |
| **11** | **Existing TD3 Model Checkpoint** | `models/td3_wildlife_uav.pt` **does NOT exist** (`models/` is empty `[]`). Training remains a separate pending task per Phase 8. | `Path('models/td3_wildlife_uav.pt').exists() == False` |

---

## 2. Audit Conclusions & Action Items for Phases 2–9

1. **No Reinstallation of Working Components:**
   - Python `.venv` (`3.11.9`), `airsim==1.8.1`, `torch==2.15.0+cpu`, Visual C++ v14 Redistributable (`14.51.36247.0`), NVIDIA Driver (`566.07`), and `D:\AirSimEnvironments\Blocks` are already present and verified. None of them will be reinstalled or replaced.
2. **Targeted Fix for `0xC0000135` (`STATUS_DLL_NOT_FOUND`):**
   - Download only the official Microsoft DirectX End-User Runtimes (June 2010) package (`directx_Jun2010_redist.exe`) to `D:\AirSimEnvironments\DirectXRedist`, verify its Microsoft Authenticode digital signature and file integrity, extract it to a temporary folder, and copy **only** the 4 required 64-bit DLLs (`X3DAudio1_7.dll`, `XAPOFX1_5.dll`, `D3DCompiler_43.dll`, `xinput1_3.dll`) into `D:\AirSimEnvironments\Blocks\Blocks\WindowsNoEditor\Blocks\Binaries\Win64` without touching `C:\Windows\System32`.
3. **Backup & Correction of `settings.json`:**
   - Back up `C:\Users\madhu\Documents\AirSim\settings.json` before modifying it, validate every key against the compiled `Blocks.exe` (AirSim `v1.8.1`) schema, ensure `"DefaultVehicleState": "Disarmed"`, and synchronize `configs/airsim_settings.json`.
