# `eda_panel.py`

## Mục đích

Giao diện Tầng 2 hiển thị kết quả EDA do các service tính toán.

## Chức năng

- Bộ lọc: 7/14/30 ngày gần nhất, một ngày, khoảng ngày, Agent và Alert Level.
- Tổng quan: KPI, xu hướng theo ngày, level, Top Rule/Agent/Event ID và heatmap
  Agent × tất cả level thực có.
- Outlier: Boxplot, KDE, Q1/median/Q3, IQR, skewness và kurtosis trên
  `total_events` hoặc các nhóm level; có thể xem riêng từng Agent.
- Quan hệ: bảng Pearson, p-value, heatmap tương quan, scatter và ANOVA theo Agent
  với biến đích `total_events`.
- Card Tổng Alert mở danh sách log theo đúng bộ lọc hiện tại.

Dataset được nạp bằng worker thread để không khóa Tkinter. UI chỉ trình bày;
công thức nằm trong `EdaService`, `OutlierService`, `RelationshipService`.

## Vai trò trong pipeline

Nhận CSV sạch, điều phối bộ lọc và biến kết quả phân tích thành bảng/biểu đồ.

