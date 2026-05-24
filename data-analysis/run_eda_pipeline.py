from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from export_for_dashboard import (
    DEFAULT_CLEAN_DATASET,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_RECOMMENDATIONS,
    export_dashboard_files,
)


ANALYSIS_ROOT = Path(__file__).resolve().parent
NOTEBOOKS_DIR = ANALYSIS_ROOT / "notebooks"
PIPELINE_STATUS_PATH = ANALYSIS_ROOT / "outputs" / "app" / "pipeline_status.json"

NOTEBOOK_GROUPS = {
    "eda": [
        "01_data_understanding.ipynb",
        "02_data_cleaning.ipynb",
        "03_exploratory_analysis.ipynb",
    ],
    "full": [
        "01_data_understanding.ipynb",
        "02_data_cleaning.ipynb",
        "03_exploratory_analysis.ipynb",
        "04_statistical_tests.ipynb",
        "05_final_insights.ipynb",
    ],
    "export-only": [],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Data Analyst notebook pipeline and generate JSON exports "
            "for Streamlit, Plotly, backend, or frontend teams."
        )
    )
    parser.add_argument(
        "--scope",
        choices=sorted(NOTEBOOK_GROUPS),
        default="eda",
        help=(
            "eda runs notebooks 01-03 then exports dashboard JSON. "
            "full runs notebooks 01-05 then exports dashboard JSON. "
            "export-only only regenerates outputs/app JSON files."
        ),
    )
    parser.add_argument(
        "--kernel",
        default="price-analytics",
        help="Jupyter kernel name used to execute notebooks.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=1800,
        help="Timeout in seconds for each notebook execution.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue executing following notebooks if one notebook fails.",
    )
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def execute_notebook(notebook_path: Path, kernel_name: str, timeout: int) -> dict[str, Any]:
    try:
        import nbformat
        from nbclient import NotebookClient
    except ImportError as exc:
        raise SystemExit(
            "Notebook execution dependencies are missing. Run: pip install -r data-analysis/requirements.txt"
        ) from exc

    if not notebook_path.exists():
        raise FileNotFoundError(f"Notebook not found: {notebook_path}")

    started_at = utc_now()
    print(f"\nExecuting notebook: {notebook_path.name}")
    notebook = nbformat.read(notebook_path, as_version=4)
    client = NotebookClient(
        notebook,
        kernel_name=kernel_name,
        timeout=timeout,
        resources={"metadata": {"path": str(ANALYSIS_ROOT)}},
    )
    client.execute()
    nbformat.write(notebook, notebook_path)
    finished_at = utc_now()
    print(f"Finished notebook: {notebook_path.name}")
    return {
        "notebook": str(notebook_path.relative_to(ANALYSIS_ROOT)),
        "status": "success",
        "started_at": started_at,
        "finished_at": finished_at,
    }


def write_pipeline_status(payload: dict[str, Any]) -> None:
    PIPELINE_STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PIPELINE_STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_pipeline(scope: str, kernel_name: str, timeout: int, continue_on_error: bool) -> dict[str, Any]:
    started_at = utc_now()
    notebook_results: list[dict[str, Any]] = []
    failed = False

    for notebook_name in NOTEBOOK_GROUPS[scope]:
        notebook_path = NOTEBOOKS_DIR / notebook_name
        try:
            result = execute_notebook(notebook_path, kernel_name, timeout)
        except Exception as exc:
            failed = True
            result = {
                "notebook": str(notebook_path.relative_to(ANALYSIS_ROOT)),
                "status": "failed",
                "started_at": utc_now(),
                "finished_at": utc_now(),
                "error": str(exc),
            }
            print(f"Notebook failed: {notebook_name}")
            print(f"Error: {exc}")
            if not continue_on_error:
                notebook_results.append(result)
                break
        notebook_results.append(result)

    if failed and not continue_on_error:
        status = "failed"
        dashboard_files: list[str] = []
    else:
        written = export_dashboard_files(
            clean_dataset=DEFAULT_CLEAN_DATASET,
            output_dir=DEFAULT_OUTPUT_DIR,
            recommendations_path=DEFAULT_RECOMMENDATIONS,
        )
        dashboard_files = [str(path.relative_to(ANALYSIS_ROOT)) for path in written]
        status = "success" if not failed else "partial_success"
        print("\nDashboard/full-stack JSON exports generated.")

    payload = {
        "pipeline": "data-analysis",
        "scope": scope,
        "status": status,
        "started_at": started_at,
        "finished_at": utc_now(),
        "notebooks": notebook_results,
        "dashboard_exports": dashboard_files,
    }
    write_pipeline_status(payload)
    return payload


def main() -> None:
    args = parse_args()
    result = run_pipeline(
        scope=args.scope,
        kernel_name=args.kernel,
        timeout=args.timeout,
        continue_on_error=args.continue_on_error,
    )
    print(f"\nPipeline status: {result['status']}")
    print(f"Status file: {PIPELINE_STATUS_PATH}")
    if result["status"] == "failed":
        sys.exit(1)


if __name__ == "__main__":
    main()
