import requests
import json
import time
controllerIP = ""
controllerPort = "8080"

URL = "http://"+controllerIP+":"+controllerPort
api = "/stats/port/1"

URL2 = URL+api
r = requests.get(url = URL2)
data = r.json()
datapath = 1

for datapath in range(1,len(data)+1):
    l = data.get(str(datapath))
    for stat in l:
        print("---on port %s" %stat.get("port_no"))
        print("recive packet: %s" %stat.get("rx_bytes"))
        print("transmit packet: %s" %stat.get("tx_bytes"))

#3y>U7s'a'vK/{R3\