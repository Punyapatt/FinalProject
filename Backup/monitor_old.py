import json
from os import pread
from this import d
import requests
import time
from multiprocessing.dummy import Pool as ThreadPool
import pandas as pd
from networkx.readwrite import json_graph
import networkx as nx
import os
import csv

global interval
global original_path
global secondary_path
global congest_time
global congest_count 
global congest_interval
global congest_interval_list

original_path = dict()
secondary_path = dict()
congest_time = dict()
congest_count = 0
congest_interval = 0
congest_interval_list = []

flow_priority = {}
# {
#     dpid : {
#         key : [val, duration],
#         ...
#     }
# }

flow = {}
# ------- Structure of flow dict --------------
# {
#     dpid : {
#         key : {
#             byte: [val, before_val],
#             packet : [val, before_val]
#         }
#     }
# }

port = {}
# ------- Structure of port dict --------------
# {
#     dpid: {
#         port_n:{
#             tx_packets: [val, before_val],
#             tx_bytes: [val, before_val],
#             tx_errors: [val, before_val],
#             duration_sec: [val, before_val]
#         }
#     }
# }

port_before = {}


topo = requests.get("http://localhost:7777/topology")
topo = topo.json()
print('Monitor topo request')
src_switch = [int(topo['host'][i][1:]) for i in topo['host']]
host = ['00:00:00:00:00:'+str('%02d'%int(i[1:])) for i in topo['host']]
end2end = {}
# {
#     src: val,
#     ...
# }

def main_thread(G, period):
    all_switch = requests.get("http://10.50.34.27:8080/stats/switches")
    all_switch = all_switch.json()
    global interval
    global original_path
    global secondary_path
    interval = period
    graph_e = G
    # send_text({"kit graph":len(graph_e)})
    start_time = time.time()
    threads = ThreadPool(10)
    result = threads.map(worker, all_switch)
    end_thread_time = time.time()
    
    connectivity = find_end2end(graph_e)
    bandwitdth_matrix = find_maxbanwidth(topo)
    congestList = check_congest(port, connectivity, bandwitdth_matrix)

    flow_congest = find_flow_congest(congestList, connectivity)
    flow_congest = find_sort_flow(flow_congest, flow_priority)
    netgraph = graph_e.copy()
    update_w = update_graph_weight(port, bandwitdth_matrix, connectivity, netgraph)
    nx.set_edge_attributes(netgraph, update_w)
    netgraph = update_graph_avail(port, bandwitdth_matrix, connectivity, netgraph)
    link_congest = reformat_link_congest(flow_congest, flow, connectivity)
    
    pandas_portstat_write(port)
    pandas_n2n_write(flow)
    pandas_flowstat_write(flow)
    
    # print(port[5][2]['tx_bytes'])
    
    # send_text(secondary_path)
    # send_text(port)
    # send_text(original_path)
    # send_text(secondary_path)
    # send_text(flow)
    # send_text(flow_priority)
    send_stat(port)
    all_time = time.time()
    print('\n\n')
    print('---------------- Monitor ----------------')
    print('kit time :', end_thread_time - start_time)
    print('jame time:', all_time - end_thread_time)
    print('All time :', all_time - start_time)
    print('-----------------------------------------')
    print('\n\n')
    
    return netgraph, link_congest
