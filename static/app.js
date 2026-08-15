const defaultSample = JSON.parse(window.DEFAULT_SAMPLE);

const depotNameInput = document.getElementById("depot-name");
const depotLatInput = document.getElementById("depot-lat");
const depotLngInput = document.getElementById("depot-lng");

const vehicleList = document.getElementById("vehicle-list");
const orderList = document.getElementById("order-list");

const vehicleTemplate = document.getElementById("vehicle-template");
const orderTemplate = document.getElementById("order-template");

const addVehicleBtn = document.getElementById("add-vehicle-btn");
const addOrderBtn = document.getElementById("add-order-btn");
const addOrderModeBtn = document.getElementById("add-order-mode-btn");
const pickDepotBtn = document.getElementById("pick-depot-btn");
const optimizeBtn = document.getElementById("optimize-btn");
const resetBtn = document.getElementById("reset-btn");

const messageEl = document.getElementById("message");
const statusBadge = document.getElementById("status-badge");
const resultSummary = document.getElementById("result-summary");
const routeResults = document.getElementById("route-results");
const mapModeEl = document.getElementById("map-mode");

const map = L.map("map", {
    zoomControl: true,
}).setView([21.0285, 105.8542], 13);

L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
}).addTo(map);

const depotLayer = L.layerGroup().addTo(map);
const orderLayer = L.layerGroup().addTo(map);
const routeLayer = L.layerGroup().addTo(map);

let mapMode = null;

const routeColors = [
    "#3b5bdb",
    "#e8590c",
    "#2f9e44",
    "#ae3ec9",
    "#0b7285",
    "#c2255c",
    "#5f3dc4",
    "#9c6f19",
];

function cleanNumber(value, fieldName) {
    if (value === "" || value === null || value === undefined) {
        throw new Error(`${fieldName} không được để trống.`);
    }

    const number = Number(value);

    if (!Number.isFinite(number)) {
        throw new Error(`${fieldName} phải là số.`);
    }

    return number;
}

function showMessage(text, type = "error") {
    messageEl.textContent = text;
    messageEl.className = `message ${type}`;
}

function hideMessage() {
    messageEl.textContent = "";
    messageEl.className = "message hidden";
}

function setStatus(text, type = "") {
    statusBadge.textContent = text;
    statusBadge.className = `status-badge ${type}`.trim();
}

function setMapMode(mode) {
    mapMode = mode;

    if (mode === "depot") {
        mapModeEl.textContent = "Chế độ chọn kho: click một vị trí trên bản đồ";
        mapModeEl.classList.remove("hidden");
        pickDepotBtn.classList.add("active");
        addOrderModeBtn.classList.remove("active");
    } else if (mode === "order") {
        mapModeEl.textContent = "Chế độ thêm đơn: click một vị trí trên bản đồ";
        mapModeEl.classList.remove("hidden");
        addOrderModeBtn.classList.add("active");
        pickDepotBtn.classList.remove("active");
    } else {
        mapModeEl.classList.add("hidden");
        pickDepotBtn.classList.remove("active");
        addOrderModeBtn.classList.remove("active");
    }
}

function makeDepotIcon() {
    return L.divIcon({
        className: "",
        html: '<div class="map-marker depot-marker">K</div>',
        iconSize: [36, 36],
        iconAnchor: [18, 18],
    });
}

