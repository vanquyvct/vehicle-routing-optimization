from __future__ import annotations

from math import radians, sin, cos, asin, sqrt
from typing import Any

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from road_router import RoadRoutingError, get_road_matrix, get_route_geometry


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """Tính khoảng cách Haversine giữa hai tọa độ, đơn vị mét."""
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


def _validate_coordinate(lat: float, lng: float, label: str) -> None:
    if not -90 <= lat <= 90:
        raise ValueError(f"{label}: vĩ độ phải nằm trong khoảng -90 đến 90.")
    if not -180 <= lng <= 180:
        raise ValueError(f"{label}: kinh độ phải nằm trong khoảng -180 đến 180.")


def _validate_payload(payload: dict[str, Any]) -> None:
    required_keys = {"depot", "vehicles", "orders"}
    missing = required_keys - payload.keys()

    if missing:
        raise ValueError(f"Thiếu trường dữ liệu: {', '.join(sorted(missing))}")

    depot = payload["depot"]
    for key in ("lat", "lng"):
        if key not in depot:
            raise ValueError(f"Kho thiếu trường {key}.")

    depot_lat = float(depot["lat"])
    depot_lng = float(depot["lng"])
    _validate_coordinate(depot_lat, depot_lng, "Kho")

    vehicles = payload["vehicles"]
    orders = payload["orders"]

    if not vehicles:
        raise ValueError("Phải có ít nhất 1 phương tiện.")

    if not orders:
        raise ValueError("Phải có ít nhất 1 đơn hàng.")

    vehicle_ids: set[str] = set()
    total_capacity = 0
    max_capacity = 0

    for vehicle in vehicles:
        if "id" not in vehicle or "capacity" not in vehicle:
            raise ValueError("Mỗi phương tiện phải có id và capacity.")

        vehicle_id = str(vehicle["id"]).strip()
        if not vehicle_id:
            raise ValueError("Mã phương tiện không được để trống.")
        if vehicle_id in vehicle_ids:
            raise ValueError(f"Mã phương tiện bị trùng: {vehicle_id}.")
        vehicle_ids.add(vehicle_id)

        capacity = int(vehicle["capacity"])
        if capacity <= 0:
            raise ValueError(f"Capacity của {vehicle_id} phải lớn hơn 0.")

        total_capacity += capacity
        max_capacity = max(max_capacity, capacity)

    order_ids: set[str] = set()
    total_demand = 0

    for order in orders:
        for key in ("id", "lat", "lng", "demand"):
            if key not in order:
                raise ValueError(f"Đơn hàng thiếu trường {key}.")

        order_id = str(order["id"]).strip()
        if not order_id:
            raise ValueError("Mã đơn hàng không được để trống.")
        if order_id in order_ids:
            raise ValueError(f"Mã đơn hàng bị trùng: {order_id}.")
        order_ids.add(order_id)

        lat = float(order["lat"])
        lng = float(order["lng"])
        _validate_coordinate(lat, lng, f"Đơn {order_id}")

        demand = int(order["demand"])
        if demand <= 0:
            raise ValueError(f"Demand của {order_id} phải lớn hơn 0.")

        if demand > max_capacity:
            raise ValueError(
                f"Đơn {order_id} có demand={demand}, lớn hơn sức chứa của mọi xe."
            )

        total_demand += demand

    if total_demand > total_capacity:
        raise ValueError(
            f"Tổng demand ({total_demand}) vượt tổng sức chứa xe ({total_capacity})."
        )


def _build_haversine_matrix(points: list[dict[str, Any]]) -> list[list[int]]:
    matrix: list[list[int]] = []

    for source in points:
        row: list[int] = []
        for target in points:
            row.append(
                haversine_m(
                    float(source["lat"]),
                    float(source["lng"]),
                    float(target["lat"]),
                    float(target["lng"]),
                )
            )
        matrix.append(row)

    return matrix


def _route_duration_from_matrix(
    route_nodes: list[int],
    durations_s: list[list[int]] | None,
) -> int:
    if not durations_s or len(route_nodes) < 2:
        return 0

    return sum(
        durations_s[route_nodes[index]][route_nodes[index + 1]]
        for index in range(len(route_nodes) - 1)
    )


