import requests
import json
import time
controllerIP = "103.253.73.175"
controllerPort = "8080"

URL = "http://"+controllerIP+":"+controllerPort
api = "/stats/flow/1"

URL2 = URL+api
r = requests.get(url = URL2)
data = r.json()
datapath = 1
print(data)
for datapath in range(1,len(data)+1):
    l = data.get(str(datapath))
    for stat in l:
        print("---flow on port %s" %stat.get("port_no"))
        print("packet_count: %s" %stat.get("packet_count"))
        print("byte_count: %s" %stat.get("byte_count"))
        print("actions: %s" %stat.get("actions"))
