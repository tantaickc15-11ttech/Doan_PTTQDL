# `profile_dataset.py`

## Mục đích

Cung cấp lệnh chạy lại profiling mà không phải sửa source code.

## Cách chạy

```powershell
python scripts/profile_dataset.py data/wazuh_dataset_30days_level7_raw.json
```

Có thể chọn file output khác bằng `--output`.

## Kết quả

Lệnh hiển thị tiến trình sau mỗi 10.000 bản ghi và ghi báo cáo vào `reports/profiling_report.json`.
