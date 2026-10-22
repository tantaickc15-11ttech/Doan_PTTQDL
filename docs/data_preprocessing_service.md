# `data_preprocessing_service.py`

## Mục đích

Làm phẳng raw JSON Wazuh thành DataFrame có kiểu ổn định và hỗ trợ tổng hợp
theo Agent/thời gian.

## Đầu vào, xử lý và đầu ra

- Input: dictionary raw alert hoặc object có thuộc tính `raw_data`.
- `flatten_alert()`: lấy Agent, Rule, Event ID, IP và người dùng từ JSON lồng.
- `build_event_dataframe()`: loại Manager `agent.id=000`, chuẩn hóa UTC, ép
  level về số và loại timestamp lỗi.
- `aggregate_by_agent()`: dùng groupby, count, nunique, mean và max.
- Output: bảng alert phẳng hoặc bảng Agent/thời gian.

Đây là tiện ích tiền xử lý dùng lại được; nó không chỉnh sửa raw alert gốc.

