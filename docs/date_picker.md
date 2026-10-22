# `date_picker.py`

## Mục đích

Tạo cửa sổ lịch Tkinter để chọn một ngày cho bộ lọc EDA mà không cần thư viện
giao diện bên ngoài.

## Đầu vào và đầu ra

Nhận widget neo, ngày ban đầu, giới hạn ngày của dataset và callback. Module
dựng lưới tháng bằng `calendar`, khóa ngày ngoài phạm vi rồi trả ngày được chọn
cho `EdaPanel`; nó không trực tiếp lọc DataFrame.

