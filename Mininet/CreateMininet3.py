from mininet.topo import Topo
from mininet.net import Mininet
from mininet.log import setLogLevel
from mininet.cli import CLI
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.link import TCLink
from time import sleep

class CreateMininet(Topo):

    def __init__(self, topo):
        Topo.__init__(self)
        switches = []
        switch =  list(topo['switch'].keys())
        host = list(topo['host'].keys())
        switch.sort(key=lambda x: int(x[1:]))
        host.sort(key=lambda x: int(x[1:]))
        
        #Create Switches
        for i in range(len(switch)):
            dp = self.tobase16(i+1)
            switches.append(self.addSwitch(switch[i], cls=OVSKernelSwitch, dpid=str(dp), protocols=["OpenFlow13"]))
        print(switch, host)

        #Add link switch

        for i, s in enumerate(switch):
            for j in range(i, len(switch)):
                if (topo['switch'][s][j] == 1):
                    #print(j, switch[j], switch)
                    #print(s, topo['switch'][s][i])
                    #print(switch[i], switch[j])
                    for port in range(len(topo['link'][s])):
                        if (switch[j] == topo['link'][s][port]):
                            port1 = port+1
                            #print(port1)
                            break
                    #print(topo['link'][switch[j]])
                    for port in range(len(topo['link'][switch[j]])):
                        if (switch[i] == topo['link'][switch[j]][port]):
                            port2 = port+1
                            break
                    print(switches[i], switches[j], port1, port2)
                    self.addLink(switches[i], switches[j], port1, port2, cls=TCLink, bw=10)
            #print()

        # Create Hosts and add link
        machost = ["00:00:00:00:00:"+ str("0"+str(h+1) if h < 10 else h) for h in range(len(host))]
        hosts = [self.addHost(host[h], mac=machost[h]) for h in range(len(host))]
        #hosts = [self.addHost(host[h]) for h in range(len(host))]
        for i in range(len(host)):
            con = topo["host"][host[i]]
            #print(con)
            for j in range(len(topo['link'][con])):
                if (host[i] == topo['link'][con][j]):
                    port2 = j+1
                    break
            for l in range(len(switch)):
                if (switch[l] == con):
                    index = l
                    break
            #print(hosts[i], switches[index], 1, port2)
            self.addLink(hosts[i], switches[index], 1, port2)
    def tobase16(self, num):
        listnum = []
        bit16 = ['0','1','2','3','4','5','6','7','8','9','a','b','c','d','e','f']
        while True:
            numtemp = num//16
            if (num//16 == 0):
                listnum.append(num)
                break
            else:
                listnum.append(numtemp)
                num = num%16
        tobase = [bit16[num] for num in listnum]
        tobasestr = "".join(tobase)
        return tobasestr

topo_logic = {'switch': {'s1': [0, 1, 0], 's2': [1, 0, 1], 's3': [0, 1, 0]}, 'host': {'h1': 's1', 'h2': 's3', 'h3': 's3', 'h4': 's3', 'h5': 's1'}, 'link': {'s1': ['s2', 'h1', 'h5'], 's2': ['s1', 's3'], 's3': ['s2', 'h2', 'h3', 'h4']}, 'ip': {'h1': '10.8.47.165', 'h2': '10.76.91.229', 'h3': '10.237.79.212', 'h4': '10.137.111.183', 'h5': '10.214.27.122'}}
topo_logic = {'switch': {'s1': [0, 1, 1, 0, 0, 0, 0, 1, 0, 0], 's2': [1, 0, 0, 0, 1, 0, 0, 0, 1, 0], 's3': [1, 0, 0, 0, 0, 0, 0, 0, 0, 1], 's4': [0, 0, 0, 0, 0, 0, 0, 0, 0, 1], 's5': [0, 1, 0, 0, 0, 0, 0, 0, 0, 0], 's6': [0, 0, 0, 0, 0, 0, 0, 0, 0, 1], 's7': [0, 0, 0, 0, 0, 0, 0, 0, 0, 1], 's8': [1, 0, 0, 0, 0, 0, 0, 0, 0, 0], 's9': [0, 1, 0, 0, 0, 0, 0, 0, 0, 0], 's10': [0, 0, 1, 1, 0, 1, 1, 0, 0, 0]}, 'host': {'h1': 's6', 'h2': 's6', 'h3': 's3', 'h4': 's2', 'h5': 's3'}, 'link': {'s1': ['s2', 's3', 's8'], 's2': ['s1', 's5', 's9', 'h4'], 's3': ['s1', 's10', 'h3', 'h5'], 's4': ['s10'], 's5': ['s2'], 's6': ['s10', 'h1', 'h2'], 's7': ['s10'], 's8': ['s1'], 's9': ['s2'], 's10': ['s3', 's4', 's6', 's7']}, 'ip': {'h1': '10.173.98.64', 'h2': '10.113.64.247', 'h3': '10.163.56.30', 'h4': '10.81.100.20', 'h5': '10.196.39.73'}}
topo_logic = {'switch': {'s1': [0, 1, 0, 0], 's2': [1, 0, 0, 1], 's3': [0, 0, 0, 0], 's4': [0, 1, 0, 0]}, 'host': {'h1': 's1', 'h2': 's4'}, 'link': {'s1': ['s2', 's3', 'h1'], 's2': ['s1', 's4'], 's3': ['s1', 's4'], 's4': ['s2', 's3', 'h2']}, 'ip': {'h1': '10.4.119.180', 'h2': '10.144.31.18'}}
topo = CreateMininet(topo_logic)
net = Mininet(topo=topo,  build=False)
c0 = RemoteController('c0', ip='127.0.0.1', port=6653)
c1 = RemoteController('c1', ip='127.0.0.1', port=6654)
net.addController(c0)
net.addController(c1)
net.build()
net.start()
CLI(net)
net.stop()
