"""Điểm bắt đầu của ứng dụng phân tích cảnh báo Wazuh.

File này chỉ khởi tạo Tkinter; toàn bộ xử lý dữ liệu nằm trong services và UI.
"""

from src.ui.main_window import MainWindow


def main():
    """Khởi tạo cửa sổ phân tích chính."""
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
