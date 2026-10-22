# Thư mục mã nguồn `src`

## Mục đích

Chứa mã ứng dụng theo cách tách giao diện khỏi logic xử lý. `main.py` ở thư mục gốc tạo
cửa sổ chính; UI nhận thao tác người dùng và gọi các service tương ứng.

## Thành phần

- `ui/`: cửa sổ, tab, bộ lọc và biểu đồ Tkinter/Matplotlib.
- `services/`: đọc/làm sạch dữ liệu, EDA, quan hệ biến và mô hình học máy.
- `models/`: namespace dành cho lớp mô tả dữ liệu; hiện chưa có model miền nghiệp vụ.
- `__init__.py`: đánh dấu `src` là Python package.

## Nguyên tắc phụ thuộc

```text
main.py → src/ui → src/services
```

Service không phụ thuộc vào widget giao diện, nhờ đó có thể kiểm thử độc lập trong `tests`.

