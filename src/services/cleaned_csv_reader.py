"""Đọc dataset CSV sạch theo từng nhóm nhỏ cho giao diện.

KỸ THUẬT: lazy loading/phân trang bằng iterator CSV.
VẤN ĐỀ: chèn hàng trăm nghìn dòng vào Treeview một lần khiến UI treo.
TÁC DỤNG: chỉ đọc thêm một batch khi người dùng cuộn gần cuối bảng.
"""

import csv
from pathlib import Path


class CleanedCsvReader:
    """Giữ iterator CSV và chỉ trả về số dòng UI cần hiển thị."""

    REQUIRED_COLUMNS = {
        "timestamp_utc",
        "agent_name",
        "rule_id",
        "rule_level",
        "rule_description",
    }

    def __init__(self, file_path, batch_size=20):
        """Mở CSV và cấu hình số dòng tối đa trả về trong mỗi batch."""
        if batch_size <= 0:
            raise ValueError("batch_size phải lớn hơn 0.")
        self.file_path = Path(file_path)
        self.batch_size = batch_size
        self._file = None
        self._reader = None
        self.end_of_file = False
        self.reset()

    def reset(self):
        """Quay lại đầu CSV mà không đọc toàn bộ file."""
        self.close()
        if not self.file_path.exists():
            raise FileNotFoundError(f"Không tìm thấy file: {self.file_path}")

        self._file = self.file_path.open("r", encoding="utf-8", newline="")
        self._reader = csv.DictReader(self._file)
        columns = set(self._reader.fieldnames or [])
        missing_columns = self.REQUIRED_COLUMNS - columns
        if missing_columns:
            self.close()
            missing_text = ", ".join(sorted(missing_columns))
            raise ValueError(f"CSV thiếu cột bắt buộc: {missing_text}")
        self.end_of_file = False

    def read_next_batch(self):
        """Trả về tối đa batch_size dòng tiếp theo."""
        if self._reader is None or self.end_of_file:
            return []

        rows = []
        for _index in range(self.batch_size):
            try:
                rows.append(next(self._reader))
            except StopIteration:
                self.end_of_file = True
                break
        return rows

    def close(self):
        """Giải phóng file handle nếu đang mở."""
        if self._file is not None:
            self._file.close()
        self._file = None
        self._reader = None

    def __del__(self):
        """Đóng file dự phòng khi đối tượng bị Python giải phóng."""
        self.close()
