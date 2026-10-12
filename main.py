"""Điểm bắt đầu của ứng dụng phân tích cảnh báo Wazuh."""

from pathlib import Path

from src.services.database_service import DatabaseService
from src.ui.main_window import MainWindow


BASE_DIR = Path(__file__).resolve().parent


def main():
    """Khởi tạo cấu hình, cơ sở dữ liệu và cửa sổ chính."""
    database = DatabaseService(BASE_DIR / "data" / "alerts.db")
    database.initialize()

    app = MainWindow(
        database=database,
        sample_file=BASE_DIR / "data" / "sample_alerts.json",
    )
    app.mainloop()


if __name__ == "__main__":
    main()
