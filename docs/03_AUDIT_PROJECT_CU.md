# Audit project cũ

## Kết luận

Project cũ đủ làm nền cho đồ án mới và không cần viết lại toàn bộ. Phần tái sử dụng gồm đầu vào JSON, HTTP receiver, SQLite, Tkinter, Matplotlib và khung kiểm thử.

## Dữ liệu local được kiểm tra

- 109 cảnh báo trong SQLite.
- 98 cảnh báo endpoint sau khi loại Agent `000`.
- 11 cảnh báo nội bộ Wazuh Manager.
- Khoảng dữ liệu hiện có từ 01/09/2026 đến 19/09/2026.
- Dữ liệu mẫu, dữ liệu test và dữ liệu thật đang trộn chung.
- Raw JSON còn giữ các field như MITRE, decoder, Event ID, target user, source IP và status ở một phần bản ghi.

Database trên chỉ dùng để audit, không được sao chép vào repo mới. Dataset cuối phải được thu thập và mô tả riêng.

## Khoảng trống so với yêu cầu mới

- Chưa có preprocessing bằng Pandas/NumPy.
- Chưa có dataset tổng hợp theo Agent và thời gian.
- Chưa có bộ lọc 3/7/15/30/90 ngày.
- Chưa có boxplot và bảng IQR.
- Chưa có correlation, ANOVA và bảng chọn biến.
- Chưa chốt target nên chưa xây model.

## Nguyên tắc thực hiện

Không chọn target, feature hoặc model trước khi có dataset cuối và kết quả EDA. Code, UI, báo cáo, slide và demo phải sử dụng cùng kết quả thật.

