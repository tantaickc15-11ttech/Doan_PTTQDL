# Namespace `src/models`

## Mục đích

Dành cho các lớp mô tả đối tượng dữ liệu nếu ứng dụng cần mở rộng. Hiện tại thư mục chỉ có
`__init__.py`; dữ liệu được biểu diễn trực tiếp bằng DataFrame và các mô hình scikit-learn
được xây dựng trong `src/services/model_service.py`.

Thư mục này không chứa file mô hình đã huấn luyện và không phải nơi lưu Pipeline. Pipeline
hiện được giữ trong bộ nhớ khi ứng dụng chạy.