def optimize_cvrp(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Giải CVRP với ưu tiên khoảng cách đường bộ thực tế.

    Luồng chính:
    1. OSRM Table service -> ma trận khoảng cách/thời gian theo mạng đường.
    2. OR-Tools -> chia đơn và tối ưu thứ tự điểm.
    3. OSRM Route service -> geometry đường bộ của từng tuyến.

    Nếu dịch vụ OSRM tạm thời không truy cập được, hệ thống tự hạ cấp về
    Haversine để demo vẫn chạy và trả cảnh báo rõ ràng.
    """
    _validate_payload(payload)

    depot = payload["depot"]
    vehicles = payload["vehicles"]
    orders = payload["orders"]

    points = [
        {
            "id": "DEPOT",
            "name": depot.get("name", "Kho"),
            "lat": float(depot["lat"]),
            "lng": float(depot["lng"]),
        }
    ] + [
        {
            "id": str(order["id"]),
            "name": order.get("name", str(order["id"])),
            "lat": float(order["lat"]),
            "lng": float(order["lng"]),
        }
        for order in orders
    ]

    routing_source = "OSRM"
    routing_warning = None
    is_fallback = False
    durations_s: list[list[int]] | None = None

    try:
        road_matrix = get_road_matrix(points)
        distance_matrix = road_matrix.distances_m
        durations_s = road_matrix.durations_s
    except RoadRoutingError as exc:
        distance_matrix = _build_haversine_matrix(points)
        routing_source = "Haversine fallback"
        routing_warning = str(exc)
        is_fallback = True

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
        0,
        capacities,
        True,
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
    total_duration_s = 0

    for vehicle_index, vehicle in enumerate(vehicles):
        index = routing.Start(vehicle_index)

        route_order_ids: list[str] = []
        route_node_ids: list[str] = []
        route_points: list[dict[str, Any]] = []
        route_node_indexes: list[int] = []
        matrix_route_distance_m = 0
        route_load = 0

        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            point = points[node_index]

            route_node_indexes.append(node_index)
            route_node_ids.append(point["id"])
            route_points.append(point)

            if node_index != 0:
                order = orders[node_index - 1]
                route_order_ids.append(str(order["id"]))
                route_load += int(order["demand"])

            previous_index = index
            index = solution.Value(routing.NextVar(index))
            matrix_route_distance_m += routing.GetArcCostForVehicle(
                previous_index,
                index,
                vehicle_index,
            )

        route_node_indexes.append(0)
        route_node_ids.append("DEPOT")
        route_points.append(points[0])

        route_distance_m = matrix_route_distance_m
        route_duration_s = _route_duration_from_matrix(route_node_indexes, durations_s)
        road_geometry: list[list[float]] = [
            [point["lat"], point["lng"]]
            for point in route_points
        ]

        # Only request road geometry for active routes.
        if route_order_ids and not is_fallback:
            try:
                geometry_result = get_route_geometry(route_points)
                if geometry_result.coordinates:
                    road_geometry = geometry_result.coordinates
                if geometry_result.distance_m > 0:
                    route_distance_m = geometry_result.distance_m
                if geometry_result.duration_s > 0:
                    route_duration_s = geometry_result.duration_s
            except RoadRoutingError as exc:
                # Keep the road-distance optimization result, but draw a straight
                # line if a geometry request fails.
                routing_warning = (
                    "Đã tối ưu bằng ma trận đường bộ, nhưng có tuyến không lấy "
                    f"được hình học đường đi: {exc}"
                )

        total_distance_m += route_distance_m
        total_duration_s += route_duration_s

        result_routes.append(
            {
                "vehicle_id": str(vehicle["id"]),
                "capacity": int(vehicle["capacity"]),
                "load": route_load,
                "orders": route_order_ids,
                "route": route_node_ids,
                "points": route_points,
                "geometry": road_geometry,
                "distance_m": route_distance_m,
                "distance_km": round(route_distance_m / 1000, 2),
                "duration_s": route_duration_s,
                "duration_min": round(route_duration_s / 60, 1) if route_duration_s else None,
            }
        )

    return {
        "status": "ok",
        "algorithm": "CVRP - Google OR-Tools",
        "routing_source": routing_source,
        "distance_method": (
            "OSRM road network"
            if not is_fallback
            else "Haversine fallback"
        ),
        "is_fallback": is_fallback,
        "warning": routing_warning,
        "routes": result_routes,
        "total_distance_m": total_distance_m,
        "total_distance_km": round(total_distance_m / 1000, 2),
        "total_duration_s": total_duration_s,
        "total_duration_min": round(total_duration_s / 60, 1) if total_duration_s else None,
    }
