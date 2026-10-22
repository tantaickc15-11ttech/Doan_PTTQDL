# Mô hình và đánh giá

## 1. Bài toán

Biến mục tiêu là `total_events` của một Agent trong một ngày. Hệ thống xây dựng và so sánh:

- HQTT: hồi quy tuyến tính đa biến.
- HQĐT: hồi quy đa thức với bậc được đánh giá từ 1 đến 10.

Biến đầu vào gồm `agent_name` và bảy biến số: `high_level_alerts`, `unique_rules`,
`unique_event_ids`, `unique_source_ips`, `unique_users`, `avg_rule_level`,
`max_rule_level`. Dòng giữ chỗ `total_events=0` không được dùng để học.

## 2. Pipeline tiền xử lý và mô hình

```text
Dữ liệu Agent/ngày
  → biến số: SimpleImputer(median)
  → Agent: imputer(mode) + OneHotEncoder(drop="first")
  → ColumnTransformer
  → HQTT: LinearRegression
     hoặc
    HQĐT: StandardScaler + PolynomialFeatures + LinearRegression
```

- Điền khuyết học trung vị/mode từ tập train, sau đó dùng lại khi predict.
- One-Hot Encoding chuyển Agent thành cột 0/1; bỏ một nhóm tham chiếu để tránh phụ thuộc
  tuyến tính hoàn hảo giữa các cột giả.
- Pipeline bảo đảm `fit()` và `predict()` luôn dùng cùng quy tắc chuyển đổi.
- `fit()` học tiền xử lý và hệ số; `predict()` chỉ áp dụng những gì đã học.

## 3. Huấn luyện chính

`model_panel.py` lấy bảng Agent/ngày, fit HQTT trên toàn bộ mẫu có log, đánh giá các bậc
HQĐT rồi fit lại HQĐT được chọn trên toàn bộ mẫu. Hai Pipeline đã fit được giữ trong bộ nhớ
để dự đoán một dòng và kiểm thử dữ liệu mới.

Ngày không log hiển thị dự đoán 0 trên bảng nhưng không được đưa vào huấn luyện.

## 4. Thang đo

```text
MSE = trung bình((y_thực_tế - y_dự_đoán)²)
```

MSE càng gần 0 thì sai số bình phương trung bình càng nhỏ. R² càng gần 1 thì mô hình giải
thích biến thiên của target càng tốt; R² âm nghĩa là mô hình kém hơn cách dự đoán bằng giá
trị trung bình trên tập đang đánh giá.

Giao diện chỉ trình bày MSE và R² theo nội dung bài học; MAE/RMSE không hiển thị.

## 5. Ba phạm vi đánh giá

### 5.1. Trên 100% dữ liệu huấn luyện

Fit và predict trên cùng dữ liệu có log. Chỉ số cho biết độ khớp với tập đã học, chưa phải
bằng chứng độc lập về khả năng tổng quát hóa.

### 5.2. Train/Test Split 80/20

```text
train_test_split(test_size=0.2, random_state=0)
  → tạo Pipeline mới
  → fit trên 80% train
  → predict trên 80% train và 20% test
  → tính MSE/R² cho hai tập
```

20% test không được dùng để dựng lại mô hình; nó chỉ được đưa qua công thức đã học từ 80%.

### 5.3. K-Fold

`KFold(n_splits=5, shuffle=True, random_state=0)` chia dữ liệu thành năm phần. Mỗi vòng tạo
Pipeline mới, fit bốn phần và predict phần còn lại. Kết quả là MSE/R² trung bình qua các fold.

## 6. Chọn bậc hồi quy đa thức

Các bậc 1–10 được đánh giá trên cùng cách chia train/test. Bậc 1 là đường cơ sở tuyến tính;
bậc ứng viên của HQĐT được chọn từ bậc 2 trở lên theo MSE test nhỏ nhất. Chênh lệch lớn giữa
MSE train và test là dấu hiệu cần xem xét overfit; không chọn bậc chỉ vì hai đường gần nhau.

Sau khi chọn bậc, Pipeline HQĐT cuối được fit lại bằng toàn bộ dữ liệu huấn luyện để sử dụng
dự đoán thực tế.

## 7. Dự đoán một mẫu

Người dùng chọn một dòng hoặc nhập `agent_name` và các biến số. `ModelService.predict()`
đưa dữ liệu qua Pipeline đã fit rồi trả `total_events` dự đoán. One-Hot và điền khuyết chỉ
diễn ra bên trong Pipeline.

## 8. Kiểm thử bằng dữ liệu mới

`external_validation_panel.py` nhận JSON Wazuh hoặc CSV sạch mới, tổng hợp thành Agent/ngày
rồi gọi `predict()` của các Pipeline học từ dữ liệu cũ.

```text
Pipeline cũ + dữ liệu mới
  → không fit lại
  → dự đoán total_events
  → so sánh với thực tế bằng MSE/R² và Distribution Plot
```

Biểu đồ MSE theo bậc trên dữ liệu mới chỉ mang tính tham khảo; nó không tự thay đổi HQĐT
chính và không huấn luyện mô hình bằng dữ liệu mới.

## 9. Thành phần code

| File | Trách nhiệm |
|---|---|
| `model_service.py` | Tạo Pipeline, fit/predict, MSE/R², split, K-Fold và chọn bậc |
| `model_panel.py` | Điều phối huấn luyện và hiển thị bảng/biểu đồ mô hình |
| `external_validation_panel.py` | Kiểm thử Pipeline cũ trên dataset độc lập |

