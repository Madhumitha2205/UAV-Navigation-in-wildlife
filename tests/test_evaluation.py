"""Unit tests for MissionRunner and ComparativeEvaluator metrics."""

from pathlib import Path
from backend.intelligent_control.config import ControllerConfig, SafetyConfig
from backend.intelligent_control.evaluation import ComparativeEvaluator
from backend.intelligent_control.mission_runner import MissionRunner
from backend.intelligent_control.route_loader import load_global_route
from backend.intelligent_control.td3_agent import TD3Agent


def test_mission_runner_and_evaluation_metrics(tmp_path: Path):
    ctrl_cfg = ControllerConfig()
    ctrl_cfg.paths.log_dir = str(tmp_path / "logs")
    ctrl_cfg.paths.output_dir = str(tmp_path / "outputs")
    safety_cfg = SafetyConfig()

    agent = TD3Agent(td3_config=ctrl_cfg.td3, limits_config=ctrl_cfg.vehicle_limits)
    agent.is_trained = True

    route = load_global_route("configs/sample_global_route.json")
    runner = MissionRunner(ctrl_cfg, safety_cfg, td3_agent=agent)

    res = runner.run_mission(
        route=route,
        nav_mode="TD3_WITH_FUZZY_SAFETY",
        execution_backend="kinematic",
        include_dynamic_obstacles=True,
        seed=42,
        process_noise_std_mps=0.0,
    )
    assert res.execution_backend == "kinematic_dry_run"
    assert res.total_travelled_distance_m > 0.0
    assert res.estimated_energy_proxy_joules > 0.0
    assert "NOT physical battery measurement" in res.energy_proxy_model_note

    evaluator = ComparativeEvaluator(ctrl_cfg, safety_cfg, td3_agent=agent)
    report = evaluator.run_comparative_experiments(route=route, seeds=[101, 102])
    assert len(report["configurations"]) == 3
    assert Path(report["artifacts"]["trials_csv"]).exists()
    assert Path(report["artifacts"]["summary_csv"]).exists()
    assert Path(report["artifacts"]["trajectory_plot"]).exists()
    assert Path(report["artifacts"]["metrics_plot"]).exists()
