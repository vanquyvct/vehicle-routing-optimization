# Checkpoint 4 - Kiểm thử và thực nghiệm

## Bổ sung

- Endpoint `/api/self-test` để chạy các test validation không phụ thuộc dịch vụ routing.
- Endpoint `/api/benchmark` để chạy 3 bộ dữ liệu cố định:
  - 10 điểm / 2 xe
  - 20 điểm / 4 xe
  - 30 điểm / 6 xe
- Benchmark so sánh Greedy baseline và CVRP/OR-Tools trên cùng ma trận khoảng cách.
- Ghi nhận:
  - tổng quãng đường baseline;
  - tổng quãng đường CVRP;
  - số km chênh lệch;
  - tỷ lệ cải thiện;
  - thời gian chạy;
  - nguồn khoảng cách OSRM hay Haversine dự phòng.
- Giao diện hiển thị bảng thực nghiệm.
- Xuất kết quả thực nghiệm thành CSV để sử dụng cho báo cáo.

## Bộ kiểm thử validation

1. Không có phương tiện.
2. Trùng mã đơn hàng.
3. Một đơn vượt sức chứa của mọi xe.
4. Tổng nhu cầu vượt tổng sức chứa.
5. Tọa độ không hợp lệ.

## Lưu ý

Benchmark không yêu cầu geometry bản đồ. Điều này giúp giảm số request routing và giữ phép so sánh baseline/CVRP nhất quán trên cùng ma trận chi phí.
