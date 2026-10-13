# `data_profiling_service.py`

## Mục đích

Đo baseline chất lượng raw dataset trước khi cleaning.

## Chỉ số

- Tổng dòng, số Agent và khoảng timestamp hợp lệ.
- Số lượng và tỷ lệ missing theo trường.
- Kiểu dữ liệu thực tế theo trường.
- Duplicate `alert.id`.
- Timestamp và `rule.level` không hợp lệ.

## Hàm chính

- `profile()`: duyệt dataset một lần và trả về dictionary báo cáo.
- `save_report()`: ghi báo cáo ra JSON UTF-8.

## Nguyên tắc kiểm toán

Module không loại duplicate, không sửa missing và luôn ghi `cleaning_applied = false`.
