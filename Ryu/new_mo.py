from multiprocessing.dummy import Pool as ThreadPool
import requests
import json
import time
import networkx as nx
from networkx.readwrite import json_graph
from networkx.algorithms.shortest_paths.weighted import single_source_dijkstra
import matplotlib.pyplot as plt

def coninformation():
    controller = "10.50.34.27"
    port = "8080"
    return controller, port
def func(datapath):
    controller,port = coninformation()
    #print("Switch %d : %d"% (self.swID, self.count))
    url_flow = "http://"+controller+":"+port+"/stats/flow/"+str(datapath)
    url_port = "http://"+controller+":"+port+"/stats/port/"+str(datapath)
    # url_queue = "http://10.50.34.27:8080/stats/queue/"+str(swID)
    res_flow = requests.get(url_flow)
    res_port = requests.get(url_port)
    # res_queue = requests.get(url_queue)

    flow_data = res_flow.json()
    port_data = res_port.json()
    # print(json.dumps(data, indent=4, sort_keys=True))
    #check = {}

    l = port_data.get(str(datapath))
    portClean = []
    flowClean = []
    for stat in l:
        num_port = stat.get("port_no")
        if num_port != "LOCAL":
            portClean.append({"port_no": stat.get("port_no"), "rx_bytes": stat.get("rx_bytes"), "tx_bytes": stat.get("tx_bytes")})
            continue
        else:
            portClean.append({"port_no": stat.get("port_no"), "rx_bytes": stat.get("rx_bytes"), "tx_bytes": stat.get("tx_bytes")})

    for stat in flow_data.get(str(datapath)):

        tempdict = dict()
        matchid = stat.get("match")

        tempdict.update({'matchid': matchid, "packet_count": stat.get("packet_count"), "byte_count": stat.get("byte_count"), "actions": stat.get("actions")})
        flowClean.append(tempdict)

    datapath = str(datapath)
    return {"flowstat": flowClean, "portstat": portClean}

def worker(index):
    index = str(index)
    return {index : func(index)}

def run_multi():
    controller,port = coninformation()
    num_thread = 10
    maxbw = 10
    flowID = list()
    log_portstat = list()
    log_flowstat = list()
    url = "http://"+controller+":"+port+"/stats/switches"
    res = requests.get(url)

    switch = res.json()
    rounds = 20
    count = 0
    #set up
    threads = ThreadPool(num_thread)
    result = threads.map(worker, switch)
    portstat_before, flowstat_before = cleandata(result)
    threads.close()
    threads.join()
    time.sleep(5)

    while count < rounds:
        threads = ThreadPool(num_thread)
        result = threads.map(worker, switch)
        #print(result)
        portstat_after, flowstat_after = cleandata(result)
        #print(checkcongest(calbanwidth(portstat_before, portstat_after), flowstat_after))
        checkcongest(calbanwidth(portstat_before, portstat_after), flowstat_after)
        #print(calbanwidth(portstat_before, portstat_after))
        #print(flowstat_after)
        log_flowstat.append(calflowstat(flowstat_before, flowstat_after))
        log_portstat.append(calbanwidth(portstat_before, portstat_after))
        #print(calbanwidth(portstat_before, portstat_after))
        portstat_before, flowstat_before = portstat_after, flowstat_after
        threads.close()
        threads.join()
        time.sleep(5)
        count+=1
    #print(portstat_after, flowstat_after, sep="\n")
    print(log_portstat)
    #print(log_flowstat)
def cleandata(allstat):
    sumportstat = dict()
    sumflowstat = dict()
    for dpid in allstat:
        dpsw = list(dpid.keys())[0]
        stat = dpid.get(dpsw).get('portstat')
        portstattemp = dict()
        for portstat in stat:
            port = portstat.get('port_no')
            portstattemp.update({port:{'rx_bytes': portstat.get('rx_bytes'), 'tx_bytes': portstat.get('tx_bytes')}})
            #print(portstattemp)
        sumportstat.update({dpsw: portstattemp})
    for dpid in allstat:
        dpsw = list(dpid.keys())[0]
        stat = dpid.get(dpsw).get('flowstat')
        sumflowstat.update({dpsw: stat})
    return sumportstat, sumflowstat

def calbanwidth(old, new):
    bandwidth = dict()
    for dpid in old.keys():
        oldportstat = old.get(dpid)
        newportstat = new.get(dpid)
        tempdict = dict()
        for port in oldportstat.keys():
            #bw = (newportstat.get(port).get('rx_bytes') + newportstat.get(port).get('tx_bytes')) - (oldportstat.get(port).get('rx_bytes') + oldportstat.get(port).get('tx_bytes'))
            bw = newportstat.get(port).get('tx_bytes') - oldportstat.get(port).get('tx_bytes')
            tempdict.update({port: bw})
        bandwidth.update({dpid: tempdict})
    return bandwidth

