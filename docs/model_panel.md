# `model_panel.py`

## Mục đích

Điều phối và hiển thị phần xây dựng HQTT/HQĐT. Phép tính nằm trong
`ModelService`; file này không tự cài đặt công thức hồi quy.

## Đầu vào và xử lý

- Nạp CSV sạch và lấy bảng Agent/ngày từ `EdaService`.
- Fit mô hình chính trên 100% mẫu có log.
- So sánh bậc 1–10, chọn HQĐT theo MSE test nhỏ nhất và fit lại trên 100% mẫu.
- Chạy đánh giá trên tập train, Train/Test Split 80/20 và K-Fold.
- Tạo Pipeline bậc tham khảo từ dữ liệu cũ cho tab kiểm thử độc lập.
- Nhận một dòng có sẵn hoặc dữ liệu nhập tay để dự đoán.

## Đầu ra giao diện

Bảng thực tế/HQTT/HQĐT, hai khung dự đoán, bảng MSE/R², Distribution Plot và
đồ thị MSE train/test theo bậc. Ngày không log hiển thị dự đoán 0 và không được
đưa vào huấn luyện.

## Vai trò trong pipeline

Là lớp trình bày của Tầng 3 – Model và cung cấp các Pipeline đã fit cho tab
kiểm thử dữ liệu mới.

