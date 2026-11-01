# WILDLIFE UAV — Intelligent Navigation and Monitoring System
## Autonomous Mission-Control Frontend Dashboard

Frontend application for the research project:
> **"An Intelligent Hierarchical UAV Navigation Framework for Safe and Energy-Efficient Wildlife Monitoring in Dynamic Environments."**

---

## 1. Overview & Research Architecture
This dashboard serves as the central mission-control interface bridging:
- **Part 1 (Global Route Planning)**: Genetic Algorithm (GA), 2-Opt local tour improvement, and A* obstacle path generation.
- **Part 2 (Local Movement Control & Safety)**: Twin Delayed Deep Deterministic Policy Gradient (TD3) local neural policy, Adaptive Fuzzy Logic (AFL) dynamic collision avoidance supervisor, and AirSim multirotor execution.

```
+------------------------------------------------------------------------------+
|                     WILDLIFE UAV DASHBOARD (REACT + TS)                      |
|                                                                              |
|  [ Mission Config ]       [ Global Planner ]       [ Live Telemetry / Safety] |
+---------+------------------------+-------------------------------+-----------+
          |                        |                               |
     HTTP REST               HTTP REST                        WebSocket / HTTP
(POST /api/planner/plan) (GET /api/planner/route)      (ws://localhost:8001/ws/telemetry)
          |                        |                               |
          v                        v                               v
+-----------------------------+               +--------------------------------+
|       BACKEND PART 1        |               |         BACKEND PART 2         |
| Global Route Planner        |               | Local RL Controller & Safety   |
| (GA + 2-Opt + A* in ENU)    |               | (TD3 + AFL + AirSim NED)       |
+-----------------------------+               +--------------------------------+
```

---

