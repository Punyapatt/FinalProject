import requests
import json
import time
controllerIP = ""
controllerPort = "8080"

URL = "http://"+controllerIP+":"+controllerPort
api = "/stats/queue/1"

URL2 = URL+api
r = requests.get(url = URL2)
data = r.json()
datapath = 1
print(data)
for datapath in range(1,len(data)+1):
    l = data.get(str(datapath))
    for stat in l:
        print("---queue on port %s" %stat.get("port_no"))
        print("duration_sec: %s" %stat.get("duration_sec"))
        print("duration_nsec: %s" %stat.get("duration_nsec"))

#3y>U7s'a'vK/{R3\