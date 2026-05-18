const API_BASE = "http://localhost:8000";

const map = L.map("map").setView([37.4218, -122.0842], 16);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

let marker = null;
let polyline = null;
let pastCycle = null;
const failMarkers = new Map();
let currentLoopFlag = true;

function createCarIcon(heading = 0) {
  const angle = Number.isFinite(heading) ? heading : 0;
  return L.divIcon({
    className: "car-position-marker",
    html: `
      <img
        src="/static/image/car-icon.svg"
        alt="current vehicle"
        style="width:38px;height:38px;transform:rotate(${angle}deg);transform-origin:center center;"
      />
    `,
    iconSize: [38, 38],
    iconAnchor: [19, 19],
  });
}

const failIcon = L.icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

function formatNumber(value, digits = 6) {
  return typeof value === "number" ? value.toFixed(digits) : "-";
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value ?? "-";
}

function modeLabel(mode) {
  return mode === "live" ? "실시간 검증" : "테스트 주행";
}

function setModeStatus(text) {
  setText("mode-status", text);
}

function resetDrivingLayer() {
  if (marker) {
    map.removeLayer(marker);
    marker = null;
  }
  if (polyline) {
    map.removeLayer(polyline);
    polyline = null;
  }
  failMarkers.forEach((item) => map.removeLayer(item));
  failMarkers.clear();
  pastCycle = null;
}

function drawTrack() {
  fetch(`${API_BASE}/track`)
    .then((res) => res.json())
    .then((track) => {
      const latlngs = track
        .filter((p) => p.latitude !== null && p.longitude !== null)
        .map((p) => [p.latitude, p.longitude]);
      if (!latlngs.length) return;
      L.polyline(latlngs, { color: "#0f4c81", weight: 8, opacity: 0.7 }).addTo(map);
      map.fitBounds(latlngs, { padding: [30, 30] });
    })
    .catch((err) => console.error("Failed to load track:", err));
}

function updatePath(data) {
  if (data.cycle !== pastCycle) {
    pastCycle = data.cycle;
    if (polyline) {
      map.removeLayer(polyline);
      polyline = null;
    }
  }

  const path = Array.isArray(data.path) ? data.path : [];
  const polyPath = path
    .filter((p) => p.latitude !== null && p.longitude !== null)
    .map((p) => [p.latitude, p.longitude]);

  if (!polyPath.length) return;

  if (!polyline) {
    polyline = L.polyline(polyPath, { color: "#1e7145", weight: 6, opacity: 0.85 }).addTo(map);
  } else {
    polyline.setLatLngs(polyPath);
  }
}

function updateMarker(current) {
  if (!current?.latitude || !current?.longitude) return;

  const latlng = [current.latitude, current.longitude];
  const heading = current.true_course ?? 0;
  if (marker) {
    marker.setLatLng(latlng);
    marker.setIcon(createCarIcon(heading));
  } else {
    marker = L.marker(latlng, { icon: createCarIcon(heading) }).addTo(map);
  }
  map.setView(latlng, map.getZoom());
}

function updateInfo(data) {
  const current = data.current;
  const comparison = data.comparison;

  setText("info-time", current?.timestamp);
  setText("info-lat", formatNumber(current?.latitude));
  setText("info-lon", formatNumber(current?.longitude));
  setText("info-speed", current?.spd_over_grnd ? `${current.spd_over_grnd.toFixed(2)} km/h` : "-");
  setText("info-heading", current?.true_course ? `${current.true_course.toFixed(2)} deg` : "-");

  const resultElem = document.getElementById("info-result");
  if (!comparison) {
    resultElem.textContent = "-";
    resultElem.className = "";
    setText("info-reason", "-");
    return;
  }

  resultElem.textContent = comparison.pass ? "PASS" : "FAIL";
  resultElem.className = comparison.pass ? "pass" : "fail";
  setText("info-reason", comparison.reason || "-");
}

function updateFailures(failures) {
  const activeKeys = new Set();

  (failures || []).forEach((f) => {
    if (!f.latitude || !f.longitude) return;
    const key = `${f.cycle ?? "-"}:${f.timestamp ?? "-"}:${f.latitude}:${f.longitude}`;
    activeKeys.add(key);
    const popupHtml = `
      <div style="font-size:13px;">
        <strong style="color:#c0392b;">FAIL</strong><br>
        <strong>위도:</strong> ${f.latitude}<br>
        <strong>경도:</strong> ${f.longitude}<br>
        <strong>속도:</strong> ${f.spd_over_grnd ?? "-"}<br>
        <strong>방향:</strong> ${f.true_course ?? "-"}<br>
        <strong>사유:</strong> ${f.reason ?? "-"}<br>
      </div>
    `;

    if (failMarkers.has(key)) {
      failMarkers.get(key).setPopupContent(popupHtml);
      return;
    }

    const failMarker = L.marker([f.latitude, f.longitude], { icon: failIcon }).addTo(map);
    failMarker.bindPopup(popupHtml, {
      autoClose: false,
      closeOnClick: false,
      closeButton: true,
      keepInView: true,
    });
    failMarkers.set(key, failMarker);
  });

  failMarkers.forEach((item, key) => {
    if (!activeKeys.has(key)) {
      map.removeLayer(item);
      failMarkers.delete(key);
    }
  });
}

function currentLoop() {
  if (!currentLoopFlag) return;

  fetch(`${API_BASE}/current`)
    .then((res) => res.json())
    .then((data) => {
      updatePath(data);
      updateMarker(data.current);
      updateInfo(data);
      updateFailures(data.fail);
      setModeStatus(`${modeLabel(data.mode)} · ${data.running ? "실행 중" : "대기 중"}`);
    })
    .catch((err) => console.error("Failed to load current data:", err));
}

function currentLoopOnOff(flag) {
  currentLoopFlag = flag;
}

function startBackend() {
  const mode = document.getElementById("drive-mode").value;
  resetDrivingLayer();
  fetch(`${API_BASE}/start-driving?mode=${encodeURIComponent(mode)}`, { method: "POST" })
    .then((res) => res.json())
    .then((data) => {
      console.log(data.message);
      setModeStatus(`${modeLabel(data.mode)} · 실행 중`);
    });
}

function stopBackend() {
  fetch(`${API_BASE}/stop-driving`, { method: "POST" })
    .then((res) => res.json())
    .then((data) => {
      console.log(data.message);
      setModeStatus(`${modeLabel(data.mode)} · 중지됨`);
    });
}

document.getElementById("save-btn").addEventListener("click", () => {
  fetch(`${API_BASE}/generate-excel`)
    .then((res) => {
      if (!res.ok) throw new Error(`download failed: ${res.status}`);
      return res.blob();
    })
    .then((blob) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report_${new Date().toISOString().slice(0, 19)}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    })
    .catch((err) => alert(`리포트 다운로드 실패: ${err.message}`));
});

drawTrack();
setInterval(currentLoop, 1000);
