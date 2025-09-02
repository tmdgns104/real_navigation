// ✅ 전체 수정된 map.js 코드

let path = [];
let polyline = null;
let marker = null;
let intervalId = null;
let prevTimestamp = null;  // 이전 타임스탬프

// Leaflet 지도 초기화
const map = L.map('map').setView([37.5, 127], 13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
}).addTo(map);

// 기준 경로 불러오기
fetch("http://localhost:8000/track")
  .then(res => res.json())
  .then(track => {
    const latlngs = track.map(p => [p.latitude, p.longitude]);
    L.polyline(latlngs, { color: 'blue', weight: 4 }).addTo(map);
    if (latlngs.length > 0) map.setView(latlngs[0], 16);
  })
  .catch(err => console.error("/track 불러오기 실패:", err));


// 주행 시작 버튼 이벤트

const startBtn = document.getElementById("start-btn");
startBtn.addEventListener("click", () => {
  if (intervalId) return; // 이미 실행 중이면 무시

  intervalId = setInterval(() => {
    fetch("http://localhost:8000/next-location")
      .then(res => res.json())
      .then(data => {
        const cur = data.current;
        const cmp = data.comparison;

        if (!cur || !cur.latitude || !cur.longitude) return;

        // 타임스탬프 되돌림 감지 → 리셋
        if (prevTimestamp && cur.timestamp < prevTimestamp) {
          console.log("타임스탬프 되돌림 감지 → polyline 리셋");
          path = [];
          if (polyline) {
            map.removeLayer(polyline);
            polyline = null;
          }
        }
        prevTimestamp = cur.timestamp;

        const latlng = [cur.latitude, cur.longitude];
        path.push(latlng);

        // polyline 다시 그리기
        if (polyline) {
          polyline.setLatLngs(path);
        } else {
          polyline = L.polyline(path, { color: 'green', weight: 5 }).addTo(map);
        }

        // 마커 이동
        if (marker) {
          marker.setLatLng(latlng);
        } else {
          marker = L.marker(latlng).addTo(map);
        }

        // FAIL 지점 시각화 (비교 결과 활용)
        if (cmp && (!cmp.position_ok || !cmp.speed_ok || !cmp.course_ok)) {
          L.circleMarker(latlng, {
            radius: 6,
            color: "red",
            fillColor: "#f03",
            fillOpacity: 0.5
          }).addTo(map).bindPopup("FAIL");
        }

        // 자동 따라가기
        map.panTo(latlng);
      })
      .catch(err => {
        console.error("/next-location 통신 에러:", err);
      });
  }, 1000);
});
