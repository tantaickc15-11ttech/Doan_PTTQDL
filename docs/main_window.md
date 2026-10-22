# `main_window.py`

## Vai trò

Giao diện Tkinter điều phối thao tác người dùng và hiển thị kết quả. Logic profiling/cleaning nằm trong service, không được viết trực tiếp trong UI.

## Luồng xử lý dataset

1. Người dùng bấm **Xử lý dataset JSON** và chọn nguyên file raw.
2. UI tạo background thread để profiling và cleaning không khóa Tkinter main loop.
3. Worker chỉ gửi thông báo qua `queue.Queue`; UI cập nhật widget bằng `after()` trên main thread.
4. Tab **Chất lượng dữ liệu** hiển thị Before/After, missing và nguyên nhân loại.
5. Bảng log sạch chỉ tải 20 dòng mỗi lần; cuộn đến cuối để tải tiếp.
6. Nhấn đúp một dòng để xem chi tiết 21 trường sau Cleaning; nhấn một lần chỉ chọn dòng.
7. Khi xử lý, UI hiển thị chữ `Loading.....` thay cho thanh Progressbar.

## File đầu ra

- `data/processed/wazuh_cleaned.csv`
- `reports/profiling_report.json`
- `reports/cleaning_report.json`

Nếu CSV đã tồn tại, UI yêu cầu người dùng xác nhận trước khi thay thế.
