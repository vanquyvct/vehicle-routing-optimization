const payloadInput = document.getElementById("payload");
const optimizeBtn = document.getElementById("optimize-btn");
const resetBtn = document.getElementById("reset-btn");
const statusEl = document.getElementById("status");
const summaryEl = document.getElementById("summary");
const routesEl = document.getElementById("routes");
const rawOutputEl = document.getElementById("raw-output");

const defaultSample = JSON.parse(window.DEFAULT_SAMPLE);

function resetUI() {
    payloadInput.value = JSON.stringify(defaultSample, null, 2);
    statusEl.textContent = "Chưa chạy";
    statusEl.className = "status";
    summaryEl.className = "summary empty";
    summaryEl.textContent = "Nhấn “Chạy tối ưu tuyến” để bắt đầu.";
    routesEl.innerHTML = "";
    rawOutputEl.textContent = "";
}

resetBtn.addEventListener("click", resetUI);

optimizeBtn.addEventListener("click", async () => {
    let payload;

    try {
        payload = JSON.parse(payloadInput.value);
    } catch (error) {
        statusEl.textContent = "JSON lỗi";
        statusEl.className = "status error";
        summaryEl.className = "summary error-box";
        summaryEl.textContent = "Dữ liệu JSON không hợp lệ.";
        return;
    }

    optimizeBtn.disabled = true;
    statusEl.textContent = "Đang tính...";
    statusEl.className = "status running";
    summaryEl.className = "summary";
    summaryEl.textContent = "Solver đang tìm phương án.";
    routesEl.innerHTML = "";
    rawOutputEl.textContent = "";

    try {
        const response = await fetch("/api/optimize", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(payload),
        });

        const result = await response.json();
        rawOutputEl.textContent = JSON.stringify(result, null, 2);

        if (!response.ok) {
            throw new Error(result.message || "Không tối ưu được.");
        }

        statusEl.textContent = "Thành công";
        statusEl.className = "status success";
        summaryEl.className = "summary";
        summaryEl.innerHTML = `
            <strong>Tổng quãng đường:</strong>
            ${result.total_distance_km.toFixed(2)} km
            <br>
            <span>${result.algorithm} · ${result.distance_method}</span>
        `;

        routesEl.innerHTML = result.routes.map((route) => `
            <article class="route-card">
                <div class="route-top">
                    <h3>${route.vehicle_id}</h3>
                    <span>${route.load}/${route.capacity}</span>
                </div>
                <p class="route-path">${route.route.join(" → ")}</p>
                <p class="route-meta">
                    ${route.distance_km.toFixed(2)} km · ${route.orders.length} đơn
                </p>
            </article>
        `).join("");
    } catch (error) {
        statusEl.textContent = "Có lỗi";
        statusEl.className = "status error";
        summaryEl.className = "summary error-box";
        summaryEl.textContent = error.message;
    } finally {
        optimizeBtn.disabled = false;
    }
});

resetUI();
