# `json_stream_reader.py`

## Mục đích

Đọc tuần tự JSON Array lớn hoặc JSON Lines mà không nạp toàn bộ file vào RAM.

## Đầu vào và đầu ra

- Đầu vào: đường dẫn file JSON và kích thước chunk.
- Đầu ra: iterator, mỗi lần trả về một dictionary.

## Hàm chính

- `iter_records()`: nhận diện format và yield từng bản ghi.
- `detect_format()`: xác định `json_array` hoặc `json_lines`.

## Vai trò trong pipeline

Đây là đầu vào của profiling và cleaning. Module chỉ đọc, không thay đổi raw dataset.
