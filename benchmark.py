from __future__ import annotations

import time
from copy import deepcopy
from typing import Any

from optimizer import _validate_payload, optimize_cvrp


DEPOT = {
    "name": "Kho trung tâm",
    "lat": 21.0285,
    "lng": 105.8542,
}

# 30 vị trí cố định quanh Hà Nội để các lần thực nghiệm có thể lặp lại.
BENCHMARK_COORDINATES = [
    (21.0320, 105.8480),
    (21.0210, 105.8610),
    (21.0360, 105.8650),
    (21.0170, 105.8490),
    (21.0260, 105.8720),
    (21.0410, 105.8390),
    (21.0125, 105.8585),
    (21.0345, 105.8790),
    (21.0220, 105.8350),
    (21.0470, 105.8530),
    (21.0140, 105.8750),
    (21.0380, 105.8260),
    (21.0060, 105.8450),
    (21.0520, 105.8680),
    (21.0290, 105.8170),
    (21.0090, 105.8830),
    (21.0440, 105.8890),
    (21.0015, 105.8640),
    (21.0560, 105.8420),
    (21.0190, 105.8970),
    (21.0610, 105.8610),
    (21.0040, 105.8320),
    (21.0480, 105.9070),
    (20.9970, 105.8790),
    (21.0670, 105.8780),
    (21.0270, 105.9120),
    (21.0580, 105.8210),
    (20.9910, 105.8510),
    (21.0720, 105.8490),
    (21.0110, 105.9120),
]

DEMAND_PATTERN = [3, 4, 2, 5, 3, 1, 4, 2, 5, 3]


def build_benchmark_payload(order_count: int, vehicle_count: int) -> dict[str, Any]:
    orders = []

    for index in range(order_count):
        lat, lng = BENCHMARK_COORDINATES[index]
        orders.append(
            {
                "id": f"B{index + 1:02d}",
                "lat": lat,
                "lng": lng,
                "demand": DEMAND_PATTERN[index % len(DEMAND_PATTERN)],
            }
        )

    vehicles = [
        {
            "id": f"XE{index + 1:02d}",
            "capacity": 18,
        }
        for index in range(vehicle_count)
    ]

    payload = {
        "depot": deepcopy(DEPOT),
        "vehicles": vehicles,
        "orders": orders,
    }

    _validate_payload(payload)
    return payload


BENCHMARK_SCENARIOS = [
    {
        "id": "B10",
        "name": "10 điểm giao",
        "orders": 10,
        "vehicles": 2,
    },
    {
        "id": "B20",
        "name": "20 điểm giao",
        "orders": 20,
        "vehicles": 4,
    },
    {
        "id": "B30",
        "name": "30 điểm giao",
        "orders": 30,
        "vehicles": 6,
    },
]


def run_benchmarks() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for scenario in BENCHMARK_SCENARIOS:
        started = time.perf_counter()

        try:
            payload = build_benchmark_payload(
                scenario["orders"],
                scenario["vehicles"],
            )

            # Benchmark không cần geometry bản đồ. Dùng cùng ma trận chi phí
            # cho baseline và CVRP để giảm số request và giữ phép so sánh nhất quán.
            result = optimize_cvrp(
                payload,
                include_geometry=False,
                solver_time_limit_s=1,
            )

            elapsed_s = time.perf_counter() - started
            comparison = result.get("comparison")

            if comparison is None:
                raise RuntimeError("Không tạo được số liệu so sánh baseline.")

            rows.append(
                {
                    "scenario_id": scenario["id"],
                    "scenario_name": scenario["name"],
                    "orders": scenario["orders"],
                    "vehicles": scenario["vehicles"],
                    "baseline_km": comparison["baseline_total_distance_km"],
                    "cvrp_km": comparison["optimized_total_distance_km"],
                    "saved_km": comparison["distance_saved_km"],
                    "improvement_percent": comparison["improvement_percent"],
                    "runtime_s": round(elapsed_s, 2),
                    "routing_source": result["routing_source"],
                    "is_fallback": result["is_fallback"],
                    "status": "ok",
                    "message": result.get("warning"),
                }
            )
        except Exception as exc:
            elapsed_s = time.perf_counter() - started
            rows.append(
                {
                    "scenario_id": scenario["id"],
                    "scenario_name": scenario["name"],
                    "orders": scenario["orders"],
                    "vehicles": scenario["vehicles"],
                    "baseline_km": None,
                    "cvrp_km": None,
                    "saved_km": None,
                    "improvement_percent": None,
                    "runtime_s": round(elapsed_s, 2),
                    "routing_source": None,
                    "is_fallback": None,
                    "status": "error",
                    "message": str(exc),
                }
            )

    return rows


def run_validation_tests() -> list[dict[str, Any]]:
    base = {
        "depot": deepcopy(DEPOT),
        "vehicles": [
            {"id": "XE01", "capacity": 10},
            {"id": "XE02", "capacity": 10},
        ],
        "orders": [
            {"id": "DH01", "lat": 21.0320, "lng": 105.8480, "demand": 4},
            {"id": "DH02", "lat": 21.0210, "lng": 105.8610, "demand": 5},
        ],
    }

    cases: list[tuple[str, dict[str, Any], str]] = []

    payload = deepcopy(base)
    payload["vehicles"] = []
    cases.append(("Không có phương tiện", payload, "ít nhất 1 phương tiện"))

    payload = deepcopy(base)
    payload["orders"][0]["id"] = "DH02"
    cases.append(("Trùng mã đơn hàng", payload, "bị trùng"))

    payload = deepcopy(base)
    payload["orders"][0]["demand"] = 15
    cases.append(("Đơn vượt sức chứa mọi xe", payload, "lớn hơn sức chứa"))

    payload = deepcopy(base)
    payload["vehicles"] = [{"id": "XE01", "capacity": 5}]
    payload["orders"] = [
        {"id": "DH01", "lat": 21.0320, "lng": 105.8480, "demand": 4},
        {"id": "DH02", "lat": 21.0210, "lng": 105.8610, "demand": 4},
    ]
    cases.append(("Tổng nhu cầu vượt tổng sức chứa", payload, "vượt tổng sức chứa"))

    payload = deepcopy(base)
    payload["orders"][0]["lat"] = 100
    cases.append(("Vĩ độ không hợp lệ", payload, "vĩ độ"))

    results = []

    for name, payload, expected_fragment in cases:
        passed = False
        actual_message = ""

        try:
            _validate_payload(payload)
            actual_message = "Hệ thống không phát hiện dữ liệu sai."
        except ValueError as exc:
            actual_message = str(exc)
            passed = expected_fragment.lower() in actual_message.lower()

        results.append(
            {
                "name": name,
                "passed": passed,
                "message": actual_message,
            }
        )

    return results
