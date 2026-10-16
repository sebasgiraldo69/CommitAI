import argparse
import json
from datetime import datetime
from pathlib import Path

from backend.app.ai.prompts import PROMPT_VERSION
from backend.app.ai.provider import get_provider
from backend.app.core.config import get_settings
from backend.app.core.errors import AppError
from backend.app.domain.commitments import timestamp, utc_now
from backend.app.schemas.analyses import AnalysisRequest
from backend.app.services.analyses import analyze_text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument(
        "--split",
        choices=["development", "evaluation", "all"],
        default="development",
    )
    args = parser.parse_args()

    if not args.live:
        parser.error("Agrega --live para ejecutar llamadas reales a la API.")

    root = Path(__file__).resolve().parents[1]
    dataset = json.loads(
        (root / "evals" / "casos-fase-0.json").read_text(encoding="utf-8")
    )
    settings = get_settings()
    provider = get_provider()

    output_dir = root / "evals" / "results"
    output_dir.mkdir(exist_ok=True)
    filename = utc_now().strftime("%Y%m%dT%H%M%S%fZ") + ".jsonl"
    output_path = output_dir / filename

    with output_path.open("w", encoding="utf-8") as output:
        metadata = {
            "type": "metadata",
            "started_at": timestamp(utc_now()),
            "provider": settings.ai_provider,
            "model": settings.ai_model,
            "prompt_version": PROMPT_VERSION,
            "dataset_version": dataset["schema_version"],
            "split": args.split,
        }
        output.write(json.dumps(metadata, ensure_ascii=False) + "\n")

        for case in dataset["cases"]:
            if args.split != "all" and case["split"] != args.split:
                continue

            row = {
                "type": "case",
                "id": case["id"],
                "expected": case["expected"],
            }

            try:
                result = analyze_text(
                    AnalysisRequest.model_validate(case["input"]),
                    provider,
                    datetime.fromisoformat(
                        case["evaluated_at"].replace("Z", "+00:00")
                    ),
                )
                row["actual"] = result
                row["count_matches"] = (
                    len(result["candidates"]) == case["expected"]["count"]
                )
                print(case["id"], "analizado")
            except AppError as exc:
                row["error"] = {"code": exc.code}
                print(case["id"], exc.code)

            output.write(json.dumps(row, ensure_ascii=False) + "\n")
            output.flush()

            if "error" in row:
                print("Se detiene la evaluación para revisar el error.")
                break

    print("Reporte:", output_path)


if __name__ == "__main__":
    main()