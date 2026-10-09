const TMS = {
    branches: [],
    currentBranchId: null,
    map: null,
    markers: [],

    async api(path, options = {}) {
        const res = await fetch(path, {
            headers: { "Content-Type": "application/json" },
            ...options,
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || "APIエラーが発生しました");
        }
        return res.json();
    },

    async loadBranches() {
        this.branches = await this.api("/api/branches");
        if (this.branches.length > 0 && !this.currentBranchId) {
            const saved = parseInt(localStorage.getItem("tms_selected_branch_id"), 10);
            const found = this.branches.find((b) => b.id === saved);
            this.currentBranchId = found ? found.id : this.branches[0].id;
        }
        return this.branches;
    },

    getBranch(id) {
        return this.branches.find((b) => b.id === id);
    },

    statusLabel(status) {
        const labels = {
            created: "受付済",
            in_hub: "営業所保管",
            delivering: "配達中",
            completed: "配達完了",
        };
        return labels[status] || status;
    },

    vehicleLabel(vtype) {
        const labels = { moped: "原付", motorcycle: "バイク", van: "軽バン" };
        return labels[vtype] || vtype;
    },

    employmentLabel(etype) {
        return etype === "employee" ? "社員" : "業務委託";
    },

    formatDate(dt) {
        const d = new Date(dt);
        return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
    },

    initMap(elementId, lat, lng, zoom = 13) {
        if (this.map) {
            this.map.remove();
            this.map = null;
            this.markers = [];
        }
        this.map = L.map(elementId).setView([lat, lng], zoom);
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
            maxZoom: 19,
        }).addTo(this.map);
        return this.map;
    },

    clearMarkers() {
        this.markers.forEach((m) => m.remove());
        this.markers = [];
    },

    addBranchMarker(branch) {
        const icon = L.divIcon({
            className: "",
            html: `<div style="background:#2563eb;color:#fff;width:30px;height:30px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);display:flex;align-items:center;justify-content:center;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,0.4);"><span style="transform:rotate(45deg);font-size:14px;">🏬</span></div>`,
            iconSize: [30, 30],
            iconAnchor: [15, 30],
        });
        const marker = L.marker([branch.lat, branch.lng], { icon })
            .addTo(this.map)
            .bindPopup(`<b>${branch.name}</b><br>${branch.address}`);
        this.markers.push(marker);
    },

    addShipmentMarker(shipment) {
        const colors = {
            created: "#6366f1",
            in_hub: "#f59e0b",
            delivering: "#3b82f6",
            completed: "#10b981",
        };
        const color = colors[shipment.status] || "#6b7280";
        const icon = L.divIcon({
            className: "",
            html: `<div style="background:${color};color:#fff;width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,0.4);font-size:12px;">📦</div>`,
            iconSize: [26, 26],
            iconAnchor: [13, 13],
        });
        const marker = L.marker([shipment.delivery_lat, shipment.delivery_lng], { icon })
            .addTo(this.map)
            .bindPopup(
                `<b>${shipment.tracking_number}</b><br>${shipment.recipient_name}<br>${this.statusLabel(shipment.status)}`
            );
        this.markers.push(marker);
    },

    addDriverMarker(driver) {
        const icons = { moped: "🛵", motorcycle: "🏍️", van: "🚐" };
        const icon = L.divIcon({
            className: "",
            html: `<div style="background:#fff;border:2px solid #1f2937;border-radius:50%;width:30px;height:30px;display:flex;align-items:center;justify-content:center;font-size:15px;box-shadow:0 1px 4px rgba(0,0,0,0.4);">${icons[driver.vehicle_type] || "🚗"}</div>`,
            iconSize: [30, 30],
            iconAnchor: [15, 15],
        });
        const marker = L.marker([driver.current_lat, driver.current_lng], { icon })
            .addTo(this.map)
            .bindPopup(
                `<b>${driver.name}</b><br>${this.vehicleLabel(driver.vehicle_type)} / ${this.employmentLabel(driver.employment_type)}<br>ステータス: ${driver.status}`
            );
        this.markers.push(marker);
    },

    fitMarkers() {
        if (this.markers.length > 0 && this.map) {
            const group = L.featureGroup(this.markers);
            this.map.fitBounds(group.getBounds().pad(0.15));
        }
    },

    addRoutePolyline(coords, color = "#3b82f6", dashed = false) {
        if (!this.map || coords.length < 2) return null;
        const line = L.polyline(coords, {
            color: color,
            weight: 4,
            opacity: 0.8,
            dashArray: dashed ? "8, 8" : null,
        }).addTo(this.map);
        this.markers.push(line);
        return line;
    },

    async fetchOsrmRoute(fromLat, fromLng, toLat, toLng) {
        try {
            const url = `https://router.project-osrm.org/route/v1/driving/${fromLng},${fromLat};${toLng},${toLat}?overview=full&geometries=geojson`;
            const res = await fetch(url);
            if (!res.ok) return null;
            const data = await res.json();
            if (data.code !== "Ok" || !data.routes || data.routes.length === 0) return null;
            return data.routes[0].geometry.coordinates.map((c) => [c[1], c[0]]);
        } catch (e) {
            return null;
        }
    },

    async drawRoute(fromLat, fromLng, toLat, toLng, color, dashed = false) {
        const routeCoords = await this.fetchOsrmRoute(fromLat, fromLng, toLat, toLng);
        if (routeCoords && routeCoords.length > 1) {
            return this.addRoutePolyline(routeCoords, color, dashed);
        }
        return this.addRoutePolyline([[fromLat, fromLng], [toLat, toLng]], color, true);
    },

    addNumberedShipmentMarker(shipment, order) {
        const colors = {
            created: "#6366f1",
            in_hub: "#f59e0b",
            delivering: "#3b82f6",
            completed: "#10b981",
        };
        const color = colors[shipment.status] || "#6b7280";
        const circled = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩"];
        const label = order ? circled[order - 1] || String(order) : "📦";
        const icon = L.divIcon({
            className: "",
            html: `<div style="background:${color};color:#fff;width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,0.4);font-size:13px;font-weight:bold;">${label}</div>`,
            iconSize: [28, 28],
            iconAnchor: [14, 14],
        });
        const marker = L.marker([shipment.delivery_lat, shipment.delivery_lng], { icon })
            .addTo(this.map)
            .bindPopup(
                `<b>${shipment.tracking_number}</b><br>${shipment.recipient_name}<br>${this.statusLabel(shipment.status)}${order ? `<br>配送順: ${order}番目` : ""}`
            );
        this.markers.push(marker);
    },

    addDriverMarkerWithColor(driver, color = "#1f2937") {
        const icons = { moped: "🛵", motorcycle: "🏍️", van: "🚐" };
        const icon = L.divIcon({
            className: "",
            html: `<div style="background:#fff;border:3px solid ${color};border-radius:50%;width:32px;height:32px;display:flex;align-items:center;justify-content:center;font-size:16px;box-shadow:0 1px 4px rgba(0,0,0,0.4);">${icons[driver.vehicle_type] || "🚗"}</div>`,
            iconSize: [32, 32],
            iconAnchor: [16, 16],
        });
        const marker = L.marker([driver.current_lat, driver.current_lng], { icon })
            .addTo(this.map)
            .bindPopup(
                `<b>${driver.name}</b><br>${this.vehicleLabel(driver.vehicle_type)} / ${this.employmentLabel(driver.employment_type)}<br>ステータス: ${driver.status}`
            );
        this.markers.push(marker);
    },

    showToast(message, isError = false) {
        const toast = document.createElement("div");
        toast.className = `fixed bottom-4 right-4 z-[2000] px-4 py-3 rounded-lg shadow-lg text-white text-sm font-medium ${isError ? "bg-red-600" : "bg-green-600"}`;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3500);
    },

    async resetDemo() {
        if (!confirm("デモデータを初期状態にリセットしますか？")) return;
        try {
            await this.api("/api/demo/reset", { method: "POST" });
            this.showToast("デモデータを初期化しました");
            if (typeof onDemoReset === "function") {
                await onDemoReset();
            }
        } catch (e) {
            this.showToast(e.message, true);
        }
    },

    renderNav(activePage) {
        const nav = document.getElementById("main-nav");
        if (!nav) return;
        const tabs = [
            { id: "admin", label: "🌐 本部", href: "/admin" },
            { id: "branch", label: "🏬 営業所", href: "/branch" },
            { id: "driver", label: "🛵 ドライバー", href: "/driver" },
            { id: "customer", label: "📱 顧客追跡", href: "/customer" },
        ];
        nav.innerHTML = `
            <div class="flex items-center gap-1 flex-wrap">
                ${tabs
                    .map(
                        (t) =>
                            `<a href="${t.href}" class="nav-tab ${t.id === activePage ? "active" : ""}">${t.label}</a>`
                    )
                    .join("")}
            </div>
            <div class="flex items-center gap-2 flex-wrap">
                <select id="branch-select" class="!w-auto text-sm">
                    ${this.branches
                        .map(
                            (b) =>
                                `<option value="${b.id}" ${b.id === this.currentBranchId ? "selected" : ""}>${b.name}</option>`
                        )
                        .join("")}
                </select>
                <button id="reset-btn" class="btn-danger text-sm">🔄 デモデータ初期化</button>
            </div>
        `;
        document.getElementById("branch-select").addEventListener("change", (e) => {
            this.currentBranchId = parseInt(e.target.value, 10);
            localStorage.setItem("tms_selected_branch_id", this.currentBranchId);
            if (typeof onBranchChange === "function") {
                onBranchChange(this.currentBranchId);
            }
        });
        document.getElementById("reset-btn").addEventListener("click", () => this.resetDemo());
    },
};
