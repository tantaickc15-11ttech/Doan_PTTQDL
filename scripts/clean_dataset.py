"""Chạy Validation/Cleaning và xuất CSV cùng báo cáo kiểm toán."""

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
for output_stream in (sys.stdout, sys.stderr):
    if hasattr(output_stream, "reconfigure"):
        output_stream.reconfigure(encoding="utf-8")

from src.services.data_cleaning_service import DataCleaningService


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Validation và cleaning raw Wazuh dataset."
    )
    parser.add_argument("input_file", help="Đường dẫn raw JSON dataset.")
    parser.add_argument(
        "--output",
        default="data/processed/wazuh_cleaned.csv",
        help="File CSV sạch đầu ra.",
    )
    parser.add_argument(
        "--report",
        default="reports/cleaning_report.json",
        help="File JSON nhận cleaning report.",
    )
    return parser.parse_args()


def main():
    arguments = parse_arguments()

    def show_progress(rows):
        print(f"Đã xử lý {rows:,} bản ghi...", flush=True)

    report = DataCleaningService.clean_to_csv(
        arguments.input_file,
        arguments.output,
        progress_callback=show_progress,
    )
    DataCleaningService.save_report(report, arguments.report)

    print(f"Input: {report['before']['input_rows']:,}")
    print(f"Đã loại: {report['actions']['removed_unique_rows']:,}")
    print(f"Output: {report['after']['output_rows']:,}")
    print(f"CSV: {Path(arguments.output).resolve()}")
    print(f"Report: {Path(arguments.report).resolve()}")


if __name__ == "__main__":
    main()
