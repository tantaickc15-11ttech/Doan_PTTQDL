# `cleaned_csv_reader.py`

## Mục đích

Đọc danh sách log sau Cleaning theo từng batch 20 dòng, tránh nạp toàn bộ CSV 492.696 dòng vào RAM.

## Hàm chính

- `reset()`: mở lại CSV từ đầu.
- `read_next_batch()`: trả về tối đa 20 dictionary tiếp theo.
- `close()`: đóng file handle.

## Vai trò trong UI

UI tải 20 dòng đầu. Khi thanh cuộn đến cuối, UI gọi `read_next_batch()` để nối thêm 20 dòng. Bấm một dòng sẽ hiển thị toàn bộ các cột của bản ghi sạch.
