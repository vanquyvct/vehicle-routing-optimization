from __future__ import annotations

from itertools import permutations
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


def _route_distance_from_matrix(
    route_nodes: list[int],
    distances_m: list[list[int]],
) -> int:
    if len(route_nodes) < 2:
        return 0

    return sum(
        distances_m[route_nodes[index]][route_nodes[index + 1]]
        for index in range(len(route_nodes) - 1)
    )


def _vehicle_orders_to_route(
    vehicle: dict[str, Any],
    order_node_indexes: list[int],
    points: list[dict[str, Any]],
    orders: list[dict[str, Any]],
    distances_m: list[list[int]],
    durations_s: list[list[int]] | None,
) -> dict[str, Any]:
    route_nodes = [0] + order_node_indexes + [0]
    route_points = [points[node] for node in route_nodes]
    order_ids = [str(orders[node - 1]["id"]) for node in order_node_indexes]
    route_load = sum(int(orders[node - 1]["demand"]) for node in order_node_indexes)

    distance_m = _route_distance_from_matrix(route_nodes, distances_m)
    duration_s = _route_duration_from_matrix(route_nodes, durations_s)

    return {
        "vehicle_id": str(vehicle["id"]),
        "capacity": int(vehicle["capacity"]),
        "load": route_load,
        "orders": order_ids,
        "route": ["DEPOT"] + order_ids + ["DEPOT"],
        "points": route_points,
        "distance_m": distance_m,
        "distance_km": round(distance_m / 1000, 2),
        "duration_s": duration_s,
        "duration_min": round(duration_s / 60, 1) if duration_s else None,
    }


def _build_greedy_baseline(
    vehicles: list[dict[str, Any]],
    orders: list[dict[str, Any]],
    points: list[dict[str, Any]],
    distances_m: list[list[int]],
    durations_s: list[list[int]] | None,
) -> dict[str, Any] | None:
    """
    Baseline đơn giản để so sánh:
    - lần lượt xét từng xe;
    - tại vị trí hiện tại, chọn điểm chưa giao gần nhất mà xe còn đủ tải;
    - quay về kho khi không thể nhận thêm điểm;
    - thử một số thứ tự xe khác nhau và giữ phương án greedy tốt nhất.

    Đây là heuristic cơ sở, không phải thuật toán tối ưu toàn cục.
    """
    vehicle_count = len(vehicles)

    if vehicle_count <= 5:
        vehicle_orders = list(permutations(range(vehicle_count)))
    else:
        original = tuple(range(vehicle_count))
        by_capacity_desc = tuple(
            sorted(
                range(vehicle_count),
                key=lambda index: int(vehicles[index]["capacity"]),
                reverse=True,
            )
        )
        by_capacity_asc = tuple(reversed(by_capacity_desc))
        vehicle_orders = [original, by_capacity_desc, by_capacity_asc]

    # Giới hạn số lần thử để baseline luôn nhẹ.
    vehicle_orders = vehicle_orders[:120]

    best: dict[str, Any] | None = None
    all_order_nodes = set(range(1, len(orders) + 1))

    for vehicle_order in vehicle_orders:
        unassigned = set(all_order_nodes)
        assigned_by_vehicle: dict[int, list[int]] = {
            index: [] for index in range(vehicle_count)
        }
        feasible = True

        for vehicle_index in vehicle_order:
            capacity = int(vehicles[vehicle_index]["capacity"])
            remaining_capacity = capacity
            current_node = 0

            while unassigned:
                feasible_nodes = [
                    node
                    for node in unassigned
                    if int(orders[node - 1]["demand"]) <= remaining_capacity
                ]

                if not feasible_nodes:
                    break

                next_node = min(
                    feasible_nodes,
                    key=lambda node: (
                        distances_m[current_node][node],
                        -int(orders[node - 1]["demand"]),
                        str(orders[node - 1]["id"]),
                    ),
                )

                assigned_by_vehicle[vehicle_index].append(next_node)
                unassigned.remove(next_node)
                remaining_capacity -= int(orders[next_node - 1]["demand"])
                current_node = next_node

        if unassigned:
            feasible = False

        if not feasible:
            continue

        routes = []
        total_distance_m = 0
        total_duration_s = 0

        for vehicle_index, vehicle in enumerate(vehicles):
            route = _vehicle_orders_to_route(
                vehicle=vehicle,
                order_node_indexes=assigned_by_vehicle[vehicle_index],
                points=points,
                orders=orders,
                distances_m=distances_m,
                durations_s=durations_s,
            )
            routes.append(route)
            total_distance_m += route["distance_m"]
            total_duration_s += route["duration_s"]

        candidate = {
            "method": "Greedy nearest-neighbor có ràng buộc tải",
            "routes": routes,
            "total_distance_m": total_distance_m,
            "total_distance_km": round(total_distance_m / 1000, 2),
            "total_duration_s": total_duration_s,
            "total_duration_min": (
                round(total_duration_s / 60, 1)
                if total_duration_s
                else None
            ),
        }

        if best is None or total_distance_m < best["total_distance_m"]:
            best = candidate

    return best



