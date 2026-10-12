# Wazuh Project Integration

Thư mục này chỉ chứa integration chuyển raw JSON từ Wazuh đến ứng dụng desktop.

- `custom-project-alerts`: shell wrapper chạy trên Wazuh Manager.
- `custom-project-alerts.py`: gửi raw JSON đến receiver bằng HTTP POST.
- `alerts_process.py`: HTTP receiver chạy cùng ứng dụng desktop.
- `project_config.example.conf`: cấu hình mẫu an toàn.

File cấu hình thật là `project_config.conf` và không được đưa lên GitHub.

