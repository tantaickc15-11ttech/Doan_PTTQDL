# `data_cleaning_service.py`

## Mục đích

Kiểm tra, loại bản ghi lỗi/trùng và chuẩn hóa raw Wazuh JSON thành CSV sạch có
thể kiểm toán.

## Đầu vào và kỹ thuật

JSON Array hoặc JSON Lines được đọc streaming bởi `JsonStreamReader`.

1. Kiểm tra `id`, `timestamp`, `agent.id`, `rule.id`, `rule.level`.
2. Loại timestamp/level không hợp lệ và Manager `agent.id=000`.
3. Khử trùng theo alert ID, giữ bản hợp lệ đầu tiên.
4. Giữ rỗng các trường tùy chọn, không tự tạo dữ liệu giả.
5. Chuẩn hóa timestamp về UTC ISO 8601 và level về số.
6. Ghi file `.tmp`, chỉ thay thế file đích khi hoàn tất.

Mỗi dòng bị loại chỉ thuộc một nguyên nhân, do đó kiểm toán được:

```text
input_rows = output_rows + removed_unique_rows
```

## Đầu ra

CSV 11 cột: `timestamp_utc`, `agent_name`, `source_ip`, `src_ip`, `dst_user`,
`target_user_name`, `event_id`, `rule_id`, `rule_level`, `rule_firedtimes`,
`rule_description`; kèm báo cáo before/actions/after/audit.

Service không còn tạo `agent_risk_index` hoặc `alert_risk_level`.

## Vai trò trong pipeline

`raw Wazuh JSON → validation/dedup/normalize → wazuh_cleaned.csv → EDA`.