def worker(dpid):
    # --------------------------------[ Flow ]-------------------------------------------
    dp = requests.post("http://localhost:8080/stats/flow/"+str(dpid), 
                       data = json.dumps({
                           "priority": 32768,
                           "table_id": 0
                       }))
    dp = dp.json()
    features = ['byte_count', 'packet_count', "duration_sec"]

    if dpid not in flow:
        flow[dpid] = {}
        flow_priority[dpid] = {}
    
    for i in dp[str(dpid)]: 
        if i['priority'] == 32768:
            # print('dpid[%d] %s -> %s'%(dpid, i['match']['dl_src'][2:], i['match']['dl_dst'][2:]))
            key = i['match']['dl_src'] + i['match']['dl_dst']
            
            if key not in flow[dpid]:
                flow[dpid][key] = {x:[0, 0] for x in features}
                flow_priority[dpid][key] = [0, 0]
            
            # Update current value   
            for j in features:
                before = flow[dpid][key][j][1]
                val = i[j] - before
                # if j == 'byte_count':
                #     src, dst = i['match']['dl_src'][2:], i['match']['dl_dst'][2:]
                #     print('[%d] %s -> %s = %d'%(dpid, src, dst, (val/interval)*8))
                flow[dpid][key][j] = [val, i[j]]
            
            # end to end traffic   
            if i['match']['dl_src'] in host and dpid in src_switch:
                e_src = i['match']['dl_src'][-2:]
                e_dst = i['match']['dl_dst'][-2:]
                end2end[e_src + '->' + e_dst] = (flow[dpid][key]['byte_count'][0]/interval)*8
                
            # get volume up to flow_priority w/o sort
            if flow[dpid][key]['byte_count'][0] != 0:
                # packet_size = (flow[dpid][key]['byte_count'][0])/(flow[dpid][key]['packet_count'][0]) # volume byte/packet (w/o devide interval)
                packet_size = flow[dpid][key]['byte_count'][0]
                time_con = flow_priority[dpid][key][1] + interval
                flow_priority[dpid][key] = [packet_size, time_con]
            else:
                flow_priority[dpid][key] = [0, 0]
    
    #---------------------------------[ Port ]-------------------------------------------
    port_req = requests.get("http://localhost:8080/stats/port/"+str(dpid))
    port_res = port_req.json()
    features = ["tx_packets", "tx_bytes", "duration_sec"]
    if dpid not in port:
        port[dpid] = {}
    
    for i in port_res[str(dpid)]:
        port_num = i["port_no"]
        if port_num == "LOCAL":
            continue
        if port_num not in port[dpid]:
            port[dpid][port_num] = {x:[0, 0] for x in features}
            
        for j in features:
            before = port[dpid][port_num][j][1]
            val = i[j] - before
            # if j == "tx_bytes":
            #     print('tx bytes dpid[%d] port %d : %d'%(dpid, port_num, ((val*8)/interval)))
            port[dpid][port_num][j] = [val, i[j]]
 
    return True
def find_maxbanwidth(all_switch):
    """
    sw_bw = {"s1":[0,10],"s2":[10,0]}
    link_matrix = [[0, 10],[10,0]]
    """

    sw_bw = all_switch.get("bandwidth").get("switch")
    link_matrix = [sw_bw.get(switch) for switch in sw_bw]
    return link_matrix
def check_congest(portstat, dpidcon, bandwitdth_matrix):
    """
    dpidcon {dpid : {port: endDpid},...}
    congest_list {dpid: [port]}
    bandwitdth_matrix: ][bw 0] [bw 0]]
    """
    global interval
    
    global congest_count 
    global congest_interval
    global congest_interval_list

    #FIND CONGESTION PORT
    congest_list = dict()
    for dpid in portstat:
        for port_no in portstat[dpid]:
            tx_bytes = portstat.get(dpid).get(port_no).get('tx_bytes')[0]
            if dpidcon.get(dpid).get(port_no) == None:
                continue
            nDpid = dpidcon[dpid][port_no]
            max_bandwidth = bandwitdth_matrix[dpid-1][nDpid-1]
            if max_bandwidth == 0:
                continue
            if ((tx_bytes/interval)*8 >= (max_bandwidth*2**20)*0.7):
                # send_text({'congest':[dpid, (tx_bytes/interval)*8, (max_bandwidth*2**20)*0.7]})
                if dpid not in congest_list.keys():
                    congest_list.update({dpid: [port_no]})
                else:
                    congest_list[dpid].append(port_no)
    accumulate_congest(congest_list)
    congest_interval += interval
    if congest_list != {}:
        congest_count += 1
        congest_interval_list.append(congest_interval)
        send_chat({'congest '+str(congest_interval): congest_count})
    return congest_list

