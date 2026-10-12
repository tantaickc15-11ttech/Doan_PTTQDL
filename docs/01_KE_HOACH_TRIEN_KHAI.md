# Kế hoạch triển khai

## Giai đoạn 0 – Baseline

- Tách repo mới khỏi đồ án cũ.
- Chỉ tái sử dụng code Python desktop cần thiết.
- Loại Telegram khỏi active code.
- Chạy lại toàn bộ kiểm thử.

## Giai đoạn 1 – Data

- Chốt raw dataset thật.
- Lọc `agent.id != "000"`.
- Flatten field cần thiết.
- Chuẩn hóa timestamp và kiểu dữ liệu.
- Phân tích missing theo ngữ nghĩa.
- Tạo dataset sạch và dataset tổng hợp.

## Giai đoạn 2 – EDA và dashboard

- Bộ lọc Agent và thời gian.
- KPI và thống kê mô tả.
- Bar chart và line chart có câu hỏi phân tích rõ ràng.
- Đối chiếu số liệu UI với dữ liệu nguồn.

## Giai đoạn 3 – Outlier

- Tính Q1, Q3, IQR và các ngưỡng.
- Tạo bảng thống kê, boxplot và bảng đánh giá outlier.
- Phân biệt outlier, rare event và high severity alert.

## Giai đoạn 4 – Mối quan hệ và chọn biến

- Correlation cho biến số.
- ANOVA cho biến phân loại khi phù hợp.
- Lập bảng bằng chứng chọn hoặc loại biến.

## Giai đoạn 5 – Model

Chỉ bắt đầu sau khi người thực hiện chốt target. Model phải có train/test, MSE, R² và validation phù hợp.

## Những điểm chưa chốt

- Tên đề tài cuối cùng.
- Bài toán phân tích chính.
- Khoảng thời gian dataset cuối.
- Danh sách Agent sử dụng.
- Target dự đoán.
- Model cuối cùng.