function makeOrderIcon(id) {
    return L.divIcon({
        className: "",
        html: `<div class="map-marker order-marker">${id.replace(/^DH/i, "")}</div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
    });
}

function addVehicleRow(vehicle = null) {
    const fragment = vehicleTemplate.content.cloneNode(true);
    const card = fragment.querySelector(".vehicle-card");

    const index = vehicleList.children.length + 1;

    card.querySelector(".vehicle-id").value =
        vehicle?.id ?? `XE${String(index).padStart(2, "0")}`;

    card.querySelector(".vehicle-capacity").value =
        vehicle?.capacity ?? 15;

    card.querySelector(".remove-vehicle").addEventListener("click", () => {
        card.remove();
        hideMessage();
    });

    vehicleList.appendChild(fragment);
}

function addOrderRow(order = null) {
    const fragment = orderTemplate.content.cloneNode(true);
    const card = fragment.querySelector(".order-card");

    const index = orderList.children.length + 1;

    card.querySelector(".order-id").value =
        order?.id ?? `DH${String(index).padStart(2, "0")}`;

    card.querySelector(".order-demand").value =
        order?.demand ?? 1;

    card.querySelector(".order-lat").value =
        order?.lat ?? map.getCenter().lat.toFixed(6);

    card.querySelector(".order-lng").value =
        order?.lng ?? map.getCenter().lng.toFixed(6);

    card.querySelector(".remove-order").addEventListener("click", () => {
        card.remove();
        renderInputMarkers();
        clearResult();
    });

    card.querySelectorAll("input").forEach((input) => {
        input.addEventListener("change", () => {
            renderInputMarkers();
            clearResult();
        });
    });

    orderList.appendChild(fragment);
    renderInputMarkers();
}

function collectPayload() {
    const depot = {
        name: depotNameInput.value.trim() || "Kho",
        lat: cleanNumber(depotLatInput.value, "Vĩ độ kho"),
        lng: cleanNumber(depotLngInput.value, "Kinh độ kho"),
    };

    const vehicles = [...vehicleList.querySelectorAll(".vehicle-card")].map((card, index) => {
        const id = card.querySelector(".vehicle-id").value.trim();
        const capacity = cleanNumber(
            card.querySelector(".vehicle-capacity").value,
            `Sức chứa xe ${index + 1}`,
        );

        if (!id) {
            throw new Error(`Mã xe ${index + 1} không được để trống.`);
        }

        return {id, capacity: Math.trunc(capacity)};
    });

    const orders = [...orderList.querySelectorAll(".order-card")].map((card, index) => {
        const id = card.querySelector(".order-id").value.trim();

        if (!id) {
            throw new Error(`Mã đơn ${index + 1} không được để trống.`);
        }

        return {
            id,
            demand: Math.trunc(
                cleanNumber(
                    card.querySelector(".order-demand").value,
                    `Nhu cầu đơn ${id}`,
                )
            ),
            lat: cleanNumber(
                card.querySelector(".order-lat").value,
                `Vĩ độ đơn ${id}`,
            ),
            lng: cleanNumber(
                card.querySelector(".order-lng").value,
                `Kinh độ đơn ${id}`,
            ),
        };
    });

    return {depot, vehicles, orders};
}

function clearResult() {
    routeLayer.clearLayers();
    setStatus("Chưa chạy");
    resultSummary.className = "result-summary empty";
    resultSummary.textContent = "Nhấn “Tối ưu tuyến” để hệ thống tính phương án.";
    routeResults.innerHTML = "";
}

function renderInputMarkers(fit = false) {
    depotLayer.clearLayers();
    orderLayer.clearLayers();

    const bounds = [];

    const depotLat = Number(depotLatInput.value);
    const depotLng = Number(depotLngInput.value);

    if (Number.isFinite(depotLat) && Number.isFinite(depotLng)) {
        const marker = L.marker(
            [depotLat, depotLng],
            {icon: makeDepotIcon()}
        )
            .bindPopup(`<strong>${depotNameInput.value || "Kho"}</strong>`)
            .addTo(depotLayer);

        bounds.push(marker.getLatLng());
    }

    [...orderList.querySelectorAll(".order-card")].forEach((card) => {
        const id = card.querySelector(".order-id").value.trim() || "DH";
        const demand = card.querySelector(".order-demand").value;
        const lat = Number(card.querySelector(".order-lat").value);
        const lng = Number(card.querySelector(".order-lng").value);

        if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
            return;
        }

        const marker = L.marker(
            [lat, lng],
            {icon: makeOrderIcon(id)}
        )
            .bindPopup(`<strong>${id}</strong><br>Nhu cầu: ${demand}`)
            .addTo(orderLayer);

        bounds.push(marker.getLatLng());
    });

    if (fit && bounds.length >= 2) {
        map.fitBounds(L.latLngBounds(bounds).pad(0.15));
    } else if (fit && bounds.length === 1) {
        map.setView(bounds[0], 14);
    }
}


function makeRouteSequenceIcon(sequence, color) {
    return L.divIcon({
        className: "",
        html: `
            <div class="route-sequence-marker" style="--sequence-color:${color}">
                ${sequence}
            </div>
        `,
        iconSize: [30, 30],
        iconAnchor: [15, 15],
    });
}

function renderRoutes(result) {
    routeLayer.clearLayers();

    const activeRoutes = result.routes.filter((route) => route.orders.length > 0);

    routeResults.innerHTML = activeRoutes.map((route, index) => {
        const color = routeColors[index % routeColors.length];

        const numberedStops = route.orders
            .map((orderId, stopIndex) => `${stopIndex + 1}. ${orderId}`)
            .join(" → ");

        return `
            <article class="route-result" style="--route-color:${color}">
                <div class="route-result-top">
                    <div>
                        <span class="route-swatch"></span>
                        <strong>${route.vehicle_id}</strong>
                    </div>

                    <span>${route.load}/${route.capacity}</span>
                </div>

                <p class="route-path">
                    <span class="depot-label">Kho</span>
                    ${numberedStops ? ` → ${numberedStops}` : ""}
                    → <span class="depot-label">Kho</span>
                </p>

                <div class="route-stats">
                    <span>${route.distance_km.toFixed(2)} km</span>
                    ${
                        route.duration_min !== null && route.duration_min !== undefined
                            ? `<span>≈ ${route.duration_min.toFixed(1)} phút</span>`
                            : ""
                    }
                    <span>${route.orders.length} điểm giao</span>
                </div>
            </article>
        `;
    }).join("");

    const routeBounds = [];

    activeRoutes.forEach((route, index) => {
        const color = routeColors[index % routeColors.length];
        const latLngs = (
            route.geometry && route.geometry.length
                ? route.geometry
                : route.points.map((point) => [point.lat, point.lng])
        );

        L.polyline(latLngs, {
            color,
            weight: 5,
            opacity: 0.86,
        }).addTo(routeLayer);

        // route.points = [DEPOT, điểm 1, điểm 2, ..., DEPOT].
        // Đánh số các điểm giao theo đúng thứ tự xe phải ghé.
        route.points.slice(1, -1).forEach((point, stopIndex) => {
            const sequence = stopIndex + 1;

            L.marker(
                [point.lat, point.lng],
                {
                    icon: makeRouteSequenceIcon(sequence, color),
                    zIndexOffset: 1000 + sequence,
                }
            )
                .bindPopup(`
                    <strong>${route.vehicle_id}</strong><br>
                    Thứ tự: ${sequence}<br>
                    Điểm giao: ${point.id}
                `)
                .bindTooltip(
                    `${route.vehicle_id} · ${sequence}. ${point.id}`,
                    {
                        direction: "top",
                        offset: [0, -12],
                    }
                )
                .addTo(routeLayer);
        });

        latLngs.forEach((latLng) => routeBounds.push(latLng));
    });

    if (routeBounds.length) {
        map.fitBounds(L.latLngBounds(routeBounds).pad(0.15));
    }
}

function loadSample() {
    depotNameInput.value = defaultSample.depot.name ?? "Kho trung tâm";
    depotLatInput.value = defaultSample.depot.lat;
    depotLngInput.value = defaultSample.depot.lng;

    vehicleList.innerHTML = "";
    defaultSample.vehicles.forEach((vehicle) => addVehicleRow(vehicle));

    orderList.innerHTML = "";
    defaultSample.orders.forEach((order) => addOrderRow(order));

    hideMessage();
    setMapMode(null);
    clearResult();
    renderInputMarkers(true);
}

addVehicleBtn.addEventListener("click", () => {
    addVehicleRow();
    clearResult();
});

addOrderBtn.addEventListener("click", () => {
    addOrderRow();
    clearResult();
});

pickDepotBtn.addEventListener("click", () => {
    setMapMode(mapMode === "depot" ? null : "depot");
});

addOrderModeBtn.addEventListener("click", () => {
    setMapMode(mapMode === "order" ? null : "order");
});

map.on("click", (event) => {
    if (mapMode === "depot") {
        depotLatInput.value = event.latlng.lat.toFixed(6);
        depotLngInput.value = event.latlng.lng.toFixed(6);
        renderInputMarkers();
        clearResult();
        setMapMode(null);
        return;
    }

    if (mapMode === "order") {
        addOrderRow({
            id: `DH${String(orderList.children.length + 1).padStart(2, "0")}`,
            demand: 1,
            lat: Number(event.latlng.lat.toFixed(6)),
            lng: Number(event.latlng.lng.toFixed(6)),
        });
        clearResult();
    }
});

[depotNameInput, depotLatInput, depotLngInput].forEach((input) => {
    input.addEventListener("change", () => {
        renderInputMarkers();
        clearResult();
    });
});

resetBtn.addEventListener("click", loadSample);

optimizeBtn.addEventListener("click", async () => {
    hideMessage();

    let payload;

    try {
        payload = collectPayload();
    } catch (error) {
        showMessage(error.message);
        return;
    }

    if (!payload.vehicles.length) {
        showMessage("Phải có ít nhất một phương tiện.");
        return;
    }

    if (!payload.orders.length) {
        showMessage("Phải có ít nhất một đơn hàng.");
        return;
    }

    optimizeBtn.disabled = true;
    optimizeBtn.textContent = "Đang tối ưu...";
    setStatus("Đang tính", "running");

    try {
        const response = await fetch("/api/optimize", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(payload),
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.message || "Không tối ưu được dữ liệu hiện tại.");
        }

        setStatus("Thành công", "success");

        resultSummary.className = "result-summary";
        resultSummary.innerHTML = `
            <div>
                <span>Tổng quãng đường</span>
                <strong>${result.total_distance_km.toFixed(2)} km</strong>
            </div>

            <div>
                <span>Nguồn định tuyến</span>
                <strong>${result.is_fallback ? "Haversine dự phòng" : "OSRM / đường bộ"}</strong>
            </div>

            <div>
                <span>${
                    result.total_duration_min !== null && result.total_duration_min !== undefined
                        ? "Tổng thời gian ước tính"
                        : "Số xe sử dụng"
                }</span>
                <strong>${
                    result.total_duration_min !== null && result.total_duration_min !== undefined
                        ? `${result.total_duration_min.toFixed(1)} phút`
                        : result.routes.filter((route) => route.orders.length).length
                }</strong>
            </div>
        `;

        renderRoutes(result);

        if (result.is_fallback) {
            showMessage(
                `OSRM chưa sử dụng được nên hệ thống đang chạy chế độ dự phòng Haversine. ${result.warning || ""}`,
                "warning",
            );
        } else if (result.warning) {
            showMessage(result.warning, "warning");
        } else {
            showMessage(
                "Đã tối ưu bằng khoảng cách đường bộ và vẽ tuyến theo mạng đường thực tế.",
                "success",
            );
        }
    } catch (error) {
        setStatus("Có lỗi", "error");
        routeLayer.clearLayers();
        resultSummary.className = "result-summary empty";
        resultSummary.textContent = "Không thể tạo phương án với dữ liệu hiện tại.";
        routeResults.innerHTML = "";
        showMessage(error.message);
    } finally {
        optimizeBtn.disabled = false;
        optimizeBtn.textContent = "Tối ưu tuyến";
    }
});

loadSample();
