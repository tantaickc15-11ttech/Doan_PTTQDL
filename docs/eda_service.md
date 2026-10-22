# `eda_service.py`

## Mục đích

Đọc CSV sạch, áp dụng bộ lọc và tạo số liệu thống nhất cho EDA, quan hệ biến và
mô hình.

## Đầu vào

CSV sạch có timestamp UTC, Agent, Rule, Alert Level, Event ID, IP, người dùng
và mô tả Rule.

## Xử lý chính

- Chuẩn hóa timestamp, kiểu số và kiểu chuỗi.
- Ghép các trường IP/người dùng tương đương thành biến phân tích.
- Lọc theo Agent, Alert Level, 7/14/30 ngày gần nhất, một ngày hoặc khoảng ngày.
- Khoảng gần nhất neo theo timestamp lớn nhất trong dataset, không theo hôm nay.
- Tính KPI, đếm theo ngày/level và Top Agent/Rule/Event ID.
- Heatmap dùng tất cả Alert Level thực tế sau lọc; tổ hợp thiếu được điền 0.
- Tổng hợp Agent/ngày bằng count, sum, nunique, mean và max.

## Đầu ra

Bảng Agent/ngày gồm `total_events`, `high_level_alerts`, các nhóm level,
`unique_rules`, `unique_event_ids`, `unique_source_ips`, `unique_users`,
`avg_rule_level`, `max_rule_level`. Dòng không log có `total_events=0` để biểu
đồ liên tục nhưng bị `ModelService` loại trước khi huấn luyện.

## Vai trò trong pipeline

`wazuh_cleaned.csv → EdaService → EdaPanel/Outlier/Relationship/Model`.

