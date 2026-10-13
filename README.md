# Đồ án Phân tích và Trực quan dữ liệu Wazuh

Ứng dụng Python desktop đọc cảnh báo Wazuh, lưu dữ liệu gốc, xây dựng dataset phân tích và trực quan hóa kết quả bằng Tkinter và Matplotlib.

## Phạm vi hiện tại

- Nhập cảnh báo từ file JSON.
- Nhận raw JSON trực tiếp từ Wazuh qua HTTP và API key.
- Chuẩn hóa cảnh báo cơ bản và lưu vào SQLite.
- Tạo event DataFrame bằng Pandas, loại Agent `000` và chuẩn hóa timestamp.
- Tổng hợp dữ liệu cơ bản theo Agent và ngày.
- Hiển thị bảng, tìm kiếm, lọc và các biểu đồ tổng quan.
- Không phát triển hoặc sử dụng chức năng Telegram.

## Hướng phát triển của đồ án mới

```text
Raw Wazuh log
→ lọc Agent endpoint
→ clean và chuẩn hóa
→ dataset phân tích
→ EDA
→ Outlier IQR
→ phân tích mối quan hệ
→ chọn biến
→ model nếu phù hợp
→ dashboard
```

Model và target chưa được chọn. Hai nội dung này chỉ được thực hiện sau khi kiểm tra dataset thật.

Service tiền xử lý hiện nằm tại `src/services/data_preprocessing_service.py`.

## Profiling raw dataset

Chạy thống kê baseline trước khi cleaning:

```powershell
python scripts/profile_dataset.py data/wazuh_dataset_30days_level7_raw.json
```

Kết quả được ghi vào `reports/profiling_report.json`. Bước này chỉ thống kê, không sửa raw data và không loại duplicate.

## Chạy baseline

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .\integration\project_config.example.conf .\integration\project_config.conf
python main.py
```

## Kiểm thử

```powershell
python -m unittest discover -s tests -v
```

## Bảo mật dữ liệu

Không commit API key, database thật hoặc raw log có thông tin nhạy cảm. Các file này đã được loại khỏi Git bằng `.gitignore`.
