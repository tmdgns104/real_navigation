let path = [];
let polyline = null;
let prevTimestamp = null;  // 이전 타임스탬프



window.print = () => {
  console.warn("window.print() 호출이 차단되었습니다.");
};

const map = L.map('map').setView([37.5, 127], 13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
}).addTo(map);

// 전역 변수
let path = [];
let marker = null;
let polyline = null;
let intervalId = null;

// 트랙 표시
fetch("http://localhost:8000/track")
  .then(res => res.json())
  .then(track => {
    const latlngs = track.map(p => [p.latitude, p.longitude]);
    L.polyline(latlngs, { color: 'blue', weight: 4 }).addTo(map);
    if (latlngs.length > 0) map.setView(latlngs[0], 16);
  });

// 주행 시작 버튼 이벤트
document.getElementById("start-btn").addEventListener("click", () => {
  if (intervalId) return; // 이미 실행 중이면 무시

  intervalId = setInterval(() => {
      fetch("http://localhost:8000/next-location")
        .then(data => {
          const cur = data.Current;
          if (!cur.latitude || !cur.longitude) return;

          // ✅ 타임스탬프 기준으로 과거로 되돌아가면 리셋
          if (prevTimestamp && cur.timestamp < prevTimestamp) {
            console.log("타임스탬프 되돌림 감지 → polyline 리셋");
            path = [];
            if (polyline) {
              map.removeLayer(polyline);  // 지도에서 기존 선 제거
              polyline = null;
            }
          }

          prevTimestamp = cur.timestamp;

          const latlng = [cur.latitude, cur.longitude];
          path.push(latlng);

          // ✅ polyline 다시 그리기
          if (polyline) {
            polyline.setLatLngs(path);
          } else {
            polyline = L.polyline(path, { color: 'green', weight: 5 }).addTo(map);
          }

          // ✅ 마커 이동
          if (marker) {
            marker.setLatLng(latlng);
          } else {
            marker = L.marker(latlng).addTo(map);
          }

          // 자동 따라가기
          map.panTo(latlng);
        });

        .catch(err => {
          console.error("통신 에러:", err);
        });
  }, 1000);


});