## 2. Technology Stack
- **Framework**: [React 19](https://react.dev/) + [Vite 8](https://vite.dev/)
- **Language**: [TypeScript](https://www.typescriptlang.org/) (Strict Mode)
- **Styling**: [Tailwind CSS 3](https://tailwindcss.com/) with Tactical Dark Mission-Control Theme
- **Icons**: [Lucide React](https://lucide.dev/)
- **Routing**: [React Router DOM v7](https://reactrouter.com/)
- **Data Analytics & Charts**: [Recharts v3](https://recharts.org/)
- **State Management**: [Zustand v5](https://github.com/pmndrs/zustand)
- **Form Validation**: [React Hook Form](https://react-hook-form.com/) + [Zod](https://zod.dev/)
- **HTTP & Telemetry**: [Axios](https://axios-http.com/) + Native WebSocket Client (with auto-reconnect and stale detection)
- **Testing**: [Vitest](https://vitest.dev/) + [React Testing Library](https://testing-library.com/)

---

## 3. Quick Start & Development Commands

### Prerequisites
- Node.js `>= 20.0.0` (Tested on `v24.16.0`)
- npm `>= 10.0.0` (Tested on `11.13.0`)

### Installation
From the root repository:
```bash
cd frontend
npm install
```

### Run in Development Mode
```bash
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

### Run Automated Unit and Integration Tests
```bash
npm test
```
To run tests in interactive watch mode:
```bash
npm run test:watch
```

### Production Build
```bash
npm run build
```
The compiled output is located in `frontend/dist/`. To preview the production bundle locally:
```bash
npm run preview
```

---

## 4. Environment Variables Configuration
Configure backend URLs in `.env` (or copy from `.env.example`):

```bash
# Global Route Planning API (GA + 2-Opt + A*)
VITE_GLOBAL_API_URL=http://localhost:8000

# Local Controller & AirSim Safety API (TD3 + AFL)
VITE_CONTROL_API_URL=http://localhost:8001

# WebSocket URL for real-time UAV telemetry stream
VITE_WS_URL=ws://localhost:8001/ws/telemetry

# Initial default mode: 'true' for standalone demo mode, 'false' for live backend
VITE_DEMO_MODE=true
```

---

## 5. Standalone Demo Mode vs. Live Backend Mode

| Feature | Demo Mode (`VITE_DEMO_MODE=true`) | Live Mode (`VITE_DEMO_MODE=false`) |
|---|---|---|
| **Indicator** | Purple `[SIM DEMO]` badge pulsing in Topbar & Sidebar | Green `[LIVE BACKEND]` badge in Topbar & Sidebar |
| **Route Generation** | Simulates GA search with latency (~800ms) and mock route | Real HTTP call `POST /api/planner/plan` |
| **Telemetry Stream** | Internal tick generator advances UAV along waypoints at 2Hz | Real WebSocket stream (`ws://.../ws/telemetry`) |
| **Safety Events** | Interactive demonstration of TD3 vs AFL adjustments | Actual AFL safety supervisor telemetry events |
| **Simulator Commands** | Local mock status toggles | Calls `POST /api/mission/*` and `POST /api/simulation/*` |
| **Failure Handling** | Self-contained, zero external dependency | Reports connection offline status truthfully |

You can toggle between **Demo Mode** and **Live Mode** at any moment via the button in the top navigation bar or the **Settings** page.

---

## 6. Coordinate Conventions & Transformations
Following `INTEGRATION_GUIDE.md`:
1. **Global Planner Frame (`ENU_ALT_UP`)**:
   - $X$: East (metres)
   - $Y$: North (metres)
   - $Z$: Altitude positive **UP** (metres)
2. **AirSim Multirotor Frame (`NED`)**:
   - $\text{North} = +Y_{\text{planner}}$
   - $\text{East} = +X_{\text{planner}}$
   - $\text{Down} = -Z_{\text{planner}}$

The shared transformation utility in `src/utils/coordinateUtils.ts` (`plannerToAirSim` and `airSimToPlanner`) ensures consistency across:
- Waypoint and obstacle placement
- Interactive 2D SVG canvas rendering
- High-frequency telemetry packets

---

## 7. Application Page Directory
1. **Overview (`/`)**: High-level telemetry badges, active flight state, spatial 2D trajectory overview, and activity audit feed.
2. **Mission Configuration (`/mission-config`)**: Configure environment bounds, start/destination coordinates, monitoring waypoints with priority tags, geometric obstacles (circles & rectangles), and GA hyperparameters with strict Zod validation.
3. **Global Route Planner (`/planner`)**: Large interactive 2D environment with pan, zoom, fit-to-viewport, layer toggles (obstacles, safety buffers, initial route vs GA+2-Opt route, intermediate points), and Recharts GA fitness evolution history.
4. **Live UAV Monitoring (`/monitoring`)**: Live telemetry panels ($X, Y, Z, V_x, V_y, V_z$, speed, battery, flight state), 2D radar tracking, flight controls with confirmation modals, and AirSim camera status.
5. **Safety & Obstacle Monitoring (`/safety`)**: Visual representation of the Adaptive Fuzzy Logic (AFL) layer, proximity radar with safe ($>6.0m$), warning ($2.5m - 6.0m$), and critical ($<2.5m$) zones, TD3 vs final command diff vector, and intervention history table.
6. **Mission Analytics (`/analytics`)**: Post-mission evaluation charts: planned vs actual flown distance, velocity/altitude flight profiles, clearance margins, and kinematic energy proxy ($\int \|\mathbf{a}\|^2 dt$).
7. **Experiment Comparison (`/comparison`)**: Benchmark comparison table and bar charts comparing:
   - *Config A: Baseline Waypoint Navigation*
   - *Config B: TD3 without Fuzzy Safety*
   - *Config C: TD3 with Adaptive Fuzzy Safety (Proposed)*
8. **Settings (`/settings`)**: Configurable REST/WebSocket URLs, measurement unit selector, coordinate system preferences, and default restore actions.

---

## 8. Automated Test Summary
Verified with **Vitest** and **React Testing Library**:
- `src/test/navigation.test.tsx`: Route mounting and sidebar page navigation across all 8 pages.
- `src/test/validators.test.ts`: Zod schema verification for environment, waypoints, circular/rectangular hazards, and probabilities.
- `src/test/coordinateUtils.test.ts`: ENU $\leftrightarrow$ AirSim NED conversions and SVG canvas projections.
- `src/test/missionStore.test.ts`: Zustand store operations (add, edit, remove waypoints/hazards, route plan state).
- `src/test/telemetry.test.ts`: Telemetry packet ingestion, bounded array buffer capping (max 30 items), and demo packet generation.
- `src/test/components.test.tsx`: Confirmation modals, loading spinners, error boundaries, empty states, and metric cards.

Execute all tests:
```bash
npm test
```
Result: **30 passed across 6 test suites.**
