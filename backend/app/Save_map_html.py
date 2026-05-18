from datetime import datetime
from pathlib import Path

import folium


def make_cycle_folium(track_data, failures, path, cycle_count, name):
    track_list = [
        (item["latitude"], item["longitude"])
        for item in track_data
        if item.get("latitude") is not None and item.get("longitude") is not None
    ]
    path_list = [
        (item["latitude"], item["longitude"])
        for item in path
        if item.get("latitude") is not None and item.get("longitude") is not None
    ]
    fail_items = [
        item
        for item in failures
        if item.get("latitude") is not None and item.get("longitude") is not None
    ]

    center = path_list[0] if path_list else track_list[0] if track_list else (37.5, 127.0)
    m = folium.Map(location=center, zoom_start=12)

    if track_list:
        folium.PolyLine(track_list, color="blue", weight=8, opacity=0.7, tooltip="reference track").add_to(m)
    if path_list:
        folium.PolyLine(path_list, color="green", weight=8, opacity=0.7, tooltip="driving path").add_to(m)
    for item in fail_items:
        folium.Marker(
            (item["latitude"], item["longitude"]),
            popup=item.get("reason", "-"),
            icon=folium.Icon(color="red"),
        ).add_to(m)

    output_dir = Path("track_comparison")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    output_path = output_dir / f"track_{name}_{cycle_count}_{timestamp}.html"
    m.save(output_path)
    return str(output_path)