def find_end2end(graph):
    #FIND N2N PORT
    # url = "http://10.50.34.27:7777/get_networkx"
    # response = requests.get(url)
    # data = response.json()
    # G = json_graph.node_link_graph(data)
    graph = list(graph.edges(data=True))
    dpidcon = dict()
    for link in graph:
        if (type(link[0]) == int and type(link[1]) == int):
            if dpidcon.get(link[0]) == None:
                dpidcon.update({link[0]: {}})
            dpidcon[link[0]].update({link[2].get("port"): link[1]})
    return dpidcon

def find_flow_outport(dpid, port_no, dpidcon):
    """
    port_no {interger}
    dpid {interger}
    flow_list {list} : [flowid, ..]
    original_path {dict} : {flowid : [dpid, dpid, dpid]}
    secondary_path {dict} : {flowid : [dpid, dpid, dpid]}
    dpidcon {dict} : {dpid : {port: dpidcon},...}
    """
    global original_path
    global secondary_path
    flow_list = list()
    nDpid = dpidcon[dpid][port_no]
    for flowid in secondary_path:
        for index in range(len(secondary_path[flowid])-1):
            if secondary_path[flowid][index] == dpid and secondary_path[flowid][index+1] == nDpid:
                flow_list.append(flowid)
    for flowid in original_path:
        if flowid in secondary_path:
            continue
        for index in range(len(original_path[flowid])-1):
            if original_path[flowid][index] == dpid and original_path[flowid][index+1] == nDpid:
                flow_list.append(flowid)
    return flow_list

def find_flow_congest(congest_list, dpidcon):
    """
    dpidcon{dict} : {dpid : {port: dpidcon},...}
    flow_congest {dict} : {dpid: {port: [flowid_1, flowid_2, ..., flowid_n]}}
    port {interger}
    dpid {interger}
    """
    flow_congest = dict()
    for dpid in congest_list:
        temp_port = dict()
        for port_no in congest_list[dpid]:
            temp_port.update({port_no: find_flow_outport(dpid, port_no, dpidcon)})
        flow_congest.update({dpid: temp_port})
    return flow_congest

def sort_flow(flow_priority, dpid, flowlist):
    """
    flowlist{list} : [flowid_1, ..., flowid_n]
    flow_sort {dict} : [{flowid : }, ]
    """
    flow_sort = list()
    for flowid in flowlist:
        if flow_priority[dpid].get(flowid) == None:
            continue
        flow_sort.append({flowid :flow_priority[dpid].get(flowid)})
    # send_text({"sss":flow_sort})
    flow_sorted = sorted(flow_sort, key=lambda flow_object: (flow_object.get(list(flow_object.keys())[0])[0], flow_object.get(list(flow_object.keys())[0])[1]), reverse=True)
    return flow_sorted

def find_sort_flow(flowcongest, flow_priority):
    """
    flowcongest {dict} : {dpid: {port: [flowid_1, flowid_2, ..., flowid_n]}}
    dpidFlowSort {dict} : {dpid: port: [{flowid_1 : [val, duration]}, flowid_2: [val, duration], ..., flowid_n : [val, duration]]}
    """
    dpidFlowSort = dict(flowcongest)
    for dpid in flowcongest:
        for port_no in flowcongest.get(dpid):
            flowlist = flowcongest.get(dpid).get(port_no)
            dpidFlowSort[dpid][port_no] = sort_flow(flow_priority, dpid, flowlist)
    return dpidFlowSort

def update_graph_weight(portstat, bandwitdth_matrix, dpidcon, graph):
    """
    netgraph.copy()
    """
    netgraph = graph.copy()
    update_w = dict()
    for dpid in range(1, len(dpidcon)+1):
        for con in range(1, len(dpidcon)+1):
            if bandwitdth_matrix[dpid-1][con-1] != 0:
                if netgraph.get_edge_data(dpid, con) == None:
                    continue
                port_no = netgraph.get_edge_data(dpid, con).get("port")
                if portstat.get(dpid).get(port_no) == None:
                    continue
                bw = portstat.get(dpid).get(port_no).get('tx_bytes')[0]
                avail_bw = float(bandwitdth_matrix[dpid-1][con-1])*(2**20) - (float(bw)/interval)*8
                avail_bw = max(avail_bw, 0)
                if avail_bw == 0:
                    weight = 10**8
                else:
                    weight = 10**8/(avail_bw)
                update_w.update({(dpid, con): {"weight": weight, "ai": avail_bw}})
    return update_w

