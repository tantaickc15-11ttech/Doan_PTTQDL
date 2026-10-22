# Dữ liệu đã xử lý `data/processed`

## Mục đích

Chứa dataset đã flatten, làm sạch và chuẩn hóa để ứng dụng thực hiện EDA, tổng hợp
Agent/ngày và huấn luyện mô hình.

## File chính

- `wazuh_cleaned.csv`: nguồn dữ liệu sạch mặc định của ứng dụng khi file tồn tại.

## Yêu cầu dữ liệu

Các trường thời gian, Agent, rule level và các thuộc tính cảnh báo phải đúng schema mô tả
trong `docs/02_DATASET_SCHEMA_DU_KIEN.md`. Các biến Agent/ngày được tạo trong service,
không phải nhập thủ công vào CSV.

File dữ liệu phát sinh có thể tạo lại từ raw data và không được commit mặc định.