def calflowstat(old, new):
    flowstat = dict()
    flowtable = list()
    for dpid in old.keys():
        oldflowstat = old.get(dpid)
        newflowstat = new.get(dpid)
        tempdict = dict()
        for flowindex in range(len(oldflowstat)):
            flow = oldflowstat[flowindex].get('matchid')
            if flow not in flowtable:
                flowtable.append(flow)
            pc = (newflowstat[flowindex].get("packet_count") - oldflowstat[flowindex].get("packet_count"))
            bc = (newflowstat[flowindex].get("byte_count") - oldflowstat[flowindex].get("byte_count"))
            for flowentryindex in range(len(flowtable)):
                if flowtable[flowentryindex] == flow:
                    flowid = flowentryindex
                    break
            tempdict.update({flowid :{"packet_count": pc, "byte_count": bc}})
        flowstat.update({dpid: tempdict})
    return flowstat, flowtable

def congest_graph(graph, portstat):
    

def checkcongest(bwstat, flowstat):
    r = requests.get('http://10.50.34.27:7777/topology')
    sw_bw = r.json().get("bandwidth").get("switch")

    
    url = "http://10.50.34.27:7777/get_networkx"
    response = requests.get(url)
    data = response.json()
    #print(type(data))

    G = json_graph.node_link_graph(data)
    #print(list(G.edges(data=True)))
    graph = list(G.edges(data=True))
    portbw = list()
    for i in sw_bw.keys():
        portbw.append(sw_bw.get(i))
    congest = dict()
    #print(portbw)
    #bwstat = {'4': {'LOCAL': 0, 1: 0, 2: 0, 3: 0}, '3': {'LOCAL': 0, 2: 0}, '2': {'LOCAL': 0, 1: 0, 2: 0}, '1': {'LOCAL': 0, 1: 0, 3: 0}}

    for dpid in bwstat.keys():
        dpid_bw = bwstat.get(dpid)
        tempcon = list()
        for port in dpid_bw.keys():
            if port == 'LOCAL':
                continue
            bw = dpid_bw.get(port)

            if (float(bw)/5 >= (float(portbw[int(dpid)-1][port])*1000/8 * 70/100)):
                tempcon.append(port)
        if len(tempcon) > 0:
            congest.update({dpid: tempcon})
    congest_dpid = list(congest.keys())
    print("congest : " + str(congest))
    #print(congest.keys())
    count = 0
    list_congest = list()

    while count < len(congest_dpid):
        dpid = congest_dpid[count]
        congest_port = congest.get(dpid)
        dpid = int(dpid)
        listofcon = list()
        for port in congest_port:
            for con in range(len(portbw[dpid-1])):
                if portbw[dpid-1][con] == 0:
                    continue 
                elif G.get_edge_data(dpid, con+1).get("port") == port:
                    listofcon.append([dpid, con+1])
                    #print(congest[str(con+1)])
                    #print(G.get_edge_data(con+1, dpid).get("port"))
                    #print(con+1, dpid)
                    #print("list : " + str(congest[str(con+1)]))
                    #print("remove : " + str(G.get_edge_data(con+1, dpid).get("port")))
                    if  G.get_edge_data(con+1, dpid).get("port") in congest[str(con+1)]:
                        congest[str(con+1)].remove(G.get_edge_data(con+1, dpid).get("port"))
                    if len(congest[str(con+1)]) <= 0:
                        congest_dpid.remove(str(con+1))
                    break
        for i in listofcon:
            if len(i) > 0:
                list_congest.append(i)

        count += 1

    cleanlist = list()
    flow_congest = list()
    #print(flowstat)
    for twocon in list_congest:
        flowout = flowstat.get(str(twocon[0]))
        tempflow = list()
        for i in flowout:
            if str(i.get("actions")[0]) == "OUTPUT:"+str(G.get_edge_data(twocon[0], twocon[1]).get("port")):
                #ต้องหา flow ใหญ่ด้วย
                tempflow.append(i.get("matchid"))
        flowin = flowstat.get(str(twocon[1]))
        for i in flowin:
            if str(i.get("actions")[0]) == "OUTPUT:"+str(G.get_edge_data(twocon[1], twocon[0]).get("port")):
                #ต้องหา flow ใหญ่ด้วย
                tempflow.append(i.get("matchid"))
        flow_congest.append(tempflow)
    #{dpid: {port: {flow}}}

    #clean
    link_congest = list()
    for i in range(len(flow_congest)):
        for f in flow_congest[i]:
            if len(f) != 0:
                link_congest.append({"link_congestion": [tuple(list_congest[i])], "src_flow": f.get("matchid").get("dl_src"), "dst_flow": f.get("matchid").get("dl_dst"),  reroute:True})
                break
    print(link_congest)
    return link_congest

    #return congest
    #return  [{link_congestion, src_flow, dst_flow, reroute:True}, . . .]

run_multi()
