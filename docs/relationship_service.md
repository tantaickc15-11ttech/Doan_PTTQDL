# `relationship_service.py`

## Mục đích

Tạo bằng chứng thống kê về mối liên hệ giữa các biến số và khác biệt theo Agent
trước khi xây dựng mô hình.

## Đầu vào

Bảng Agent/ngày từ `EdaService.aggregate_agent_day()`.

## Pearson correlation

- Tính hệ số `r` và p-value giữa từng biến số với biến mục tiêu.
- Đánh dấu chọn khi `|r| > 0,3` và `p < 0,05` theo code hiện tại.
- Biến hằng/thiếu dữ liệu được giữ trong bảng nhưng không chọn.
- Tương quan không chứng minh quan hệ nhân quả.

## One-way ANOVA

- Chia `total_events` thành các nhóm theo `agent_name`.
- Cần ít nhất hai nhóm, mỗi nhóm có ít nhất hai quan sát.
- Trả F-statistic, p-value và kết luận khác biệt trung bình.
- Chỉ cho biết có ít nhất một nhóm khác, không chỉ ra nhóm nào.

Code hiện tại không chạy Shapiro hoặc Levene, nên báo cáo không được khẳng định
đã kiểm định hai giả định này.

## Đầu ra và vai trò

Ma trận tương quan, bảng Pearson và kết quả ANOVA cho `EdaPanel`, làm bằng chứng
EDA khi giải thích lựa chọn biến cho mô hình.

