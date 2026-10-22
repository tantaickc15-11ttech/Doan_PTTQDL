# Phạm vi và kiến trúc hiện tại

## Phạm vi đồ án

Ứng dụng desktop Python phân tích và trực quan dữ liệu cảnh báo Wazuh theo bốn
tầng: làm sạch dữ liệu, EDA, xây dựng mô hình và trình bày/kiểm thử.

Đồ án hiện tại không sử dụng Telegram, HTTP receiver thời gian thực, SQLite,
danh sách cảnh báo vận hành hoặc trạng thái hệ thống. Thư mục `integration` đã
được loại bỏ vì không tham gia luồng phân tích.

## Thành phần đang sử dụng

| Thành phần | Vai trò |
|---|---|
| `JsonStreamReader` | Đọc JSON Array/JSON Lines lớn theo streaming |
| `DataProfilingService` | Thống kê chất lượng raw dataset trước cleaning |
| `DataCleaningService` | Validation, dedup, chuẩn hóa và xuất CSV sạch |
| `EdaService` | Lọc, thống kê và tổng hợp Agent/ngày |
| `OutlierService` | IQR, KDE, skewness và kurtosis |
| `RelationshipService` | Pearson, p-value và ANOVA |
| `ModelService` | Pipeline HQTT/HQĐT, dự đoán và đánh giá |
| `MainWindow` và các panel | Giao diện trình bày kết quả |

## Chức năng đã hoàn thành

- Bộ lọc 7/14/30 ngày gần nhất, một ngày và khoảng ngày.
- Thống kê mô tả, các biểu đồ EDA và heatmap mọi Alert Level thực có.
- Phân tích ngoại lệ và quan hệ giữa biến.
- HQTT đa biến và HQĐT có lựa chọn bậc.
- MSE/R² trên tập train, Train/Test Split, K-Fold và dữ liệu độc lập mới.

Mỗi file Python có xử lý được mô tả bằng một file cùng tên trong `docs/`.

