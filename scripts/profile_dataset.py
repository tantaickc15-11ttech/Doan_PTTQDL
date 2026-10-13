"""Chạy profiling raw Wazuh dataset và xuất báo cáo JSON."""

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
for output_stream in (sys.stdout, sys.stderr):
    if hasattr(output_stream, "reconfigure"):
        output_stream.reconfigure(encoding="utf-8")

from src.services.data_profiling_service import DataProfilingService


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Thống kê raw Wazuh dataset trước cleaning."
    )
    parser.add_argument("input_file", help="Đường dẫn raw JSON dataset.")
    parser.add_argument(
        "--output",
        default="reports/profiling_report.json",
        help="File JSON nhận báo cáo profiling.",
    )
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    source_path = Path(arguments.input_file)
    output_path = Path(arguments.output)

    def show_progress(rows):
        print(f"Đã profiling {rows:,} bản ghi...", flush=True)

    report = DataProfilingService.profile(
        source_path,
        progress_callback=show_progress,
    )
    DataProfilingService.save_report(report, output_path)

    print(f"Hoàn tất: {report['input']['total_rows']:,} bản ghi")
    print(f"Báo cáo: {output_path.resolve()}")


if __name__ == "__main__":
    main()
