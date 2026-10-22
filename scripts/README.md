# Thư mục `scripts`

## Mục đích

Cung cấp lệnh chạy riêng tầng dữ liệu mà không cần mở giao diện Tkinter. Các script chỉ
điều phối; thuật toán chính được tái sử dụng từ `src/services`.

## Thành phần

- `profile_dataset.py`: đọc dataset và sinh báo cáo profiling để biết schema, dữ liệu thiếu,
  phân bố và vấn đề chất lượng.
- `clean_dataset.py`: đọc raw data, làm sạch/chuẩn hóa và xuất CSV cùng báo cáo cleaning.

## Cách chạy

```powershell
python scripts/profile_dataset.py <duong-dan-dataset>
python scripts/clean_dataset.py <duong-dan-dataset>
```

Chi tiết hai lệnh và đầu ra nằm trong `docs/DATA_PROCESSING.md`.

