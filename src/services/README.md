# Tầng xử lý `src/services`

## Mục đích

Chứa logic nghiệp vụ và kỹ thuật phân tích. UI gọi các hàm tại đây để tránh trộn thuật toán
với mã dựng giao diện.

## Thành phần

- `json_stream_reader.py`: đọc JSON Wazuh dung lượng lớn theo luồng.
- `cleaned_csv_reader.py`: đọc CSV đã làm sạch và chuẩn hóa kiểu dữ liệu.
- `data_profiling_service.py`: thống kê cấu trúc, thiếu dữ liệu và chất lượng đầu vào.
- `data_cleaning_service.py`: flatten, validation, loại trùng và chuẩn hóa dữ liệu.
- `data_preprocessing_service.py`: chuẩn bị dữ liệu cho các màn hình phân tích.
- `eda_service.py`: lọc thời gian/Agent/level và tạo các bảng thống kê EDA.
- `outlier_service.py`: phát hiện ngoại lệ bằng IQR và dữ liệu cho Boxplot/KDE.
- `relationship_service.py`: Pearson, ANOVA và heatmap quan hệ giữa các biến.
- `risk_scoring_service.py`: logic điểm rủi ro kế thừa; không tạo target hiện tại.
- `model_service.py`: tổng hợp Agent/ngày, Pipeline điền khuyết + One-Hot, HQTT/HQĐT,
  dự đoán và đánh giá MSE/R².
- `__init__.py`: đánh dấu package service.

## Luồng chính

```text
reader → profiling/cleaning → preprocessing/EDA
       → relationship/outlier → model_service → UI
```

Xem `docs/TECHNIQUE_MAPPING.md` và các file `.md` cùng tên để biết chi tiết kỹ thuật.

