# Flow vận hành ứng dụng

Đây là điểm đọc đầu tiên để hiểu ứng dụng chạy theo thứ tự nào, dùng kỹ thuật
gì và gọi đến file/hàm nào. Chi tiết từng module nằm trong file `.md` cùng tên.

## 1. Khởi động

```text
main.py:main()
  → MainWindow.__init__()
    → tạo 5 tab
    → khởi tạo EdaPanel, ModelPanel, ExternalValidationPanel
    → nạp dataset/báo cáo đang có
  → Tk.mainloop()
```

## 2. Nhập raw JSON và làm sạch

```text
MainWindow.import_json()
  → worker _process_dataset_worker()
    → DataProfilingService.profile()
      → JsonStreamReader.iter_records()
    → DataCleaningService.clean_to_csv()
      → đọc streaming
      → kiểm tra trường bắt buộc
      → loại Manager agent.id=000
      → chuẩn hóa UTC và kiểu số
      → loại alert ID trùng
      → ghi file tạm rồi replace
  → queue trả kết quả về main thread
  → refresh_data_views()
```

Kỹ thuật: streaming theo chunk, one-pass profiling, validation, deduplication,
chuẩn hóa và atomic write. Đầu ra là `data/processed/wazuh_cleaned.csv`.

## 3. Nhập CSV sạch

```text
MainWindow.import_json()
  → _process_cleaned_csv_worker()
  → EdaService.load_dataset() kiểm tra schema/kiểu
  → đưa vào dataset làm việc
  → refresh_data_views()
```

CSV sạch không chạy lại raw cleaning. Bảng log dùng `CleanedCsvReader` để đọc
theo batch, tránh nạp toàn bộ file vào Treeview.

## 4. Lọc và EDA tổng quan

```text
EdaPanel.reload_dataset()
  → EdaService.load_dataset()
  → EdaPanel.apply_filters()
    → EdaService.filter_data()
    → overview/daily_counts/level_counts
    → top_rules/top_agents/top_event_ids
    → agent_level_counts() cho heatmap
    → aggregate_agent_day()
```

Kỹ thuật: ép kiểu, Boolean filtering, groupby, count, nunique, mean, median,
pivot/unstack và reindex. Bộ lọc 7/14/30 ngày neo theo ngày mới nhất trong file.

## 5. Phân tích ngoại lệ

```text
Bảng Agent/ngày
  → EdaPanel._update_outlier()
  → OutlierService
    → Q1, median, Q3 và ngưỡng 1,5×IQR
    → skewness, excess kurtosis và KDE
  → Boxplot + Distribution Plot + bảng bằng chứng
```

Outlier IQR là bất thường thống kê, không tự động có nghĩa là tấn công.

## 6. Quan hệ giữa biến

```text
Bảng Agent/ngày
  → RelationshipService.correlation_with()
    → Pearson r + p-value cho biến số
  → RelationshipService.anova_by_agent()
    → nhóm total_events theo agent_name
    → one-way ANOVA: F + p-value
  → EdaPanel hiển thị bảng/heatmap/scatter/ANOVA
```

Pearson dùng cho biến số; ANOVA dùng cho `agent_name` phân loại. Các kết quả
thể hiện liên hệ thống kê, không chứng minh quan hệ nhân quả.

## 7. Huấn luyện mô hình

```text
ModelPanel.reload_dataset()
  → EdaService.load_dataset()
  → EdaService.aggregate_agent_day()
  → ModelPanel.train_model()
    → ModelService.train(summary)                  [HQTT]
    → ModelService.select_polynomial_degree()      [bậc 1–10]
    → ModelService.train(summary, selected_degree) [HQĐT]
```

Flow con của `ModelService.train()`:

```text
Loại dòng giữ chỗ total_events=0
  → tách X và y=total_events
  → nhánh số: SimpleImputer(median)
  → HQĐT thêm StandardScaler + PolynomialFeatures
  → nhánh Agent: imputer(mode) + OneHotEncoder(drop="first")
  → ColumnTransformer ghép hai nhánh
  → LinearRegression.fit(X, y)
  → predict và tính residual, MSE, R²
```

`fit()` học quy tắc tiền xử lý và hệ số. `predict()` chỉ áp dụng những gì đã
học. One-Hot chuyển Agent thành cột 0/1; Agent tham chiếu có toàn số 0.

## 8. Đánh giá mô hình

### Tập huấn luyện 100%

Fit và predict cùng dữ liệu có log. Chỉ số mô tả độ khớp tập đã học, chưa phải
kiểm thử độc lập.

### Train/Test Split

```text
train_test_split(test_size=0.2, random_state=0)
  → fit Pipeline mới trên 80% train
  → predict 20% test, không fit test
  → MSE/R² train và test
```

### K-Fold

```text
KFold(n_splits=5, shuffle=True, random_state=0)
  → mỗi fold tạo Pipeline mới
  → fit train, predict test
  → lấy MSE/R² trung bình
```

### Chọn bậc HQĐT

Các bậc 1–10 dùng cùng một split. Chọn từ bậc 2 trở lên theo MSE test nhỏ nhất;
độ chênh train/test được quan sát để nhận biết overfit.

## 9. Dự đoán một mẫu

```text
Chọn dòng hoặc nhập biến
  → ModelPanel.predict_one()/predict_polynomial()
  → ModelService.predict()
  → Pipeline cũ transform + regression.predict()
  → total_events dự đoán
```

## 10. Kiểm thử dữ liệu mới

```text
ExternalValidationPanel.load_external_dataset()
  → worker _load_worker()
  → JSON: cleaning tạm / CSV: load trực tiếp
  → EdaService.aggregate_agent_day()
  → ModelService.evaluate_external()
    → Pipeline học từ dữ liệu cũ.predict()
    → MSE/R² trên total_events mới
  → bảng và biểu đồ
```

Flow này không gọi `fit()` trên dữ liệu mới. Biểu đồ bậc 1–10 chỉ tham khảo,
không tự đổi mô hình HQĐT chính.

## 11. Chạy không qua giao diện

- `scripts/profile_dataset.py` gọi `DataProfilingService`.
- `scripts/clean_dataset.py` gọi `DataCleaningService`.

Hai script dùng cùng service với GUI nên không tạo quy tắc xử lý thứ hai.

## 12. Bản đồ trách nhiệm

| Nhóm | Điều phối/hiển thị | Tính toán |
|---|---|---|
| Nhập và làm sạch | `main_window.py` | `json_stream_reader.py`, `data_profiling_service.py`, `data_cleaning_service.py` |
| EDA | `eda_panel.py` | `eda_service.py` |
| Ngoại lệ | `eda_panel.py` | `outlier_service.py` |
| Quan hệ biến | `eda_panel.py` | `relationship_service.py` |
| Xây mô hình | `model_panel.py` | `model_service.py` |
| Dữ liệu mới | `external_validation_panel.py` | cleaning, EDA và `model_service.py` |

