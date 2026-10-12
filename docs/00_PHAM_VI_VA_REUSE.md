# Phạm vi và phần tái sử dụng

## Phạm vi mới

Đồ án tập trung vào phân tích và trực quan dữ liệu cảnh báo Wazuh bằng ứng dụng Python desktop. Telegram không thuộc phạm vi phát triển mới.

## Phần tái sử dụng từ đồ án Lập trình Python

| Thành phần | Cách sử dụng |
|---|---|
| `AlertReader` | Giữ làm đầu vào JSON, sau đó mở rộng cho dữ liệu lớn |
| `Alert` | Giữ model cảnh báo cơ bản và raw JSON |
| `DatabaseService` | Giữ bảng raw event và khả năng tìm kiếm |
| `WazuhReceiver` | Giữ chức năng nhận log thật |
| `AnalysisService` | Giữ thống kê cơ bản, tiếp tục mở rộng EDA |
| `MainWindow` | Giữ khung Tkinter và Matplotlib |
| Bộ kiểm thử | Giữ làm kiểm thử hồi quy |

## Phần không tái sử dụng

- Telegram service và Telegram integration.
- Báo cáo, slide và video của môn học cũ.
- Database, API key và cấu hình thật.

## Phần cần xây mới

- Tiền xử lý bằng Pandas/NumPy.
- Dataset tổng hợp theo Agent và thời gian.
- Bộ lọc 3/7/15/30/90 ngày.
- Thống kê mô tả.
- Boxplot và IQR Outlier.
- Correlation, ANOVA và chọn biến.
- Model hồi quy sau khi chốt target.