def update_graph_avail(portstat, bandwitdth_matrix, dpidcon, graph):
    graph = graph.copy()
    for dpid in range(1, len(bandwitdth_matrix)+1):
        for con in range(1, len(bandwitdth_matrix)+1):
            if bandwitdth_matrix[dpid-1][con-1] != 0:
                if graph.get_edge_data(dpid, con) != None: # Kit add for test
                    port_no = graph.get_edge_data(dpid, con).get("port")
                    if portstat.get(dpid).get(port_no) == None:
                        continue
                    bw = portstat.get(dpid).get(port_no).get('tx_bytes')[0]
                    avail_bw = float(bandwitdth_matrix[int(dpid)-1][con-1])*2**20 - float(bw)/interval*8
                    if avail_bw <= ((45/100)*(float(bandwitdth_matrix[dpid-1][con-1])*2**20)):
                        #print("-----remove :", dpid, dpidcon.get(dpid).get(port))
                        graph.remove_edge(dpid, dpidcon.get(dpid).get(port_no))
                        graph.remove_edge(dpidcon.get(dpid).get(port_no), dpid)
    return graph

def reformat_link_congest(congestList, flowstat, dpidcon):
    """
    congestList
    """
    global secondary_path
    global original_path
    global interval
    link_congest = list()
    for dpid in congestList:
        dpid_port = congestList.get(dpid)
        for port_no in dpid_port:
            flows = dpid_port.get(port_no)
            flowpriority = dict()
            tempdict = dict()
            for flowindex in range(len(flows)):
                flowid = list(flows[flowindex].keys())[0]
                tempflow = dict()
                size = flows[flowindex].get(flowid)[0]
                tempflow.update({'src': flowid[:int(len(flowid)/2)], 'dst': flowid[int(len(flowid)/2):]})
                #tempflow.update({'size': int(flowstat.get(dpid).get(flowid).get('byte')[0]/interval)*8})
                tempflow.update({'size': int(size/interval)*8})
                flowpriority.update({flowindex: tempflow})
            dpid_con = dpidcon[dpid][port_no]
            tempdict.update({"switch":[dpid, dpid_con], "flows": flowpriority, "reroute": "new_path"})
            link_congest.append(tempdict)
    originalpath = list()
    # send_text({"newpath":new_path})
    for flowid in secondary_path.keys():
        # send_text({"currbw newpath": flowstat_monitor.get(flowid)})
        #----Kit add for test------------------------
        # check_back2original[]
        #--------------------------------------------
        if secondary_path.get(flowid) == None:
            dpid = original_path.get(flowid)[0]
        else:
            dpid = secondary_path.get(flowid)[0]

        if flowstat.get(dpid).get(flowid).get('byte_count')[0] <= 0:
            tempflow = dict()
            tempflow.update({'src': flowid[:int(len(flowid)/2)], 'dst': flowid[int(len(flowid)/2):]})
            tempflow.update({'size': 0})
            link_congest.append({"switch": secondary_path.get(flowid)[0], "flow": tempflow, "reroute": "original_path"})
            originalpath.append(flowid)
    for flowid in originalpath:
        del secondary_path[flowid]
    return link_congest

def add_path(path):
    global original_path
    original_path.update(path)

def update_path(path):
    global secondary_path
    secondary_path.update(path)


def first_write():
    with open('port_stat.csv', 'w') as csvfile:
        fieldnames = ['dpid', 'port', 'curr_bw']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

