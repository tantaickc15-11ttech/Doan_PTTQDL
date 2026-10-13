# `data_cleaning_service.py`

## Mục đích

Validation, loại dòng không hợp lệ, loại duplicate và chuẩn hóa raw Wazuh JSON thành CSV.

## Quy tắc

1. Kiểm tra `id`, `timestamp`, `agent.id`, `rule.id`, `rule.level`.
2. Loại timestamp hoặc Level không chuyển đổi được.
3. Loại Agent `000`.
4. Với ID trùng, giữ bản ghi hợp lệ xuất hiện đầu tiên.
5. Missing tùy chọn được giữ rỗng, không điền giá trị giả.
6. Timestamp được chuẩn hóa về UTC ISO 8601.

Mỗi dòng bị loại chỉ thuộc một nguyên nhân đầu tiên, vì vậy có thể kiểm toán:

```text
input_rows = output_rows + removed_unique_rows
```

## Đầu ra

- CSV gồm 20 cột phục vụ EDA.
- Dictionary cleaning report.
- Ví dụ before/after đã che giá trị nhạy cảm.
