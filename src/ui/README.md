# Tầng giao diện `src/ui`

## Mục đích

Chứa giao diện desktop Tkinter, nhận lựa chọn của người dùng, gọi service và hiển thị bảng,
biểu đồ hoặc chỉ số. Các file này không triển khai lại công thức phân tích.

## Thành phần

- `main_window.py`: cửa sổ chính, thanh công cụ, notebook và điều phối dữ liệu chung.
- `date_picker.py`: chọn một ngày hoặc khoảng ngày.
- `eda_panel.py`: các tab Tổng quan, Quan sát dữ liệu và Phân tích.
- `model_panel.py`: huấn luyện/dự đoán HQTT và HQĐT; hiển thị MSE/R², split, K-Fold.
- `external_validation_panel.py`: nạp dữ liệu mới và đánh giá Pipeline cũ, không fit lại.
- `filtered_alert_window.py`: cửa sổ xem chi tiết các cảnh báo sau khi lọc.
- `__init__.py`: đánh dấu package UI.

## Flow tương tác

```text
Người dùng → widget/panel → service xử lý → bảng hoặc biểu đồ
```

Luồng gọi hàm đầy đủ được mô tả trong `docs/APP_FLOW.md`.

