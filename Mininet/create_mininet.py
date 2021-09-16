# from mininet_1 import TCPTraffic
import random
import requests
import json
import threading
import time
import random as rd
import os
import pickle
# import networkx as nx
# import matplotlib.pyplot as plt
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel
from mininet.cli import CLI
from mininet.node import RemoteController, OVSSwitch

lock = threading.Lock()

class CreateMininet(Topo):

    def __init__(self, switch, host):
        Topo.__init__(self)
        # switches = []

        #Create Switches
        for i in switch: 
            switches.append(self.addSwitch(i))
        print(switches, end="\n\n")

        #Add link switch
        for i, s in enumerate(switch):
            for j in range(len(switch)-i):
                if switch[s][i:][j] == 1:
                    print(s, switch[s][i:])
                    print(switches[j+i], switches[i])
                    self.addLink(switches[j+i], switches[i])
            print()
        
        # Create Hosts and add link
        for i in host:
            hosts.append(i)
            self.addLink(self.addHost(i), switches[switches.index(host[i])])
        # print("Create mininet ----", hosts)

class TrafficGenerator(threading.Thread):

    def __init__(self):
        super(TrafficGenerator, self).__init__()
        self.procs = []
        self.count = 1
        self.over = True

    def perform(self, one, two):
        pass

    def run(self):

        # global hosts
        sw = hosts[:]
        print("Traffic gen ---", sw)
        done = []
        while(True):

            rd.shuffle(sw)
            if((sw[0], sw[1]) not in done):
                # print("Traffic gen-------------")
                self.perform(sw[0], sw[1])
                time.sleep(0.1)
                # print("Traffic gen-------------", end="\n\n")
                #done.append((sw[0], sw[1]))
            if(len(done) == (len(sw)*(len(sw) - 1))):
                self.over = False

class PingTraffic(TrafficGenerator):

    def __init__(self):
        super(PingTraffic, self).__init__()

    def perform(self, one, two):
        global net, lock
        
        # print "Pinging#%d %s to %s" % (self.count, one, two)
        # cmd = "sudo ITGSend -a %s -E 1000 -T ICMP -z 1000"% ('10.0.0.'+two[1:])
        cmd = "ping 10.0.0.8 -w 1 "
        lock.acquire()
        net.get(one).cmd(cmd)
        lock.release()
        self.count += 1
        print("Ping ", one, two, self.count)

class TCPTraffic(TrafficGenerator):

    def __init__(self):
        super(TCPTraffic, self).__init__()

    def perform(self, one, two):
        global net, lock

        # print "Iperf TCP#%d %s to %s" % (self.count, one, two)
        # cmd = "iperf -c %s -y C -p %d -n 1000 &" % ('10.0.0.'+two[1:], 5000+int(str(two)[1:]))
        cmd = "iperf -c 10.0.0.1 -y C -p 5050 -n 1000"
        lock.acquire()
        net.get(one).cmd(cmd)
        lock.release()
        self.count += 1
        print("TCP ", one, two, self.count)
        #time.sleep(0.1)

class DataLog(threading.Thread):

    # Constructor
    def __init__(self, path):
        super(DataLog, self).__init__()
        self.path = path

    def run(self):
        global net
        start = time.time()
        print("Data log-----", self.path)
        while(True):
            for s in switches:
                print("Datalog------", s)
                data = net.get(s).cmd('ovs-ofctl dump-flows -O OpenFlow13 %s' % (s))
                print(data)
                with open('%s/%s.txt' % (self.path, s), 'a') as f:
                    f.write("Time : "+str(time.time() - start) + "\n")
                    f.write("Data : "+data+'\n')
            time.sleep(5)

def RandomTopo():
    """Random logical topology"""
    amountSwitch = 5
    amountHost = 6
    maxLink = 3
    listSw = [random.randint(1, maxLink) for i in range(amountSwitch)]
    listHs = [random.randint(1, amountSwitch) for i in range(amountHost)]
    dicSw = dict()
    dicHs = dict()
    for i in range(amountSwitch):
        nameSw = "s"+str(i+1)
        listCon = [0 for item in range(amountSwitch)]
        listNameSw = [sw for sw in range(amountSwitch)]
        listNameSw.pop(i)
        for sw in range(listSw[i]):
            connect = random.randint(0, len(listNameSw)-1)
            connect = listNameSw.pop(connect)
            listCon[connect] = 1
        dicSw.update({nameSw: listCon})
    for i in range(amountHost):
        dicHs.update({'h'+str(i+1): 's'+str(listHs[i])})
    sumdict = dict()
    sumdict.update({'switch': dicSw})
    sumdict.update({'host': dicHs})
    return sumdict


def run():
    global net, host_path
    # topo_logic = {
    #     "switch":{
    #         "s1": [ 0, 1],
    #         "s2": [ 1, 0]
  
    #     },
    #     "host": { 
    #         "h1": 's1', #server
    #         "h2": 's1', 
    #         "h3": 's1', 
    #         "h4": 's1', 
    #         "h5": 's2', #server
    #         "h6": 's2',
    #         "h7": 's2',
    #         "h8": 's2'
    #     },
    #     "test": "Topology"
    # }
    topo_logic = RandomTopo()

    #------- Send topology to web--------------------------------------------------
    url = "http://127.0.0.1:7777/topology"
    payload = json.dumps(topo_logic)
    print(type(payload))
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request("PUT", url, headers=headers, data=payload)
    print(response.text)

    topo = CreateMininet(topo_logic["switch"], topo_logic["host"])

    net = Mininet(topo, autoSetMacs=True, controller=lambda name: RemoteController(name, ip='127.0.0.1'), switch=OVSSwitch)
    
    net.start()
    print("---------------Dumping host connections")
    dumpNodeConnections(net.hosts)
    print("---------------Testing network connectivity")

    # path = os.path.dirname(host_path)
    
    
    # net.get("h1").cmd("iperf -s -D -p 5050")
    # net.get("h5").cmd("iperf -s -D -p 5060")
        
    # flow_thread_log = DataLog(path)
    # tcp = TCPTraffic()
    # ping = PingTraffic()

    # tcp.daemon = True
    # ping.daemon = True

    # tcp.start()
    # ping.start()
    # flow_thread_log.start()

    # t = 0
    # time_out = 25
    # while t < time_out and (tcp.over or ping.over):
    #     print(t)
    #     time.sleep(0.1)
    #     t+= 0.1
    # print(t)
    # if t<time_out:
    #     print("Operations completed before 20 seconds, terminating")
    # else:
    #     print("Terminating the traffic after 20 seconds")


    CLI(net)
    net.stop()
        
if __name__ == '__main__':
    hosts = []
    switches = []
    host_path = '/home/user01/mininet/topo_py/traffic_log/'
    print(host_path)
    setLogLevel('info')
    run()


