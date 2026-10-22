# `outlier_service.py`

## Mục đích và đầu vào

Phát hiện ngoại lệ và mô tả hình dạng phân phối trên bảng Agent/ngày từ
`EdaService.aggregate_agent_day()`.

## Kỹ thuật

- `IQR = Q3 - Q1`; ngưỡng dưới `Q1 - 1,5×IQR`, ngưỡng trên `Q3 + 1,5×IQR`.
- Skewness: gần 0 đối xứng, dương lệch phải, âm lệch trái.
- Excess kurtosis: gần 0 tương đương phân phối chuẩn, dương nhọn hơn, âm bẹt hơn.
- KDE tạo đường mật độ khi số lượng/độ biến thiên dữ liệu cho phép.

## Đầu ra

Q1, median, Q3, IQR, hai ngưỡng, danh sách outlier, dữ liệu Boxplot/KDE,
skewness và kurtosis. Chỉ số chính hiện tại là `total_events`; không dùng
`agent_risk_index`.

Outlier IQR chỉ là bất thường thống kê, không tự động có nghĩa là tấn công.

