const map = L.map('map').setView([37.5,127],13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,}).addTo(map);


let path = [];
let marker = null;
let polyline = null;
let intervarlId = null;
let pastcycle = 0;
let failMarkers = [];
let currentLoopFlag = true;


fetch("http://localhost:8000/track")
  .then(res => res.json())
  .then(track => {
    const latlngs = track.map(p => [p.latitude, p.longitude]);
    L.polyline(latlngs, {color: "blue", weight:15 }.addTo(map));
    if (latlngs.length > 0) map.setView(latlngs[0],13);
  });
  
  
  
function currentLoop(onoff){
  if (!onoff){
    console.warn("current off")
    return;
  }
  fetch("http://localhost:8000/current")
    .then(res => res.json())
    .then(data => {
      if (!data.current?.latitude || !data.current?.longitude){
        console.warn("위치 없음: 빈 응답");
        return;
      }
      
      if (data.cycle != pastcycle){
        pastcycle = data.cycle;
        console.log("바퀴수 변동 감지 => polyline 리셋");
        path = [];
        if (polyline) {
        map.removeLayer(polyline);
        polyline = null;
        }
      }
      
      const latlng = [dsta.current.latitude, data.current.longitude];
      path = data.path;
      
      if (!data.path || !Array.isArray(data.path) || data.path.length ===0 ){
        console.warn("path가 비어있거나 없음");
      } else{
        const polyPath = path.map(p => [p.latitude,p.longitude]);
        console.log(polyPath[polyPath.length - 1]);
        if(!polyline){
          polyline =L.polyline(polyPath,{color:'green',weight:15}).addTo(map);
        } else{
          polyline.setLatLngs(polyPath);
        }
      }
      
      if(marker){
        marker.setLatLngs(latlng);
      } else{
        caricon = L.icon({
          inconUrl:"/static/image/car-icon.png",
          iconSize:[28,28],
          iconAnchor:[14,28]
        });
        marker = L.marker(latlng,{icon.caricon}).addTo(map);
        console.log("마커 생성");
      }
      
      map.setView(latlng,map.getZoom());
      
      document.getElementById("info-time").textContent = data.current.timestamp
      document.getElementById("into-lat").textContent = data.current.latitude.toFixed(6);
      document.getElementById("into-lon").textContent = data.current.longitude.toFixed(6);
      document.getElementById("into-speed").textContent = data.current.spd_over_grnd + " km/h";
      document.getElementById("into-heading").textContent = data.current.true_course + "°";
      
      const resultElem = document.getElementById("info-result");
      const reasonElem = document.getElementById("info-reason");
      
      if (data.comparison.pass ===true){
        resultElem.textContent = "PASS";
        resultElem.className ="pass";
        reasonElem.textContent = "일치";
      } else {
        resultElem.textContent = "FAIL";
        resultElem.className ="fail";
        reasonElem.textContent = data.comparison.reason;
      }
      
      failures = data.fail;
      failMarkers.forEach(m => map.removeLayer(m));
      failMarkes =[];
      const failIcon = L.icon({
        iconUrl:'https://raw.githubusercontent.com//pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
        iconSize: [25,41];
        iconAnchor:[12, 41],
        popupAnchor:[1,-34],
        shadowUrl: 'https://unpkg.com/leaflet@1.9.3/dist/images/marker-shadow.png',
        shadowSize: [41, 41],
        shadowAnchor:[12,41]        
      });
      
      
      failures.forEach(f => {
        if (!f.latitude || !f.longitude) return;
        const latlng = [f.latitude,f.longitude];
        const failMarker = L.marker(latlng, {
          icon: failIcon
        }).addTo(map);
        
        const failReason = f.reason || "이유 정의되지 않음";
        const popupHtml = '
          <div style="font-size:13px;">
            <strong style="color:red;">● FAIL</strong><br>
            <strong>위도 :</strong> ${f.latitude}<br>
            <strong>경도 :</strong> ${f.longitude}<br>
            <strong>속도 :</strong> ${f.spd_over_grnd || "-"}<br>
            <strong>헤딩 :</strong> ${f.true_course || "-"}<br>
            <strong>이유 :</strong> ${f.reason || "-"}<br>
          </div>
        ';
        failMarker.bindPopup(popupHtml);
        failMarkers.push(failMarker);
      }); 
      
    })

}

function currentLoopOnOff(flag){
  if(flag){
  currentLoopFlag = true;
  }else{
  currentLoopFlag = fale;
  }
}


setInterval(() => {currentLoop(currentLoopFlag);},1000);

document.getElementById("save-btn").addEventListener("click",() => {
  console.log("[리포트 저장] 시도중...");
  fatch("http://localhost:8000/generate-excel")
  .then(res => {
    console.log("응답 상태 코드:",res.status);
    if (!res.ok) throw new Error("다운로드 실패 - 상태코드 " + res.status);
    return res.blob();
  })
  .then(blob => {
    if (blob.size ===0) throw new Error("응답은 왔지만 파일이 비어있음(0바이트)");
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = 'report_${new Date().toISOString().slice(0,19)}.csv';
    documnet.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
    console.log("리포트 다운로드 완료");
  })
  .catch(arr => {
    console.error("리포트 다운로드 실패:", err);
    alert("리포트 다운로드 실패: " + err.message);
  });
});


function start_Backend(){
  fetch("http://localhost:8000/start-driving",{method:"POST"})
  .then(res => res.json())
  .then(data => console.log(data.message));
}


function stop_Backend(){
  fetch("http://localhost:8000/stop-driving",{method:"POST"})
  .then(res => res.json())
  .then(data => console.log(data.message));
}