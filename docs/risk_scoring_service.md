# `risk_scoring_service.py`

## Trạng thái và mục đích

Đây là module quy tắc rủi ro kế thừa/tham khảo. Nó ánh xạ `rule_level` thành
điểm `1/4/16/64` và nhãn Low/Medium/High/Critical.

Module là rule-based scoring, không phải mô hình học máy. Quy trình đồ án hiện
tại đã bỏ `agent_risk_index` và `alert_risk_level` khỏi CSV, EDA và mô hình;
vì vậy service này không nằm trên luồng chạy chính dự đoán `total_events`.

## Đầu vào và đầu ra

- Input: một hoặc nhiều `rule_level`, hoặc tổng điểm quy ước.
- Output: điểm từng alert hoặc nhãn mức quy ước.

Chỉ sử dụng module nếu sau này khôi phục yêu cầu chấm điểm rủi ro và phải cập
nhật đồng bộ code, UI, báo cáo và slide.

