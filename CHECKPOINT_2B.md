# Checkpoint 2B - Road-network routing

## Nội dung

- Dùng OSRM Table service để lấy ma trận khoảng cách và thời gian lái xe theo mạng đường OpenStreetMap.
- OR-Tools sử dụng ma trận khoảng cách đường bộ thay cho Haversine khi OSRM khả dụng.
- Sau khi OR-Tools xác định thứ tự điểm, OSRM Route service trả về geometry theo đường phố thực tế.
- Leaflet vẽ geometry đường bộ thay vì nối thẳng các tọa độ.
- Đánh số 1, 2, 3... cho từng điểm theo thứ tự xe cần ghé.
- Hiển thị quãng đường và thời gian lái xe ước tính.
- Có chế độ Haversine dự phòng nếu dịch vụ OSRM tạm thời không truy cập được.

## Lưu ý kỹ thuật

OSRM sử dụng dữ liệu OpenStreetMap. Bản demo này gọi public OSRM demo server qua backend Flask.
Nếu triển khai ở quy mô lớn hoặc sử dụng lâu dài, nên tự triển khai OSRM hoặc dùng một dịch vụ routing có SLA/API key phù hợp.
