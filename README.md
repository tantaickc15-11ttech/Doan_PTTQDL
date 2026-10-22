# Đồ án Phân tích và Trực quan dữ liệu cảnh báo Wazuh

Ứng dụng Python desktop dùng Tkinter để làm sạch, phân tích, trực quan hóa và
xây dựng mô hình dự đoán từ log cảnh báo Wazuh.

## Trạng thái hiện tại

Ứng dụng đã hoàn thành:

1. Đọc, profiling, validation, loại trùng và chuẩn hóa raw JSON.
2. EDA, lọc dữ liệu, heatmap, outlier IQR, Pearson và ANOVA.
3. Dự đoán `total_events` bằng hồi quy tuyến tính đa biến và hồi quy đa thức.
4. Đánh giá bằng MSE/R² trên tập train, Train/Test Split, K-Fold và dữ liệu mới.

Ứng dụng không dùng Telegram, HTTP receiver thời gian thực hoặc SQLite trong
luồng hiện tại. Thư mục `integration` đã được loại bỏ.

## Flow tổng quát

```text
Raw Wazuh JSON hoặc CSV sạch
  → Profiling → Validation → Deduplication → Chuẩn hóa UTC/kiểu dữ liệu
  → data/processed/wazuh_cleaned.csv
  → Lọc EDA → Thống kê → Heatmap → IQR/KDE → Pearson/ANOVA
  → Tổng hợp một dòng cho mỗi Agent/ngày
  → Pipeline: điền khuyết + One-Hot agent_name
  → HQTT đa biến / HQĐT
  → dự đoán total_events
  → MSE/R²: train 100% → Train/Test 80/20 → K-Fold → dữ liệu mới độc lập
```

Luồng gọi hàm chi tiết: [docs/APP_FLOW.md](docs/APP_FLOW.md).

## Các tab giao diện

- **Tổng quan**: KPI và biểu đồ mô tả theo bộ lọc.
- **Quan sát dữ liệu**: bằng chứng trước/sau cleaning và bảng Agent/ngày.
- **Phân tích**: Distribution, Boxplot/IQR/KDE, Pearson và ANOVA.
- **Xây dựng mô hình**: HQTT/HQĐT, dự đoán, MSE/R², 80/20, K-Fold và chọn bậc.
- **Kiểm thử dữ liệu mới**: dùng nguyên Pipeline cũ để predict, không fit lại.

Bộ lọc hỗ trợ 7/14/30 ngày gần nhất, một ngày cụ thể và khoảng ngày. Khoảng
gần nhất được tính từ timestamp mới nhất trong dataset.

## Mô hình hiện tại

- Target: `total_events` theo Agent/ngày.
- Biến phân loại: `agent_name`, xử lý bằng One-Hot Encoding.
- Biến số: `high_level_alerts`, `unique_rules`, `unique_event_ids`,
  `unique_source_ips`, `unique_users`, `avg_rule_level`, `max_rule_level`.
- Dòng không log có `total_events=0` để biểu đồ liên tục nhưng không dùng train.

Mọi bước tiền xử lý và hồi quy nằm trong `sklearn.pipeline.Pipeline` để
`fit()` và `predict()` luôn sử dụng cùng quy tắc.

## Cấu trúc thư mục

```text
Code/
├─ main.py                 Điểm khởi chạy Tkinter
├─ src/services/           Logic dữ liệu, EDA và mô hình
├─ src/ui/                 Các cửa sổ và panel giao diện
├─ scripts/                Chạy profiling/cleaning bằng dòng lệnh
├─ data/processed/         Dataset CSV sạch dùng bởi ứng dụng
├─ reports/                Báo cáo profiling và cleaning
├─ tests/                  Kiểm thử tự động
└─ docs/                   Tài liệu hệ thống và từng file Python
```

## Cài đặt và chạy

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Nút **Thêm dữ liệu** nhận raw JSON hoặc CSV sạch. Xử lý file lớn chạy ở worker
thread để không khóa giao diện.

## Chạy xử lý bằng dòng lệnh

```powershell
python scripts/profile_dataset.py <duong-dan-raw.json>
python scripts/clean_dataset.py <duong-dan-raw.json>
```

## Kiểm thử

```powershell
python -m unittest discover -s tests -v
```

## Bản đồ tài liệu

- [APP_FLOW.md](docs/APP_FLOW.md): flow vận hành và call flow toàn ứng dụng.
- [TECHNIQUE_MAPPING.md](docs/TECHNIQUE_MAPPING.md): kỹ thuật, biến và module.
- [DATA_PROCESSING.md](docs/DATA_PROCESSING.md): đọc, profiling và làm sạch dữ liệu.
- [EDA_ANALYSIS.md](docs/EDA_ANALYSIS.md): EDA, ngoại lệ và quan hệ biến.
- [MODEL_AND_EVALUATION.md](docs/MODEL_AND_EVALUATION.md): Pipeline, mô hình và đánh giá.
- [README.md](docs/README.md): thứ tự đọc và phạm vi của bộ tài liệu.

Tài liệu được gom theo flow nghiệp vụ thay vì tách một file `.md` cho từng file Python.

## Bảo mật dữ liệu

Không commit raw log có thông tin nhạy cảm, khóa truy cập hoặc dữ liệu hệ thống
thật. Chỉ dùng dataset đã kiểm tra và ẩn thông tin khi đưa vào báo cáo.

