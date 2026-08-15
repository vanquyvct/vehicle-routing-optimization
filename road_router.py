from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


OSRM_BASE_URL = "https://router.project-osrm.org"
OSRM_PROFILE = "driving"
DEFAULT_TIMEOUT_SECONDS = 10


class RoadRoutingError(RuntimeError):
    """Raised when the external road-routing service cannot return a usable result."""


@dataclass
class MatrixResult:
    distances_m: list[list[int]]
    durations_s: list[list[int]]


@dataclass
class RouteGeometryResult:
    coordinates: list[list[float]]
    distance_m: int
    duration_s: int


def _coordinates_string(points: list[dict[str, Any]]) -> str:
    """
    OSRM expects coordinates in longitude,latitude order.
    Our application stores them as lat/lng.
    """
    return ";".join(
        f"{float(point['lng']):.6f},{float(point['lat']):.6f}"
        for point in points
    )


def _get_json(url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "User-Agent": "vehicle-routing-tttn/1.0",
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RoadRoutingError(f"Không kết nối được dịch vụ định tuyến đường bộ: {exc}") from exc

    if payload.get("code") != "Ok":
        message = payload.get("message") or payload.get("code") or "Unknown OSRM error"
        raise RoadRoutingError(f"Dịch vụ định tuyến trả lỗi: {message}")

    return payload


def get_road_matrix(points: list[dict[str, Any]]) -> MatrixResult:
    """
    Return all-pairs road distances/durations from OSRM Table service.

    Distances are the distances of the fastest routes, in meters.
    Durations are in seconds.
    """
    if not points:
        raise RoadRoutingError("Không có tọa độ để tạo ma trận đường bộ.")

    coords = _coordinates_string(points)
    query = urlencode({"annotations": "distance,duration"})
    url = f"{OSRM_BASE_URL}/table/v1/{OSRM_PROFILE}/{coords}?{query}"

    payload = _get_json(url)

    raw_distances = payload.get("distances")
    raw_durations = payload.get("durations")

    if not raw_distances or not raw_durations:
        raise RoadRoutingError("OSRM không trả về đầy đủ ma trận khoảng cách/thời gian.")

    distances_m: list[list[int]] = []
    durations_s: list[list[int]] = []

    for row in raw_distances:
        if any(value is None for value in row):
            raise RoadRoutingError("Có cặp điểm không tìm được đường đi bằng ô tô.")
        distances_m.append([int(round(float(value))) for value in row])

    for row in raw_durations:
        if any(value is None for value in row):
            raise RoadRoutingError("Có cặp điểm không tìm được thời gian di chuyển.")
        durations_s.append([int(round(float(value))) for value in row])

    return MatrixResult(
        distances_m=distances_m,
        durations_s=durations_s,
    )


def get_route_geometry(points: list[dict[str, Any]]) -> RouteGeometryResult:
    """
    Route through the supplied points in the given order and return road geometry.

    Returned coordinates are converted to [lat, lng] for Leaflet.
    """
    if len(points) < 2:
        return RouteGeometryResult(
            coordinates=[],
            distance_m=0,
            duration_s=0,
        )

    coords = _coordinates_string(points)
    query = urlencode(
        {
            "alternatives": "false",
            "steps": "false",
            "geometries": "geojson",
            "overview": "full",
        }
    )
    url = f"{OSRM_BASE_URL}/route/v1/{OSRM_PROFILE}/{coords}?{query}"

    payload = _get_json(url)
    routes = payload.get("routes") or []

    if not routes:
        raise RoadRoutingError("OSRM không trả về tuyến đường.")

    route = routes[0]
    geometry = route.get("geometry", {})
    raw_coordinates = geometry.get("coordinates") or []

    # GeoJSON uses [longitude, latitude]. Leaflet needs [latitude, longitude].
    leaflet_coordinates = [
        [float(latitude), float(longitude)]
        for longitude, latitude in raw_coordinates
    ]

    return RouteGeometryResult(
        coordinates=leaflet_coordinates,
        distance_m=int(round(float(route.get("distance", 0)))),
        duration_s=int(round(float(route.get("duration", 0)))),
    )
