# Tầng 2 – Phân tích khám phá dữ liệu

## Nguồn và đơn vị phân tích

Tầng 2 đọc `data/processed/wazuh_cleaned.csv`. Dashboard dùng từng alert; phần
outlier, Pearson, ANOVA và mô hình dùng một dòng Agent/ngày. Agent/ngày không
log được thêm giá trị 0 để chuỗi biểu đồ liên tục nhưng không dùng để train.

## Chức năng

1. Lọc theo Agent, Alert Level, 7/14/30 ngày gần nhất, một ngày hoặc khoảng ngày.
2. KPI và thống kê mô tả: tổng, mean, median, số Rule, IP và user.
3. Line chart, bar chart, Top-N và heatmap mọi level thực có.
4. IQR/Boxplot, KDE, skewness và kurtosis cho dữ liệu Agent/ngày.
5. Pearson correlation, p-value, heatmap và scatter.
6. One-way ANOVA so sánh `total_events` theo Agent.

## Giới hạn diễn giải

- `rule_firedtimes` không được dùng làm tổng event.
- IQR không tự động kết luận tấn công.
- Pearson không chứng minh nhân quả.
- ANOVA hiện trả F và p-value, chưa kiểm định Shapiro/Levene.
- Tầng hiện tại không sử dụng `agent_risk_index` hoặc `alert_risk_level`.

