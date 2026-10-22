# Thư mục `data`

## Mục đích

Quản lý dữ liệu đầu vào, dữ liệu sau làm sạch và bộ dữ liệu kiểm thử độc lập của đồ án.
Ứng dụng chỉ đọc dữ liệu tại đây; mã xử lý nằm trong `src/services`.

## Thành phần

- `sample_alerts.json`: dữ liệu mẫu nhỏ để ứng dụng có thể khởi động và minh họa.
- `raw/`: log Wazuh gốc, chưa làm sạch.
- `processed/`: CSV đã chuẩn hóa để EDA và huấn luyện mô hình.
- `alerts.db`: dữ liệu cục bộ phát sinh nếu có; không thuộc luồng chính hiện tại.
- Các CSV đặt trực tiếp trong `data/`: dữ liệu làm việc cục bộ, bị loại khỏi Git.

## Luồng dữ liệu

```text
raw JSON/CSV
  → profiling và làm sạch
  → processed/wazuh_cleaned.csv
  → EDA và huấn luyện HQTT/HQĐT

CSV kiểm thử do người dùng chọn
  → chuẩn hóa đúng schema
  → Pipeline đã fit từ dữ liệu cũ
  → dự đoán và tính MSE/R², không fit lại
```

## Lưu ý

Dữ liệu Wazuh thật có thể chứa thông tin hệ thống nhạy cảm. `.gitignore` không cho commit
CSV, database, raw JSON và dữ liệu kiểm thử; chỉ các README và dữ liệu mẫu an toàn được lưu.

