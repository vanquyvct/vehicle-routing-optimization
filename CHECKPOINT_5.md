# Checkpoint 5 - Dashboard và xuất kết quả cho báo cáo

## Chức năng bổ sung

- Tổng hợp KPI sau khi chạy benchmark:
  - tỷ lệ cải thiện trung bình;
  - tổng quãng đường tiết kiệm;
  - kịch bản cải thiện tốt nhất;
  - runtime trung bình.
- Biểu đồ so sánh quãng đường Greedy baseline và CVRP.
- Biểu đồ tỷ lệ cải thiện và runtime theo quy mô dữ liệu.
- Sinh nhận xét tự động trực tiếp từ kết quả benchmark.
- Xuất kết quả benchmark thành LaTeX:
  - bảng kết quả;
  - nhãn và caption;
  - đoạn nhận xét tổng hợp.
- Giữ chức năng xuất CSV từ Checkpoint 4.

## Ý nghĩa

Checkpoint này tập trung vào khả năng trình bày và tái sử dụng số liệu thực nghiệm
trong báo cáo Thực tập tốt nghiệp. Các biểu đồ được dựng trực tiếp bằng SVG,
không cần thêm thư viện JavaScript bên ngoài.
