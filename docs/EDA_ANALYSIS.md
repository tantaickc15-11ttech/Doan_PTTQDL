# Phân tích khám phá dữ liệu

## 1. Nguồn và đơn vị phân tích

`eda_service.py` đọc CSV sạch. Dashboard tổng quan dùng từng alert; Outlier, Pearson,
ANOVA và mô hình dùng bảng một dòng cho mỗi Agent/ngày.

```text
wazuh_cleaned.csv
  → EdaService
  → lọc và thống kê tổng quan
  → aggregate_agent_day()
  → OutlierService / RelationshipService / ModelService
```

## 2. Chuẩn hóa và bộ lọc

- Chuẩn hóa timestamp, biến số và chuỗi.
- Hợp nhất các trường IP/user tương đương thành biến phân tích.
- Lọc theo Agent và mọi Alert Level thực có.
- Chọn 7/14/30 ngày gần nhất, một ngày hoặc khoảng ngày.
- Khoảng gần nhất neo theo timestamp lớn nhất của dataset, không theo ngày hệ thống.

## 3. Thống kê và trực quan

- KPI: tổng alert, mean, median, số Rule, IP và user duy nhất.
- Line chart số alert theo ngày.
- Bar chart theo level và Top Agent/Rule/Event ID.
- Heatmap Agent × toàn bộ level thực tế sau lọc; tổ hợp thiếu được điền 0.
- Distribution Plot và Boxplot trên chỉ số Agent/ngày.

`rule_firedtimes` không được dùng thay cho số lượng event.

## 4. Tổng hợp Agent/ngày

Các phép `groupby`, `count`, `nunique`, `mean` và `max` tạo `total_events`,
`high_level_alerts`, `unique_rules`, `unique_event_ids`, `unique_source_ips`,
`unique_users`, `avg_rule_level`, `max_rule_level` và các nhóm level.

Dòng không có log được biểu diễn bằng 0 để chuỗi ngày liên tục. `ModelService` loại các
dòng giữ chỗ này trước khi fit.

## 5. Ngoại lệ và hình dạng phân phối

`outlier_service.py` sử dụng:

```text
IQR = Q3 - Q1
Ngưỡng dưới = Q1 - 1,5 × IQR
Ngưỡng trên = Q3 + 1,5 × IQR
```

- Boxplot thể hiện Q1, median, Q3, hai ngưỡng và điểm ngoại lệ.
- Skewness gần 0: đối xứng; dương: lệch phải; âm: lệch trái.
- Excess kurtosis gần 0: gần độ nhọn chuẩn; dương: nhọn hơn; âm: bẹt hơn.
- KDE mô tả mật độ khi số mẫu và độ biến thiên cho phép.

Outlier là bất thường thống kê, không tự động đồng nghĩa với tấn công.

## 6. Quan hệ giữa các biến

### Pearson

`relationship_service.py` tính hệ số `r` và p-value giữa biến số với target. Code đánh dấu
chọn khi `|r| > 0,3` và `p < 0,05`. Biến hằng hoặc thiếu dữ liệu không được chọn.
Tương quan không chứng minh quan hệ nhân quả.

### One-way ANOVA

`total_events` được chia nhóm theo `agent_name`. Cần ít nhất hai Agent và mỗi nhóm có ít
nhất hai quan sát. Kết quả F-statistic và p-value cho biết có khác biệt trung bình giữa ít
nhất hai nhóm, nhưng không chỉ ra cặp Agent nào khác nhau.

Code hiện chưa chạy Shapiro hoặc Levene nên không được tuyên bố đã kiểm định hai giả định
này.

## 7. Giao diện và thành phần code

| File | Trách nhiệm |
|---|---|
| `eda_service.py` | Đọc, lọc, thống kê và tổng hợp Agent/ngày |
| `outlier_service.py` | IQR, Boxplot, KDE, skewness, kurtosis |
| `relationship_service.py` | Pearson, p-value, ANOVA và ma trận tương quan |
| `eda_panel.py` | Điều phối bộ lọc và hiển thị bảng/biểu đồ |
| `date_picker.py` | Chọn một ngày trong phạm vi dataset |
| `filtered_alert_window.py` | Xem log chi tiết theo batch sau khi lọc |

`risk_scoring_service.py` là quy tắc kế thừa, không nằm trong flow dự đoán hiện tại và
không phải mô hình học máy.

