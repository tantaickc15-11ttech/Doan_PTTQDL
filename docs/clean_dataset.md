# `clean_dataset.py`

## Mục đích

Chạy lại Validation/Cleaning từ command line mà không sửa source code.

## Cách chạy

```powershell
python scripts/clean_dataset.py data/wazuh_dataset_30days_level7_raw.json
```

## Kết quả mặc định

- `data/processed/wazuh_cleaned.csv`
- `reports/cleaning_report.json`

Raw JSON chỉ được mở để đọc, không bị sửa hoặc ghi đè.
