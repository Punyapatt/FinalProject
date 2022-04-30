from mininet.topo import Topo
from mininet.node import OVSKernelSwitch
from mininet.link import TCLink
import requests
import json

class Topology(Topo):
    def __init__(self):
        Topo.__init__(self)
        # switches = []

        topo_logic = {
            "test": "Topology",
            "switch":{
                "s1": [ 1, 1, 1, 0, 0, 0],
                "s2": [ 1, 1, 0, 1, 0, 0],
                "s3": [ 1, 0, 1, 0, 1, 1],
                "s4": [ 0, 1, 0, 1, 1, 0],
                "s5": [ 0, 0, 1, 1, 1, 1],
                "s6": [ 0, 0, 1, 0, 1, 1]
    
            },
            "host": { 
                "h1": 's1', 
                "h2": 's1', 
                "h3": 's5', 
                "h4": 's5'
            },
            "bandwidth": {
                "switch": {
                    "s1": [0, 17, 20, 0, 0, 0],
                    "s2": [17, 0, 0, 17, 0, 0],
                    "s3": [20, 0, 0, 0, 20, 5],
                    "s4": [0, 17, 0, 0, 17, 0],
                    "s5": [0, 0, 20, 17, 0, 5],
                    "s6": [0, 0, 5, 0, 5, 0]
                },
                "host": {"h1": 100, "h2": 100, "h3": 100, "h4":100},
            }
        }
        
        # topo_logic = {
        #     "test": "Topology",
        #     "switch":{
        #         "s1": [1, 0, 1, 0, 0, 0, 1, 0, 0, 0],
        #         "s2": [0, 1, 0, 1, 0, 0, 0, 1, 0, 0],
        #         "s3": [1, 0, 1, 0, 1, 1, 0, 0, 0, 0],
        #         "s4": [0, 1, 0, 1, 1, 1, 0, 0, 0, 0],
        #         "s5": [0, 0, 1, 1, 1, 0, 0, 0, 0, 0],
        #         "s6": [0, 0, 1, 1, 0, 1, 0, 0, 0, 0],
        #         "s7": [1, 0, 0, 0, 0, 0, 1, 0, 1, 1],
        #         "s8": [0, 1, 0, 0, 0, 0, 0, 1, 1, 1],
        #         "s9": [0, 0, 0, 0, 0, 0, 1, 1, 1, 0],
        #         "s10": [0, 0, 0, 0, 0, 0, 1, 1, 0, 1]
    
        #     },
        #     "host": { 
        #         "h1": "s5",
        #         "h2": "s5",
        #         "h3": "s6",
        #         "h4": "s6",
        #         "h5": "s9",
        #         "h6": "s9",
        #         "h7": "s10",
        #         "h8": "s10"
        #     },
        #     "bandwidth": {
        #         "switch": {
        #             "s1": [0, 0, 30, 0, 0, 0, 30, 0, 0, 0],
        #             "s2": [0, 0, 0, 30, 0, 0, 0, 30, 0, 0],
        #             "s3": [30, 0, 0, 0, 18, 18, 0, 0, 0, 0],
        #             "s4": [0, 30, 0, 0, 20, 20, 0, 0, 0, 0],
        #             "s5": [0, 0, 18, 20, 0, 0, 0, 0, 0, 0],
        #             "s6": [0, 0, 18, 20, 0, 0, 0, 0, 0, 0],
        #             "s7": [30, 0, 0, 0, 0, 0, 0, 0, 18, 18],
        #             "s8": [0, 30, 0, 0, 0, 0, 0, 0, 18, 18],
        #             "s9": [0, 0, 0, 0, 0, 0, 18, 20, 0 ,0],
        #             "s10": [0, 0, 0, 0, 0, 0, 18, 20, 0, 0]
        #         },
        #         "host": {"h1": 100, "h2": 100, "h3": 100, "h4":100, "h5": 100, "h6": 100, "h7": 100, "h8": 100}
        #     }
        # }
        
        # topo_logic = {
        #     "test": "Topology",
        #     "switch":{
        #         "s1": [ 1, 1],
        #         "s2": [ 1, 1] 
        #     },
        #     "host": { 
        #         "h1": 's1', 
        #         "h2": 's2' 
        #     },
        #     "bandwidth": {
        #         "switch": {
        #             "s1": [0, 10],
        #             "s2": [10, 0]                
        #         },
        #         "host": {"h1": 100, "h2": 100},
        #     }
        # }
        #------- Send topology to web--------------------------------------------------
        url = "http://127.0.0.1:7777/topology"
        payload = json.dumps(topo_logic)
        print(type(payload))
        headers = {
            'Content-Type': 'application/json'
        }
        response = requests.request("PUT", url, headers=headers, data=payload)
        print(response.text)
        #----------------------------------------------------------------------------------------------------------------------------
        
        
        switch, host, bandwidth = topo_logic["switch"], topo_logic["host"], topo_logic["bandwidth"]
        switches = []
        hosts = []
        #Create Switches
        bw_sw = bandwidth["switch"]
        bw_host = bandwidth["host"]
        
        for i in switch: 
            switches.append(self.addSwitch(i, cls=OVSKernelSwitch))
        print(switches, end="\n\n")

        #Add link switch
        for i, s in enumerate(switch):
            for j in range((len(switch)-1)-i):
                if switch[s][i+1:][j] == 1:
                    bw = bw_sw[s][i+1:][j]
                    print(s, switch[s][i+1:], j, "bw :", bw)
                    print(switches[j+i+1], switches[i])
                    
                    linkopts = {'bw':bw, 'use_htb':True, 'delay':'5ms', 'max_queue_size':1000, 'cls':TCLink}
                    self.addLink(switches[j+i+1], switches[i], **linkopts)
            print()
        
        # Create Hosts and add link
        for i in host:
            hosts.append(i)
            bw = bw_host[i]
            linkopts = {'bw':bw, 'use_htb':True, 'delay':'5ms'}
            self.addLink(self.addHost(i, cpu=.2), switches[switches.index(host[i])], **linkopts)
    
topos = {'custom_topology': (lambda: Topology())}
    