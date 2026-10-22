# Thư mục `tests`

## Mục đích

Chứa kiểm thử tự động cho tầng service. Dữ liệu kiểm thử nhỏ được tạo trong test, không phụ
thuộc dataset Wazuh thật và không mở giao diện Tkinter.

## Thành phần

- `test_json_stream_reader.py`, `test_cleaned_csv_reader.py`: kiểm tra bộ đọc dữ liệu.
- `test_data_profiling.py`, `test_data_cleaning.py`, `test_data_preprocessing.py`: kiểm tra
  profiling, cleaning và chuẩn bị dữ liệu.
- `test_eda_service.py`, `test_outlier_service.py`, `test_relationship_service.py`: kiểm tra
  thống kê EDA, IQR, Pearson và ANOVA.
- `test_model_service.py`: kiểm tra tổng hợp Agent/ngày, Pipeline, dự đoán và đánh giá mô hình.
- `test_risk_scoring_service.py`: kiểm tra logic risk scoring kế thừa.
- `__init__.py`: đánh dấu package kiểm thử.

## Cách chạy

```powershell
python -m unittest discover -s tests -v
```

Test giúp phát hiện lỗi hồi quy khi sửa code; không tham gia vào luồng chạy của ứng dụng.

