# Vehicle Routing TTTN

Hệ thống hỗ trợ điều phối phương tiện và tối ưu tuyến đường giao hàng.

## Phiên bản hiện tại

Vertical slice đầu tiên của dự án:

- Flask backend
- REST API `POST /api/optimize`
- CVRP bằng Google OR-Tools
- Giới hạn tải trọng phương tiện
- Kho + nhiều phương tiện + nhiều điểm giao
- Khoảng cách Haversine
- Giao diện web nhập JSON và hiển thị kết quả

## Yêu cầu

- Python 3.10+
- pip

## Cài đặt

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Nếu PowerShell chặn script:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Chạy

```powershell
python app.py
```

Mở trình duyệt:

```text
http://127.0.0.1:5000
```

## Kiểm tra API

```text
GET /api/health
POST /api/optimize
```

## Cấu trúc

```text
vehicle-routing-tttn/
├── app.py
├── optimizer.py
├── requirements.txt
├── data/
│   └── sample.json
├── templates/
│   └── index.html
└── static/
    ├── app.js
    └── style.css
```

## Bước tiếp theo

- Leaflet + OpenStreetMap
- Thêm/sửa/xóa xe và điểm giao trực tiếp trên giao diện
- Vẽ route lên bản đồ
- Lưu dữ liệu
- Baseline để so sánh kết quả
- Bộ test và báo cáo thực nghiệm