def pandas_portstat_write(bwstat):
    global interval
    #path=/ryu/ryu/app/work/
    for dpid in bwstat.keys():
        port_bw = bwstat.get(dpid)
        newdf = pd.DataFrame({})
        for port_no in port_bw.keys():
            newdf['port'+str(port_no)] = [port_bw.get(port_no).get('tx_bytes')[0]*8/interval]
        try:
            portstat_pandas = pd.read_csv("~/ryu/ryu/app/work/csv/portstat_"+str(dpid)+".csv")
        except:
            portstat_pandas = pd.DataFrame({})
        portstat_pandas.append(newdf).to_csv("~/ryu/ryu/app/work/csv/portstat_"+str(dpid)+".csv", index=False)
#run_multi(555)

def accumulate_congest(congest):
    global interval
    global congest_time
    """
    congest_time = [dpid : port : time]
    """
    for dpid in congest.keys():
        if dpid not in congest_time.keys():
            congest_time.update({int(dpid): {}})
        for port_no in congest.get(dpid):
            if port_no not in congest_time.get(dpid).keys():
                congest_time[int(dpid)][port_no] = interval
            else:
                congest_time[int(dpid)][port_no] += interval
    THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
    my_file = os.path.join(THIS_FOLDER, 'time_congest.json')
    with open(my_file, 'w') as outfile:
        json.dump(congest_time, outfile)

def pandas_n2n_write(fstat):
    global interval
    flowstat_renew = reformat_flowstat(fstat)
    purehost = set()
    purehost_stat = dict()
    for flowid in flowstat_renew:
        purehost.add(flowid[:int(len(flowid)/2)])

    for node in purehost:
        purehost_stat[node] = 0

    for flowid in flowstat_renew:
        node = flowid[:int(len(flowid)/2)]
        purehost_stat[node] += flowstat_renew.get(flowid)
        #purehost_stat[node] += fstat.get(original_path.get(flowid)[0]).get(flowid).get('byte')
    #--------- Kit -----------------
    newdf = pd.DataFrame({})
    for i in end2end:
        newdf[i] = [end2end[i]]
    #-------------------------------
    # newdf = pd.DataFrame({})
    # for flowid in purehost_stat:
    #     newdf[flowid] = [purehost_stat.get(flowid)*8/interval]
    try:
        portstat_pandas = pd.read_csv("~/ryu/ryu/app/work/csv/end_flowstat.csv")
    except:
        portstat_pandas = pd.DataFrame({})
    portstat_pandas.append(newdf).to_csv("~/ryu/ryu/app/work/csv/end_flowstat.csv", index=False)

def pandas_flowstat_write(fstat):
    global interval
    flowstat_renew = reformat_flowstat(fstat)
    newdf = pd.DataFrame({})
    for i in flowstat_renew:
        col = str(int(i[:int(len(i)/2)][-2:])) + '->' + str(int(i[int(len(i)/2):][-2:]))
        newdf[col] = [flowstat_renew[i]*8/interval]
    try:
        portstat_pandas = pd.read_csv("~/ryu/ryu/app/work/csv/flowstat.csv")
    except:
        portstat_pandas = pd.DataFrame({})
    portstat_pandas.append(newdf).to_csv("~/ryu/ryu/app/work/csv/flowstat.csv", index=False)

def send_stat(bwstat):
    url = "http://10.50.34.28:3000/write"
    payload = json.dumps(bwstat)
    headers = {
    'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)

def send_chat(data):
    url = "http://10.50.34.28:3000/chat"
    payload = json.dumps(data)
    headers = {
    'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)

def send_newstat():
    url = "http://10.50.34.28:3000/writenew"
    response = requests.request("POST", url)
def send_text(data):
    url = "http://10.50.34.28:3000/text"
    payload = json.dumps(data)
    headers = {
    'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)

def reformat_flowstat(flowstat):
    """
    flowstat_renew {flowid: bytescount}
    """
    flowstat_renew = dict()
    for dpid in flowstat:
        for flowid in flowstat.get(dpid):
            if flowid in flowstat_renew and flow:
                continue
            flowstat_renew.update({flowid: flowstat.get(dpid).get(flowid).get('byte_count')[0]})
    return flowstat_renew