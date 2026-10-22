# `model_service.py`

## Mục đích

Xây dựng, dự đoán và đánh giá hai mô hình cho biến mục tiêu `total_events`:
hồi quy tuyến tính đa biến (HQTT) và hồi quy đa thức (HQĐT).

## Đầu vào

Bảng Agent/ngày từ `EdaService.aggregate_agent_day()` gồm `agent_name`, bảy
biến số (`high_level_alerts`, `unique_rules`, `unique_event_ids`,
`unique_source_ips`, `unique_users`, `avg_rule_level`, `max_rule_level`) và
`total_events`. Dòng `total_events=0` là dòng giữ chỗ nên không dùng để học.

## Kỹ thuật và tác dụng

- `Pipeline` bảo đảm `fit()` và `predict()` dùng cùng quy trình.
- `SimpleImputer(median)` điền ô số thiếu bằng trung vị học từ tập train.
- One-Hot Encoding đổi `agent_name` thành cột 0/1; `drop="first"` tạo nhóm mốc
  và tránh dummy-variable trap.
- HQĐT dùng `StandardScaler` rồi `PolynomialFeatures` trước `LinearRegression`.
- `train()` học mô hình; `predict()` chỉ áp dụng mô hình đã học.
- Train/Test Split fit 80% và kiểm tra 20%; K-Fold lặp lại nhiều fold.
- Kiểm thử độc lập chỉ predict, tuyệt đối không fit dữ liệu mới.
- Chọn bậc HQĐT từ 2 trở lên theo MSE test nhỏ nhất; bậc 1 chỉ là mốc tuyến tính.

## Đầu ra

`ModelResult` chứa Pipeline đã fit, tên biến sau chuyển đổi, hệ số, bảng thực
tế–dự đoán và MSE/R². MAE/RMSE được tính nội bộ nhưng không trình bày trên UI.

## Vai trò trong pipeline

`CSV sạch → bảng Agent/ngày → ModelService → ModelPanel/ExternalValidationPanel`.

