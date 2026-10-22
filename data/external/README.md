# Dữ liệu kiểm thử độc lập `data/external`

## Mục đích

Chứa bộ dữ liệu mới hoàn toàn dùng để kiểm tra khả năng dự đoán của mô hình đã học từ
bộ dữ liệu cũ.

## Cách sử dụng

1. Chuẩn hóa file mới về cùng schema với dữ liệu huấn luyện.
2. Nạp file tại tab **Kiểm thử dữ liệu mới**.
3. Ứng dụng dùng nguyên Pipeline HQTT/HQĐT đã fit; không gọi `fit()` trên dữ liệu mới.
4. So sánh `total_events` thực tế và dự đoán bằng MSE, R² và biểu đồ phân phối.

Nếu Agent mới chưa từng xuất hiện khi huấn luyện, One-Hot Encoder xử lý như nhóm chưa biết.
Các CSV kiểm thử bị loại khỏi Git để tránh công khai dữ liệu thật.

