"""Structured Logging Utilities for Training, Safety Interventions, and Missions."""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def setup_logger(name: str = "intelligent_control", log_file: Optional[str | Path] = None) -> logging.Logger:
    """Configure a console and optional file logger."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        logger.addHandler(ch)
        if log_file is not None:
            path = Path(log_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            fh = logging.FileHandler(path, encoding="utf-8")
            fh.setFormatter(fmt)
            logger.addHandler(fh)
    return logger


def save_csv_records(path: str | Path, records: List[Dict[str, Any]]) -> Path:
    """Write a list of flat dictionaries to a CSV file."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        with out_path.open("w", encoding="utf-8", newline="") as f:
            f.write("")
        return out_path

    fieldnames = list(records[0].keys())
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in records:
            writer.writerow(row)
    return out_path


def save_json_report(path: str | Path, data: Dict[str, Any]) -> Path:
    """Write a structured dictionary to a formatted JSON file."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return out_path