def _refresh_baseline_with_road_geometry(
    baseline: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, str | None]:
    """
    Recalculate baseline route distance/time with the same OSRM Route service
    used for the optimized routes. This keeps the comparison consistent with
    the distances displayed on screen.
    """
    if baseline is None:
        return None, None

    total_distance_m = 0
    total_duration_s = 0
    warning = None

    for route in baseline["routes"]:
        if not route["orders"]:
            continue

        try:
            geometry_result = get_route_geometry(route["points"])

            if geometry_result.distance_m > 0:
                route["distance_m"] = geometry_result.distance_m
                route["distance_km"] = round(geometry_result.distance_m / 1000, 2)

            if geometry_result.duration_s > 0:
                route["duration_s"] = geometry_result.duration_s
                route["duration_min"] = round(geometry_result.duration_s / 60, 1)
        except RoadRoutingError as exc:
            warning = (
                "Không lấy được khoảng cách hiển thị cho một tuyến baseline; "
                f"đang dùng giá trị ma trận đường bộ: {exc}"
            )

        total_distance_m += route["distance_m"]
        total_duration_s += route["duration_s"]

    baseline["total_distance_m"] = total_distance_m
    baseline["total_distance_km"] = round(total_distance_m / 1000, 2)
    baseline["total_duration_s"] = total_duration_s
    baseline["total_duration_min"] = (
        round(total_duration_s / 60, 1) if total_duration_s else None
    )

    return baseline, warning

def optimize_cvrp(
    payload: dict[str, Any],
    include_geometry: bool = True,
    solver_time_limit_s: int = 3,
) -> dict[str, Any]:
    """
    Giải CVRP với ưu tiên khoảng cách đường bộ thực tế.

    Luồng:
    1. OSRM Table service -> ma trận khoảng cách/thời gian đường bộ.
    2. Tạo baseline greedy để có mốc so sánh.
    3. OR-Tools -> tối ưu phân công và thứ tự điểm.
    4. Khi include_geometry=True, OSRM Route service trả geometry để vẽ trên Leaflet.

    Nếu OSRM tạm thời không truy cập được, hệ thống hạ cấp về Haversine.
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

    baseline = _build_greedy_baseline(
        vehicles=vehicles,
        orders=orders,
        points=points,
        distances_m=distance_matrix,
        durations_s=durations_s,
    )

    if baseline and not is_fallback and include_geometry:
        baseline, baseline_warning = _refresh_baseline_with_road_geometry(baseline)
        if baseline_warning and not routing_warning:
            routing_warning = baseline_warning

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
    search_parameters.time_limit.seconds = max(1, int(solver_time_limit_s))

    solution = routing.SolveWithParameters(search_parameters)

    if solution is None:
        raise ValueError("Không tìm được phương án hợp lệ với dữ liệu hiện tại.")

    result_routes: list[dict[str, Any]] = []
    optimized_matrix_total_m = 0
    optimized_matrix_total_duration_s = 0
    display_total_distance_m = 0
    display_total_duration_s = 0

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

        matrix_route_duration_s = _route_duration_from_matrix(
            route_node_indexes,
            durations_s,
        )

        route_distance_m = matrix_route_distance_m
        route_duration_s = matrix_route_duration_s
        road_geometry: list[list[float]] = [
            [point["lat"], point["lng"]]
            for point in route_points
        ]

        if route_order_ids and not is_fallback and include_geometry:
            try:
                geometry_result = get_route_geometry(route_points)
                if geometry_result.coordinates:
                    road_geometry = geometry_result.coordinates
                if geometry_result.distance_m > 0:
                    route_distance_m = geometry_result.distance_m
                if geometry_result.duration_s > 0:
                    route_duration_s = geometry_result.duration_s
            except RoadRoutingError as exc:
                routing_warning = (
                    "Đã tối ưu bằng ma trận đường bộ, nhưng có tuyến không lấy "
                    f"được hình học đường đi: {exc}"
                )

        optimized_matrix_total_m += matrix_route_distance_m
        optimized_matrix_total_duration_s += matrix_route_duration_s
        display_total_distance_m += route_distance_m
        display_total_duration_s += route_duration_s

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

    comparison = None

    if baseline and baseline["total_distance_m"] > 0:
        # Compare both methods using the same distance source displayed to the user.
        optimized_comparison_distance_m = display_total_distance_m
        optimized_comparison_duration_s = display_total_duration_s

        saved_m = baseline["total_distance_m"] - optimized_comparison_distance_m
        improvement_percent = (
            saved_m / baseline["total_distance_m"] * 100
        )

        comparison = {
            "baseline_method": baseline["method"],
            "baseline_total_distance_m": baseline["total_distance_m"],
            "baseline_total_distance_km": baseline["total_distance_km"],
            "baseline_total_duration_min": baseline["total_duration_min"],
            "optimized_total_distance_m": optimized_comparison_distance_m,
            "optimized_total_distance_km": round(
                optimized_comparison_distance_m / 1000, 2
            ),
            "optimized_total_duration_min": (
                round(optimized_comparison_duration_s / 60, 1)
                if optimized_comparison_duration_s
                else None
            ),
            "distance_saved_m": saved_m,
            "distance_saved_km": round(saved_m / 1000, 2),
            "improvement_percent": round(improvement_percent, 2),
            "baseline_routes": baseline["routes"],
            "distance_source": (
                "OSRM Route service"
                if not is_fallback
                else "Haversine fallback"
            ),
        }

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
        "total_distance_m": display_total_distance_m,
        "total_distance_km": round(display_total_distance_m / 1000, 2),
        "total_duration_s": display_total_duration_s,
        "total_duration_min": (
            round(display_total_duration_s / 60, 1)
            if display_total_duration_s
            else None
        ),
        "comparison": comparison,
    }
