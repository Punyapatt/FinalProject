#
# Simple Shortest Path First Controller in Ryu
# Copyright (C) 2020  Shih-Hao Tseng <shtseng@caltech.edu>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# references/sources:
# http://csie.nqu.edu.tw/smallko/sdn/ryu_sp13.htm
# http://106.15.204.80/2017/05/18/RYU%E5%A4%84%E7%90%86ARP%E5%8D%8F%E8%AE%AE/

from threading import Condition
from ryu.base import app_manager
from ryu.controller import ofp_event, dpset
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls, DEAD_DISPATCHER
from ryu.ofproto import ofproto_v1_3

from ryu.lib import hub
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import packet, ethernet, arp, ether_types, ipv4

from ryu.topology.api import get_switch, get_link, get_host
from ryu.app.wsgi import ControllerBase
from ryu.topology import event, switches
from networkx.readwrite import json_graph
from collections import defaultdict
# from new_mo import run_multi, update_path, add_path
# from monitor_dl import main_thread, send_newstat, update_path, add_path
from monitor import main_thread, send_newstat, update_path, add_path
import networkx as nx
import matplotlib.pyplot as plt
import array
import json
import requests
import time

MAIN_FORWARD_TABLE = 1


class SPFController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SPFController, self).__init__(*args, **kwargs)
        self.topology_api_app = self
        self.net = nx.DiGraph()
        self.nodes = {}
        self.links = {}
        self.no_of_nodes = 0
        self.no_of_links = 0
        self.i = 0
        self.arp_table = {}
        self.ip_to_datapath = {}
        self.dpid_to_datapath = {}
        self.count = 0
        self.switches = []
        self.links = []
        self.hosts = []
        self.route_table = {}
        self.move_flow = []
        self.bw_ = {}
        self.curr_path = {}
        self.count_flow_move = {}
        self.show_reroute = ''
        self.monitor_thread = hub.spawn(self._monitor)


    def _monitor(self):
        time.sleep(5)
        print("Start monitor")
        send_newstat()
        #first Start
        time_ = 1
        interval = 2
        while True:
            start = time.time()
            # -----------------Check congestion for reroute---[     Test      ]-----------------
            G, congestion = main_thread(self.net, 2)
            ryu_time = time.time()
            if congestion != []:
                print("   _ _       _ _             _ _     _ _   _ _  _____")
                print(" /     \\   /     \\  |\\  |  /     \\ |      /       |")
                print("|         |       | | \\ | |    _ _ | - -  \\---\\   |")
                print(" \\ _ _ /   \\_ _ _/  |  \\|  \\ _ _ / | _ _   _ _/   |")
                print()
                print("Congestion return :", congestion, "\n")
                for i in congestion:    
                    if i["reroute"] == "new_path":  #  Find a new route
                        self.show_reroute = i["reroute"]
                        print(" ------------------------")
                        print("|    Reroute new path    |")
                        print(" ------------------------")
                        link_congestion = i["switch"]
                        flows = i["flows"]
                        for flow in flows:
                            src = flows[flow]['src']
                            dst = flows[flow]['dst']
                            flow_size = flows[flow]['size']
                            if flow_size == 0:
                                break
                            G, check = self.reroute(G, link_congestion, src, dst, flow_size)
                            print(check, src, dst)
                            if check:
                                flow = src+dst
                                path = self.curr_path[flow] if flow in self.curr_path else self.route_table
                                print("Switch %d moved flow [%s ---> %s] from path")
                                print()
                                break
                            else:
                                print("Fail")
                                print()
                    elif i["reroute"] == "original_path":
                        # Back to original path
                        self.show_reroute = i["reroute"]
                        print(" -----------------------------")
                        print("|    Bact to original path    |")
                        print(" -----------------------------") 
                        src = i['flow']['src']
                        dst = i['flow']['dst']
                        self.curr_path.pop(src+dst)
                        self.count_flow_move.pop(src+dst)
                        switch = i['switch']
                        path = self.route_table[src][dst]
                        path = path[path.index(switch):]
                        self.new_route(path, self.net, src, dst, 1, False)
                self.move_flow = []
                print("End")
            else:
                print("Normal")
                print("         _ _     _")
                print("|\\  |  /     \\  |  \\   |\\    /|   /\\   |") 
                print("| \\ | |       | | _ |  | \\  / |  /--\\  |")
                print("|  \\|  \\_ _ _/  |  \\   |  \\/  | /    \\ |_ _ _")
                print()        
            # ------------------------------------------------[     Test      ]-----------------
            
            end = time.time()
            print('\n-------------------------')
            print('Monitor time :', ryu_time - start)
            print('Ryu time :', end - ryu_time)
            print("All Time :", end - start)
            interval = 2 - (end - start)
            print('interval :', interval)
            print('-------------------------')
            
            sleep_start = time.time()
            hub.sleep(interval)
            sleep_end = time.time()
            print('Sleep :', sleep_end - sleep_start)
            
    # Find a new route
    def reroute(self, netx, link_conges, src, dst, flow_size):
        if src+dst in self.move_flow:
            return netx, True
        
        print("Reroute")
        # print("av path :", netx.edges(data=True), "\n")
        for i, j, k in netx.edges(data=True):
            if type(i) == int and type(j) == int:
                print((i, j), k)
        
        candidate_path = {}
        netx.remove_edges_from([tuple(link_conges)])
        # original_route = self.route_table[src][dst]
        # print("original route :", original_route)
        try:
            if src+dst in self.curr_path:
                route_path = self.curr_path[src+dst]
                print("Link congestion :", link_conges)
                print("curr path :", self.curr_path)
                if link_conges[0] in self.curr_path[src+dst]:
                    index = self.curr_path[src+dst].index(link_conges[0])
                else:
                    return netx, False
            else:
                # original_route = self.route_table[src][dst]
                route_path = self.route_table[src][dst]
                index = route_path.index(link_conges[0])
                self.count_flow_move[src+dst] = 1
            print("index :", index)
            if index != 0:
                # Reverse original_route
                backward_list = route_path[:index+1][::-1]
                print("backward route_path :", backward_list)
                for i, node in enumerate(backward_list):
                    num = 0
                    for j in range(index-i):
                        print(route_path[j], route_path[j+1])
                        if netx.get_edge_data(route_path[j], route_path[j+1]) == None:
                            return netx, True
                        num += netx.get_edge_data(route_path[j], route_path[j+1])['weight']
                    
                    print("Sum of weight org :", num)
                    length, path = nx.single_source_dijkstra(netx, node, route_path[len(route_path)-1])
                        
                    print(path, length)
                    candidate_path[node] = {'path': route_path[:index-i]+path, 'cost': num+length}       
            else:
                print("index %d"%(0))
                length, path = nx.single_source_dijkstra(netx, src, dst)
                path = path[1:-1]
                print(path, length)
                candidate_path[src] = {'path': path, 'cost': length}

            
            print("\n", candidate_path, "\n")
            candidate_path = dict(sorted(candidate_path.items(), key=lambda item: item[1]['cost']))  
            winner_path = list(candidate_path.items())[0][1]['path']
            print("winner path :", winner_path)
            
            ai = {}
            for i in range(len(winner_path)-1):
                # print(winner_path[i], winner_path[i+1], ':', netx.get_edge_data(winner_path[i], winner_path[i+1]))
                ac = netx.get_edge_data(winner_path[i], winner_path[i+1])['ai'] # available capacity of link between switchs 
                ai[(winner_path[i], winner_path[i+1])] = ac
                ai_ = dict(sorted(ai.items(), key=lambda item: item[1]))
            
            print()
            print("flow size : %f"%(flow_size))
            print("ai", list(ai_)[0], ":", ai_[list(ai_)[0]]) #Minimum bandwidth of new path
            print()

            if flow_size <= ai_[list(ai_)[0]]:
                curr_load = (100/self.bw_[list(ai_)[0]]*(2**20)) - ai_[list(ai_)[0]] # curr_load bits unit
                percent = (100/self.bw_[list(ai_)[0]]*69)/100
                percent *= 2**20    # change Mbits to bits
                print(ai_)
                print('------')
                print(self.bw_)
                print()
                print("bw_ :", 100/self.bw_[list(ai_)[0]]*(2**20))
                print("ai_ :", ai_[list(ai_)[0]])
                print("curr :", curr_load)
                print("curr + flow_size :", curr_load + flow_size)
                print("69% of bw        :", percent, "\n") 
                if curr_load + flow_size < percent:
                    print()
                    print(" Move flow [%s, %s] size : %f"%(src, dst, (flow_size*8)))
                    update_path({src+dst : winner_path})
                    self.move_flow.append(src+dst)
                    self.curr_path[src+dst] = winner_path
                    self.count_flow_move[src+dst] += 1
                    print("\ncurr_path :", self.curr_path, "\n")
                    self.new_route(winner_path, netx, src, dst, 2, True)
                    for i in range(len(winner_path)-1):
                        netx.get_edge_data(winner_path[i], winner_path[i+1])['ai'] -= flow_size # Update available capacity
                        netx.get_edge_data(winner_path[i], winner_path[i+1])['weight'] = 100 / ((flow_size)/(2**20)) # Update weight
                    return netx, True
                else:
                    return netx, False
            else:
                return netx, False

        except nx.NetworkXNoPath as err:
            print(err)
            return netx, True

    # Prepare to add flow entry
    def new_route(self, path, netx, src, dst, t0_direct, table_2):
        print("------------------[ new_route ]----------------------")
        path_d = path + [dst] # path add destination ex. [1, 2, 3] + ['00:00:00:00:00:01']
        flow = [src, dst]
        for i in range(2):
            if i == 1:
                # for route backward
                path = path[::-1]
                flow.reverse()
                path_d = path + [src]
            # print(path_d)
            path4new_route = path_d[:-1][::-1]
            # for i in path_d[:-1]
            print("path4new_route :", path4new_route)
            for i in path4new_route:
                print(i)
                next_index = path_d[path_d.index(i)+1]
                print('next_index :', next_index)
                print(netx[i])
                print()
                out_port = netx[i][next_index]['port']
                # print("Current dpid : %s" % i)
                
                # print("Next dpid [%s] : %s\n" %(next_index, netx[i][next_index]))
                        
                    # url_flow = "http://10.50.34.27:8080/stats/flow/"+str(i)
                    # response = requests.get(url_flow)
                    # data = response.json()

                    # for stat in [flow for flow in data.get("1") if flow.get('priority') == 32768 and flow.get('table_id') == 0]:
                    #     if stat.get('match').get('dl_src') == flow[0] and stat.get('match').get('dl_dst') == flow[1]:
                    #         cmd_table_0 = 'modify'
                    #     else:
                    #         cmd_table_0 = 'add'
                
                response = requests.post("http://127.0.0.1:8080/stats/flow/"+str(i), 
                                        data=json.dumps({
                                            "table_id": 0,
                                            "cookie": 0,
                                            "cookie_mask": 0,
                                            "match":{
                                                "dl_src": flow[0],
                                                "dl_dst": flow[1]
                                            }     
                                        }))
                data = response.json()
                
                if data[str(i)] != []:
                    for j in data[str(i)]:
                        if j.get('byte_count') > 0:
                            print("get byte count :", j.get('byte_count'))
                            cmd_table_0 = "modify" 
                        # else:
                        #     self.delete_flow(i, flow[0], flow[1], in_port)
                else:
                    cmd_table_0 = "add"
                                                             
                self.add_new_route(i, flow[0], flow[1], out_port, cmd_table_0, t0_direct, table_2)
        print("\n\n")
        print("%s"%(self.show_reroute))
        print(" _ _ _  .         .   _ _ _   ")
        print("|_ _ _  |  |\\  |  |  /        |     |")
        print("|       |  | \\ |  |  \\- - -\\  |-----|")
        print("|       |  |  \\|  |   _ _ _/  |     |")
        print("\n\n")

    
    # Update flow entry to OVS                  
    def add_new_route(self, dpid, src, dst, out_port, cmd_t0, t0_direct, exc_t2=None):
        # Add or modify table 0
        print("<-------- s%d table 0 %s----------->"%(dpid, cmd_t0))
        print("Table 0 direct to [%d]"%(t0_direct))
        response = requests.post("http://127.0.0.1:8080/stats/flowentry/"+cmd_t0,
                                 data=json.dumps({
                                    "dpid": int(dpid),
                                    "cookie": 0,
                                    "table_id": 0,
                                    "priority": 32768,
                                    "match": {
                                        "dl_src": src,
                                        "dl_dst": dst
                                         },
                                     "actions": [
                                        {
                                            "type": "GOTO_TABLE",
                                            "table_id": t0_direct
                                        }
                                         ]
                                 }))
        print("Table 0 :", response, "\n\n")
        
        if exc_t2:
            print("<-------- s%d table 2----------->"%(dpid))
            # Add or modify table 2
            response = requests.post("http://127.0.0.1:8080/stats/flowentry/add",
                                    data=json.dumps({
                                        "dpid": int(dpid),
                                        "cookie": 0,
                                        "table_id": 2,
                                        "idle_timeout": 0,
                                        "hard_timeout": 0,
                                        "priority": 32768,
                                        "match": {
                                            "dl_src": src,
                                            "dl_dst": dst
                                            },
                                        "actions": [
                                            {
                                                "type": "OUTPUT",
                                                "port": int(out_port)
                                            }
                                            ]
                                    }))
            print("Table 2 :", response, "\n\n")
    
    def delete_flow(self, dpid, src, dst, in_port):
        response = requests.post("http://127.0.0.1:8080/stats/flowentry/delete_strict",
                                    data=json.dumps({
                                        "dpid": int(dpid),
                                        "cookie": 0,
                                        "table_id": 0,
                                        "idle_timeout": 0,
                                        "hard_timeout": 0,
                                        "priority": 32768,
                                        "match": {
                                            "in_port": in_port,
                                            "dl_src": src,
                                            "dl_dst": dst
                                        }
                                    }))
        print("Delete Table 0 :", response)
     
    
    def add_default_flow(self, datapath, src, dst):
        print("Add default flow")
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = datapath.ofproto_parser.OFPMatch(eth_src=src, eth_dst=dst)
        inst = [parser.OFPInstructionGotoTable(MAIN_FORWARD_TABLE)]
        mod = parser.OFPFlowMod(
            datapath=datapath, match=match, table_id=0, instructions=inst)
        datapath.send_msg(mod)

    def add_flow(self, datapath, src, dst, out_port):
        print("from add flow :", datapath.id)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = datapath.ofproto_parser.OFPMatch(eth_src=src, eth_dst=dst)
        actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
        inst = [parser.OFPInstructionActions(
            ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = datapath.ofproto_parser.OFPFlowMod(
            datapath=datapath, match=match, cookie=0,
            command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0,
            priority=ofproto.OFP_DEFAULT_PRIORITY, instructions=inst, table_id=MAIN_FORWARD_TABLE)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        self.logger.info("Switch features handler")
        datapath = ev.msg.datapath
        self.logger.info(datapath.id)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(
            ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(
            ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = datapath.ofproto_parser.OFPFlowMod(
            datapath=datapath, match=match, cookie=0,
            command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0, priority=0, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):

        # ----------------------------------------------------------------------------------------------

        # self.count += 1
        # self.logger.info("Packet_in_handler %d", self.count)
        msg = ev.msg
        pkt = packet.Packet(array.array('B', ev.msg.data))
        
        
        ip = pkt.get_protocols(ipv4.ipv4)
        if ip != []:
            datapath = ev.msg.datapath
            print("dpid :", datapath.id)
            self.logger.info("%s --> %s", ip[0].src, ip[0].dst)
        # ----------------------------------------------------------------------------------------------

        pkt = packet.Packet(msg.data)
        eth_hdr = pkt.get_protocol(ethernet.ethernet)

        if not eth_hdr:
            return

        # filters out LLDP
        if eth_hdr.ethertype == 0x88cc:
            return

        datapath = msg.datapath
        dpid = datapath.id
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        # print("in_port :", in_port)

        dst = eth_hdr.dst
        src = eth_hdr.src

        # for routing
        if src not in self.net:
            self.count += 1
            print("Count :", self.count, "\n")
            self.net.add_node(src)
            self.net.add_edge(dpid, src, port=in_port)
            self.net.add_edge(src, dpid)

            print("Create JSON")
            data = json_graph.node_link_data(self.net)
            with open('ryu/app/networkx.json', 'w') as f:
                json.dump(data, f, indent=4)

            url = "http://127.0.0.1:7777/networkx"
            payload = json.dumps(data)
            headers = {
                'Content-Type': 'application/json'
            }
            response = requests.request(
                "PUT", url, headers=headers, data=payload)
            print(response)

        # ARP
        if eth_hdr.ethertype == 0x0806:
            self.arp_handler(
                pkt=pkt,
                src=src,
                dst=dst,
                datapath=datapath,
                dpid=dpid,
                ofproto=ofproto,
                parser=parser,
                in_port=in_port
            )
            return

        # IPv4 routing
        if eth_hdr.ethertype == 0x0800:
            self.ipv4_routing(
                msg=msg,
                src=src,
                dst=dst,
                datapath=datapath,
                dpid=dpid,
                ofproto=ofproto,
                parser=parser,
                in_port=in_port
            )
            return

    def arp_handler(self, pkt, src, dst,datapath,dpid,ofproto,parser,in_port):
        arp_hdr = pkt.get_protocol(arp.arp)
        if not arp_hdr:
            return

        arp_src_ip = arp_hdr.src_ip
        arp_dst_ip = arp_hdr.dst_ip
        eth_src = src
        eth_dst = dst

        self.arp_table[arp_src_ip] = eth_src
        self.ip_to_datapath[arp_src_ip] = datapath

        print(" ARP: %s (%s) -> %s (%s)" % (arp_src_ip, src, arp_dst_ip, dst))
        print(arp_hdr.opcode)
        # print(arp.ARP_REQUEST)
        # print(arp.ARP_REPLY)
        hwtype = arp_hdr.hwtype
        proto = arp_hdr.proto
        hlen = arp_hdr.hlen
        plen = arp_hdr.plen

        if arp_hdr.opcode == arp.ARP_REQUEST:
            print("Arp request")
            # request
            # lookup the arp_table
            if arp_dst_ip in self.arp_table:
                print(self.arp_table)
                actions = [parser.OFPActionOutput(in_port)]
                ARP_Reply = packet.Packet()
                eth_dst = self.arp_table[arp_dst_ip]
                # reply
                ARP_Reply.add_protocol(ethernet.ethernet(
                    ethertype=0x0806,
                    dst=eth_src,
                    src=eth_dst))
                ARP_Reply.add_protocol(arp.arp(
                    opcode=arp.ARP_REPLY,
                    src_mac=eth_dst,
                    src_ip=arp_dst_ip,
                    dst_mac=eth_src,
                    dst_ip=arp_src_ip))

                ARP_Reply.serialize()
                # send back
                out = parser.OFPPacketOut(
                    datapath=datapath,
                    buffer_id=ofproto.OFP_NO_BUFFER,
                    in_port=ofproto.OFPP_CONTROLLER,
                    actions=actions, data=ARP_Reply.data)
                datapath.send_msg(out)
                return True
            else:
                # need to ask the nodes
                print(self.arp_table)
                for sw_datapath in self.dpid_to_datapath.values():

                    # -----Direct arp request w/o flood-------------
                    ip_to_mac = arp_dst_ip[7:]
                    mac = '00:00:00:00:00:'+ \
                        str('%02d' % int(hex(int(ip_to_mac)).split('x')[-1]))

                    if mac not in self.net[sw_datapath.id]:
                        continue
                    print(self.net[sw_datapath.id])
                    port = self.net[sw_datapath.id][mac]['port']
                    print(port)
                    # ----------------------------------------------

                    actions = [parser.OFPActionOutput(port)]
                    # actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
                    out = parser.OFPPacketOut(
                        datapath=sw_datapath,
                        buffer_id=ofproto.OFP_NO_BUFFER,
                        in_port=ofproto.OFPP_CONTROLLER,
                        actions=actions, data=pkt.data)
                    sw_datapath.send_msg(out)
                    break

        elif arp_hdr.opcode == arp.ARP_REPLY:
            # it is a reply
            # print(arp_dst_ip)
            # print(self.ip_to_datapath)
            print("Arp table :", self.arp_table)
            print("--\nArp Reply\n--\n")
            if arp_dst_ip in self.ip_to_datapath:
                print('Yes')
                datapath = self.ip_to_datapath[arp_dst_ip]

                actions = [parser.OFPActionOutput(in_port)]
                ARP_Reply = packet.Packet()

                # reply
                # ethertype=pkt_ethernet.ethertype,
                ARP_Reply.add_protocol(ethernet.ethernet(
                    ethertype=0x0806,
                    dst=eth_dst,
                    src=eth_src))
                ARP_Reply.add_protocol(arp.arp(
                    opcode=arp.ARP_REPLY,
                    src_mac=eth_src,
                    src_ip=arp_src_ip,
                    dst_mac=eth_dst,
                    dst_ip=arp_dst_ip))

                ARP_Reply.serialize()
                # send back
                out = parser.OFPPacketOut(
                    datapath=datapath,
                    buffer_id=ofproto.OFP_NO_BUFFER,
                    in_port=ofproto.OFPP_CONTROLLER,
                    actions=actions, data=ARP_Reply.data)
                datapath.send_msg(out)
                print('Return Trueeeeeeeeeeeeee!!!')
                return True
        return False

    def ipv4_routing(self, msg, src, dst,datapath,dpid,ofproto,parser,in_port):
        if dst in self.net:
            print("%s -> %s" % (src, dst))
            try:
                path = nx.shortest_path(self.net, src, dst, weight='weight')
                add_path({src+dst:path[1:-1]})
                if src not in self.route_table:
                    self.route_table[src] = {dst: path[1:-1]}
                else:
                    self.route_table[src][dst] = path[1:-1]
                # print("Path :", {src+dst : path[1:-1]})

                # install the path
                try:
                    next_index = path.index(dpid)+1
                except:
                    print("except")
                    return
                current_dpid = dpid
                current_dp = datapath
                path_len = len(path)

                return_out_port = None

                # print("\nPath len :", path_len)
                while next_index < path_len:
                    print("Next index :", next_index, "\n")
                    if current_dp is None:
                        continue

                    next_dpid = path[next_index]
                    out_port = self.net[current_dpid][next_dpid]['port']
                    
                    # print("current_dp [%s]" % current_dpid)
                    # print("next_dp [%s]" % next_dpid, self.net[current_dpid][next_dpid])
                    # print("out_port :", out_port)
                         
                    if current_dpid == dpid:
                        return_out_port = out_port
                        
                    self.add_default_flow(
                        datapath=current_dp,
                        src=src,
                        dst=dst
                    )
                    
                    self.add_flow(
                        datapath=current_dp,
                        src=src,
                        dst=dst,
                        out_port=out_port
                    )

                    next_index += 1
                    current_dpid = next_dpid
                    if current_dpid in self.dpid_to_datapath:
                        current_dp = self.dpid_to_datapath[current_dpid]
                    else:
                        current_dp = None

                out_port = return_out_port
                print("Find the path successfully (%s -> %s)" % (src, dst))
                print(self.route_table)
                print("------", end="\n\n")
            except nx.NetworkXNoPath as err:
                print("-------")
                print(err)
                print("------", end="\n\n")
                return
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
        # return the packet
        out = datapath.ofproto_parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port,
            actions=actions)
        datapath.send_msg(out)

    @set_ev_cls(event.EventSwitchEnter)
    def switch_enter(self, ev):
        print("switch_enter")
        datapath = ev.switch.dp
        ofp_parser = datapath.ofproto_parser
        dpid = datapath.id
        if dpid not in self.dpid_to_datapath:
            self.dpid_to_datapath[dpid] = datapath

            # Request port/link descriptions, useful for obtaining bandwidth
            req = ofp_parser.OFPPortDescStatsRequest(datapath)
            datapath.send_msg(req)

        self.net.add_node(dpid)

    @set_ev_cls(event.EventSwitchLeave)
    def switch_leave(self, ev):
        datapath = ev.switch.dp
        dpid = datapath.id
        if dpid in self.dpid_to_datapath:
            del self.dpid_to_datapath[dpid]
        self.net.remove_node(dpid)

    @set_ev_cls(event.EventLinkAdd)
    def link_add(self, ev):
        src_port_no = ev.link.src.port_no
        src_dpid = ev.link.src.dpid
        dst_dpid = ev.link.dst.dpid
        # ---------------------------------------------------
        url = "http://10.50.34.27:7777/topology"
        response = requests.get(url)
        data = response.json()
        bw = data["bandwidth"]["switch"]
        w = bw['s'+str(src_dpid)][dst_dpid-1]
        w = 100/w
        # ---------------------------------------------------

        self.bw_[(src_dpid, dst_dpid)] = w
        self.net.add_edge(src_dpid, dst_dpid, port=src_port_no, weight=w)
