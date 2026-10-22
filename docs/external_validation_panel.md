# `external_validation_panel.py`

## Mục đích

Đánh giá công thức đã học trên một bộ dữ liệu hoàn toàn mới, độc lập.

## Đầu vào và xử lý

- Nhận JSON Wazuh hoặc CSV sạch mới.
- JSON được làm sạch tạm bằng `DataCleaningService`.
- `EdaService` tổng hợp thành Agent/ngày và loại dòng giữ chỗ không log.
- Dùng Pipeline HQTT, HQĐT và các bậc tham khảo đã fit từ dữ liệu cũ để predict.
- So sánh dự đoán với `total_events` thực tế bằng MSE và R².

Phần này **không gọi `fit()` trên dữ liệu mới**. Biểu đồ MSE theo bậc chỉ là
tham khảo, không tự thay đổi mô hình HQĐT chính.

## Đầu ra

Bảng chỉ số MSE/R², bảng thực tế–dự đoán, Distribution Plot và biểu đồ MSE của
các bậc trên bộ dữ liệu độc lập.

## Vai trò trong pipeline

`Pipeline học từ dữ liệu cũ + dữ liệu mới → predict → đánh giá ngoài mẫu`.

