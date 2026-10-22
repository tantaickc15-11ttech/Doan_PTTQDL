# Thư mục `docs`

## Mục đích

Là tài liệu kỹ thuật của đồ án. Đọc `APP_FLOW.md` trước để hiểu luồng toàn hệ thống,
sau đó dùng tài liệu theo từng file để đối chiếu với mã nguồn.

## Tài liệu tổng thể

- `APP_FLOW.md`: các flow chính, flow con và chuỗi gọi giữa UI với service.
- `TECHNIQUE_MAPPING.md`: kỹ thuật sử dụng, mục đích và vị trí triển khai.
- `00_PHAM_VI_VA_REUSE.md`: phạm vi hiện tại và phần được tái sử dụng.
- `01_KE_HOACH_TRIEN_KHAI.md`: kế hoạch triển khai.
- `02_DATASET_SCHEMA_DU_KIEN.md`: schema dữ liệu đầu vào.
- `03_AUDIT_PROJECT_CU.md`: kết quả rà soát phiên bản cũ.
- `04_TANG_1_DATA.md`: thiết kế tầng dữ liệu.
- `05_KET_QUA_PROFILING_DATASET.md`: kết quả khảo sát dữ liệu.
- `06_KET_QUA_CLEANING_DATASET.md`: kết quả làm sạch.
- `07_TANG_2_EDA.md`: nội dung EDA và trực quan hóa.

## Tài liệu theo mã nguồn

- Nhóm khởi chạy/UI: `main.md`, `main_window.md`, `date_picker.md`, `eda_panel.md`,
  `model_panel.md`, `external_validation_panel.md`, `filtered_alert_window.md`.
- Nhóm dữ liệu/EDA: `json_stream_reader.md`, `cleaned_csv_reader.md`,
  `data_cleaning_service.md`, `data_preprocessing_service.md`,
  `data_profiling_service.md`, `eda_service.md`, `outlier_service.md`,
  `relationship_service.md`, `risk_scoring_service.md`.
- Nhóm mô hình: `model_service.md`.
- Nhóm dòng lệnh: `profile_dataset.md`, `clean_dataset.md`.

Mỗi tài liệu theo file giải thích trách nhiệm, dữ liệu vào/ra, kỹ thuật và vị trí của file
trong flow; mã nguồn vẫn là nguồn chính xác cuối cùng khi có thay đổi.

