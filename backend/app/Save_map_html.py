import folium
import datetime
import os


def make_cycle_folium(track_data, failures, path, Cycle_count, name):
    track_list = []
    for i in range(len(track_data)):
        track_list.append((track_data[i]["latitude"], track_data[i]["longitude"]))
    fail_list = []
    fail_message_list = []
    for i in range(len(failures)):
        if failures[i]["latitude"] != None and failures[i]["longitude"] != None:
            fail_list.append((failures[i]["latitude"], failures[i]["longitude"]))
            fail_message_list.append(failuers[i]["reason"])
        path_list = []
    for i in range(len(path)):
        if path[i]["latitude"] != None and path[i]["longitude"] != None:
            path_list.append((path[i]["latitude"], path[i]["longitude"]))

    m = folium.Map(location=track_list[0], zoom_start=12)
    folium.Polyline(track_list, color='blue', weight=20, opacity=0.7, tooltip=f"track", ).add_to(m)
    time = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    if len(path_list) != 0:
        folium.PolyLine(path_list, color='green', weight=20, opacity=0.7, tooltip=f"track", ).add_to(m)
    for i in range(len(fail_list)):
        point = fail_list[i]
        message = fail_message_list[i]
        folium.Marker(point, popup=message, icon=folium.Icon(color="red")).add_to(m)
    if not os.path.exists(".\\track_comparsion"):
        os.makedirs(".\\track_comparsion")
    m.save(f'.\\track_comparison\\track_{name}_{Cycle_count}_{time}.html')
    return f'.\\track_comparison\\track_{name}_{Cycle_count}_{time}.html'


