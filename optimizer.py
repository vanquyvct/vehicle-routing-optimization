from __future__ import annotations

from math import radians, sin, cos, asin, sqrt
from typing import Any

from ortools.constraint_solver import pywrapcp, routing_enums_pb2


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """Khoảng cách đường chim bay giữa 2 tọa độ, trả về mét."""
    earth_radius_m = 6_371_000

    lat1_r = radians(lat1)
    lon1_r = radians(lon1)
    lat2_r = radians(lat2)
    lon2_r = radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1_r) * cos(lat2_r) * sin(dlon / 2) ** 2
    )
    c = 2 * asin(sqrt(a))
    return int(round(earth_radius_m * c))


def _validate_payload(payload: dict[str, Any]) -> None:
    required_keys = {"depot", "vehicles", "orders"}
    missing = required_keys - payload.keys()
    if missing:
        raise ValueError(f"Thiếu trường dữ liệu: {', '.join(sorted(missing))}")

    if not payload["vehicles"]:
        raise ValueError("Phải có ít nhất 1 phương tiện.")

    if not payload["orders"]:
        raise ValueError("Phải có ít nhất 1 đơn hàng.")

    for key in ("lat", "lng"):
        if key not in payload["depot"]:
            raise ValueError(f"Kho thiếu trường {key}.")

    total_capacity = 0
    max_capacity = 0

    for vehicle in payload["vehicles"]:
        if "id" not in vehicle or "capacity" not in vehicle:
            raise ValueError("Mỗi phương tiện phải có id và capacity.")
        capacity = int(vehicle["capacity"])
        if capacity <= 0:
            raise ValueError("Capacity của xe phải lớn hơn 0.")
        total_capacity += capacity
        max_capacity = max(max_capacity, capacity)

    total_demand = 0

    for order in payload["orders"]:
        for key in ("id", "lat", "lng", "demand"):
            if key not in order:
                raise ValueError(f"Đơn hàng thiếu trường {key}.")

        demand = int(order["demand"])
        if demand <= 0:
            raise ValueError("Demand của đơn hàng phải lớn hơn 0.")

        if demand > max_capacity:
            raise ValueError(
                f"Đơn {order['id']} có demand={demand}, lớn hơn sức chứa của mọi xe."
            )

        total_demand += demand

    if total_demand > total_capacity:
        raise ValueError(
            f"Tổng demand ({total_demand}) vượt tổng sức chứa xe ({total_capacity})."
        )


def _build_distance_matrix(points: list[dict[str, float]]) -> list[list[int]]:
    matrix: list[list[int]] = []

    for source in points:
        row: list[int] = []
        for target in points:
            row.append(
                haversine_m(
                    source["lat"],
                    source["lng"],
                    target["lat"],
                    target["lng"],
                )
            )
        matrix.append(row)

    return matrix


def optimize_cvrp(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Giải CVRP đơn giản:
    - 1 kho
    - nhiều xe
    - mỗi xe có capacity
    - mỗi đơn có demand
    - mục tiêu: giảm tổng khoảng cách Haversine
    """
    _validate_payload(payload)

    depot = payload["depot"]
    vehicles = payload["vehicles"]
    orders = payload["orders"]

    # Node 0 là kho, node 1..N là các đơn hàng.
    points = [
        {"lat": float(depot["lat"]), "lng": float(depot["lng"])}
    ] + [
        {"lat": float(order["lat"]), "lng": float(order["lng"])}
        for order in orders
    ]

    distance_matrix = _build_distance_matrix(points)
    demands = [0] + [int(order["demand"]) for order in orders]
    capacities = [int(vehicle["capacity"]) for vehicle in vehicles]

    manager = pywrapcp.RoutingIndexManager(
        len(distance_matrix),
        len(vehicles),
        0,
    )
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index: int, to_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distance_matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    def demand_callback(from_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        return demands[from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)

    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,            # không cho phép "slack" tải trọng
        capacities,
        True,         # tải bắt đầu từ 0 ở kho
        "Capacity",
    )

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.seconds = 3

    solution = routing.SolveWithParameters(search_parameters)

    if solution is None:
        raise ValueError("Không tìm được phương án hợp lệ với dữ liệu hiện tại.")

    result_routes: list[dict[str, Any]] = []
    total_distance_m = 0

    for vehicle_index, vehicle in enumerate(vehicles):
        index = routing.Start(vehicle_index)

        route_order_ids: list[str] = []
        route_node_ids: list[str] = ["DEPOT"]
        route_distance_m = 0
        route_load = 0

        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)

            if node_index != 0:
                order = orders[node_index - 1]
                route_order_ids.append(order["id"])
                route_node_ids.append(order["id"])
                route_load += int(order["demand"])

            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_distance_m += routing.GetArcCostForVehicle(
                previous_index,
                index,
                vehicle_index,
            )

        route_node_ids.append("DEPOT")
        total_distance_m += route_distance_m

        result_routes.append(
            {
                "vehicle_id": vehicle["id"],
                "capacity": int(vehicle["capacity"]),
                "load": route_load,
                "orders": route_order_ids,
                "route": route_node_ids,
                "distance_m": route_distance_m,
                "distance_km": round(route_distance_m / 1000, 2),
            }
        )

    return {
        "status": "ok",
        "algorithm": "CVRP - Google OR-Tools",
        "distance_method": "Haversine",
        "routes": result_routes,
        "total_distance_m": total_distance_m,
        "total_distance_km": round(total_distance_m / 1000, 2),
    }
