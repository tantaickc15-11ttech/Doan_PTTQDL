# Thư mục `docs`

## Mục đích

Tài liệu kỹ thuật tập trung của đồ án. Nội dung được gom theo luồng nghiệp vụ để người đọc
không phải mở một tài liệu riêng cho từng file Python.

## Thứ tự đọc đề xuất

1. `APP_FLOW.md`: ứng dụng chạy theo thứ tự nào và gọi module nào.
2. `DATA_PROCESSING.md`: dữ liệu đầu vào, profiling, cleaning và schema đầu ra.
3. `EDA_ANALYSIS.md`: bộ lọc, thống kê, biểu đồ, outlier và quan hệ biến.
4. `MODEL_AND_EVALUATION.md`: Pipeline, HQTT, HQĐT, dự đoán và đánh giá.
5. `TECHNIQUE_MAPPING.md`: bảng tra cứu kỹ thuật ↔ trường dữ liệu ↔ code ↔ kiểm thử.

## Phạm vi hệ thống

Ứng dụng desktop Python/Tkinter xử lý cảnh báo Wazuh theo bốn phần: làm sạch dữ liệu,
EDA, xây dựng mô hình và kiểm thử mô hình bằng dữ liệu mới. Luồng hiện tại không sử dụng
Telegram, HTTP receiver thời gian thực, SQLite, danh sách cảnh báo vận hành hoặc trạng thái
hệ thống.

Mã nguồn là nguồn chính xác cuối cùng. Khi đổi thuật toán, schema hoặc đường dẫn dữ liệu,
các tài liệu liên quan phải được cập nhật cùng lúc.

