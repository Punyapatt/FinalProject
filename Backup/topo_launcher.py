#!/usr/bin/python
"""
Custom topology launcher Mininet, with traffic generation using iperf
"""

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch, DefaultController
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.util import customClass

from new_mininet import Topology

from os import path
from os import mkdir
import os
import random
import time
import sys
import re
import numpy as np
import json
import requests
import pickle


# GLOBAL VARIABLES
# experiment_duration = 180  # seconds
# controller_ip = '10.14.87.5'  # ubuntu_lab


# FLOW SIZES
# Calculations
#
# flows with 15 packets or greater is an elephant flow as per CISCO
# considering 1512 byte packets, elephant flow size is
#
# threshold = (14 * 1512)/1000 = 21.168 KBytes
#

# exec(open('/home/user01/sflow-rt/extras/sflow.py').read())

traffic_history = {}
e_bytes_list, m_bytes_list = [], []
e_rate, m_rate = [], []
e_pair, m_pair = [], []

mice_flow_min = 100  # KBytes = 100KB
mice_flow_max = 10240  # KBytes = 10MB
elephant_flow_min = 10240  # KBytes = 10MB
elephant_flow_max = 1024*1024*10  # KBytes = 10 GB

# FLOWS
# n_mice_flows = 45
# n_elephant_flows = 5
# n_iot_flows = 0

# L4 PROTOCOLS
# protocol_list = ['--udp', '']  # udp / tcp
protocol_list = ['-u', '']  # udp / tcp
port_min = 1025
port_max = 65536

# IPERF SETTINGS
sampling_interval = '1'  # seconds

e_bytes = ['5m', '8m', '10m', '15m', '20m', '30m', '40m']
m_bytes = ['2m', '3m', '4m', '5m', '8m', '10m', '15m']

n_bytes = ['2m', '3m', '4m', '5m', '8m', '10m', '15m', '20m']
servers = ['h5', 'h6']

# ELEPHANT FLOW PARAMS
# elephant_bandwidth_list = ['10M', '20M', '30M', '40M', '50M', '60M', '70M', '80M', '90M', '100M',
#                            '200M', '300M', '400M', '500M', '600M', '700M', '800M', '900M', '1000M']
elephant_bandwidth_list = ['6m', '7m', '8m', '10m', '14m']

# MICE FLOW PARAMS
# mice_bandwidth_list = ['100K', '200K', '300K', '400K', '500K', '600K', '700K', '800K', '900K', '1000K',
#                        '2000K', '3000K', '4000K', '5000K', '6000K', '7000K', '8000K', '9000K', '10000K', '1000K']
mice_bandwidth_list = ['500K', '600K', '700K', '800K', '900K', '1m', '2m']


def random_normal_number(low, high):
    range = high - low
    mean = int(float(range) * float(75) / float(100)) + low
    sd = int(float(range) / float(4))
    num = np.random.normal(mean, sd)
    return int(num)

def send_to_console(number, f_type, pair, bandwidth_argument, n_b):
    url = "http://10.50.34.28:3000/text"
    data = {'Number':number,
            'flow type':f_type,
            'pair': pair,
            'rate':bandwidth_argument,
            '-n':n_b}
    payload = json.dumps(data)
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)

def traffic_history_func(src, dst, ptc, bandwidth_argument, duration):
    if src+"->"+dst not in traffic_history:
        traffic_history["%s->%s"%(src, dst)] = [[ptc, bandwidth_argument, duration]]
    else:
        traffic_history["%s->%s"%(src, dst)].append([ptc, bandwidth_argument, duration])
        
def generate_elephant_flows(id, duration, net, log_dir):

    """
    Generate Elephant flows
    May use either tcp or udp
    """
    
    hosts = net.hosts

    # select random src and dst
    end_points = random.sample(hosts, 2)
    src = net.get(str(end_points[0]))
    dst = net.get(str(end_points[1]))
    e_pair.append([str(end_points[0]), str(end_points[1])])
    print("elephant flow [", src, dst, "]")
    
    # select connection params
    protocol = random.choice(protocol_list)
    port_argument = str(random.randint(port_min, port_max))
    bandwidth_argument = random.choice(elephant_bandwidth_list)
    e_rate.append(bandwidth_argument) #log
    n_b = random.choice(e_bytes)
    e_bytes_list.append(n_b) #log
    
    ptc = 'udp' if protocol == "-u" else 'tcp'
    traffic_history_func(str(src), str(dst), ptc, bandwidth_argument, duration)
    send_to_console(id+1, 'E', str(src)+" -> "+str(dst), bandwidth_argument, n_b)
    
    # create cmd
    server_cmd = "iperf -s "
    server_cmd += "-u"
    server_cmd += " -p "
    server_cmd += port_argument
    server_cmd += " -i "
    server_cmd += sampling_interval
    server_cmd += " > "
    server_cmd += log_dir + "/elephant_flow_%003d" % id + ".txt 2>&1 "
    server_cmd += " & "

    client_cmd = "iperf -c "
    client_cmd += dst.IP() + " "
    client_cmd += "-u"
    client_cmd += " -p "
    client_cmd += port_argument
    # if protocol == "-u":
    #     client_cmd += " -b "
    #     client_cmd += bandwidth_argument
    client_cmd += " -b "
    client_cmd += bandwidth_argument
    # client_cmd += " -t "
    # client_cmd += str(duration)
    client_cmd += " -n "
    client_cmd += n_b
    client_cmd += " & "

    # send the cmd
    dst.cmdPrint(server_cmd)
    src.cmdPrint(client_cmd)


# def generate_mice_flows(id, duration, net, log_dir, src, dst, rate):
def generate_mice_flows(id, duration, net, log_dir):

    """
    Generate mice flows
    May use either tcp or udp
    """
    hosts = net.hosts

    # select random src and dst
    end_points = random.sample(hosts, 2)
    
    src = net.get(str(end_points[0]))
    dst = net.get(str(end_points[1]))
    m_pair.append([str(end_points[0]), str(end_points[1])])
    # src = net.get(src)
    # dst = net.get(dst)
    print("mice flow [", src, dst, "]")

    # select connection params
    protocol = random.choice(protocol_list)
    port_argument = str(random.randint(port_min, port_max))
    bandwidth_argument = random.choice(mice_bandwidth_list)
    m_rate.append(bandwidth_argument)
    n_b = random.choice(m_bytes)
    m_bytes_list.append(n_b)

    ptc = 'udp' if protocol == "-u" else 'tcp'
    traffic_history_func(str(src), str(dst), ptc, bandwidth_argument, duration)
    send_to_console(id+1, 'M', str(src)+" -> "+str(dst), bandwidth_argument, n_b)
    
    # create cmd
    server_cmd = "iperf -s "
    server_cmd += "-u"
    server_cmd += " -p "
    server_cmd += port_argument
    server_cmd += " -i "
    server_cmd += sampling_interval
    server_cmd += " > "
    server_cmd += log_dir + "/mice_flow_%003d" % id + ".txt 2>&1 "
    server_cmd += " & "

    client_cmd = "iperf -c "
    client_cmd += dst.IP() + " "
    client_cmd += "-u"
    client_cmd += " -p "
    client_cmd += port_argument
    # if protocol == "-u":
    #     client_cmd += " -b "
    #     client_cmd += bandwidth_argument
    client_cmd += " -b "
    client_cmd += bandwidth_argument
    # client_cmd += rate
    # client_cmd += " -t "
    # client_cmd += str(duration)
    client_cmd += " -n "
    client_cmd += n_b
    client_cmd += " & "
    
    # ping = "ping "
    # ping += dst.IP() + " > "
    # ping += log_dir + "/ping_%003d" % id + ".txt &"

    # send the cmd
    dst.cmdPrint(server_cmd)
    src.cmdPrint(client_cmd)
    
    # src.cmdPrint(ping)


def generate_flows(n_elephant_flows, n_mice_flows, duration, net, log_dir):
    """
    Generate elephant and mice flows randomly for the given duration
    """
    
    if not path.exists(log_dir):
        print("Path", end=" ")
        print(path.exists(log_dir))
        mkdir(log_dir)
        print("mkdir success!!!!!!!!!!!!")

    n_total_flows = n_elephant_flows + n_mice_flows
    interval = duration / n_total_flows
    print("n_total_flows :", n_total_flows)
    print("interval :", interval)

    # ------------------------  setting random mice flow or elephant flows
    flow_type = []
    for i in range(n_elephant_flows):
        flow_type.append('E')
    for i in range(n_mice_flows):
        flow_type.append('M')
    random.shuffle(flow_type)

    # ------------------------  setting random flow start times
    flow_start_time = []
    for i in range(n_total_flows):
        # n = random.randint(1, interval)
        n = random.randint(1, 10)
        if i == 0:
            flow_start_time.append(0)
        else:
            flow_start_time.append(flow_start_time[i - 1] + n)

    # setting random flow end times
    # using normal distribution
    # we will keep duration till 95% of the total duration
    # the remaining 5% will be used as buffer to finish off the existing flows
    flow_end_time = []
    for i in range(n_total_flows):
        s = flow_start_time[i]
        # e = int(float(95) / float(100) * float(duration))  # 95% of the duration
        # end_time = random_normal_number(s, e)
        end_time = random_normal_number(s, s+50)
        print(s, end_time)
        # while end_time > e:
        #     if s > e:
        #         break
        #     end_time = random_normal_number(s, e)
        print("end time :", end_time)
        flow_end_time.append(end_time)

    # # calculating flow duration from start time and end time generated above
    flow_duration = []
    for i in range(n_total_flows):
        flow_duration.append(flow_end_time[i] - flow_start_time[i])

    print()
    print("Flow type : ", flow_type)
    print("Flow start time :", flow_start_time)
    print("Flow end time :", flow_end_time)
    print("Flow duration :", flow_duration)
    print("Remaining duration :" + str(duration - flow_start_time[-1]))
    print()

    # generating the flows
    for i in range(n_total_flows):
        if i == 0:
            time.sleep(flow_start_time[i])
        else:
            time.sleep(flow_start_time[i] - flow_start_time[i-1])
        if flow_type[i] == 'E':
            generate_elephant_flows(i, flow_duration[i], net, log_dir)
        elif flow_type[i] == 'M':
            generate_mice_flows(i, flow_duration[i], net, log_dir) 
    pickle.dump([flow_type, flow_start_time, e_pair, m_pair, e_bytes_list, m_bytes_list, e_rate, m_rate], open("variables.p", "wb"))
    # test_dict = {'flow_type':flow_type, 
    #              'flow_start_time':flow_start_time,
    #              'e_pair':e_pair,
    #              'm_pair':m_pair,
    #              'e_bytes_list':e_bytes_list,
    #              'm_bytes_list':m_bytes_list}     
    # with open('variables.json', 'w') as f:
    #     json.dump(test_dict, f)
    
    # sleeping for the remaining duration of the experiment
    # remaining_duration = duration - flow_start_time[-1]
    # info("Traffic started, going to sleep for %s seconds...\n " % remaining_duration)
    # time.sleep(remaining_duration)
    print("Enter for kill iperf")
    while True:
        if input() == '':
            break

    # ending all the flows generated by
    # killing the iperf sessions
    info("Stopping traffic...\n")
    info("Killing active iperf sessions...\n")

    # killing iperf in all the hosts
    for host in net.hosts:
        host.cmdPrint('killall -9 iperf')
    
    for i in traffic_history:
        print("%s :"%(i), traffic_history[i])


# Main function
if __name__ == "__main__":
    # Loading default parameter values
    log_dir = "/home/user01/mininet-log/test-"
    topology = Topology()
    default_controller = True
    controller_ip = "127.0.0.1"  # localhost
    controller_port = 6633
    debug_flag = False
    debug_host = "localhost"
    debug_port = 6000
    servers = []
    clients = []

    
    # Starting program
    setLogLevel('info')

    # creating log directory
    # print("Before : " + log_dir)
    # log_dir = path.expanduser('~') + log_dir
    # print("After : " + log_dir)
    i = 1
    while True:
        if not path.exists(log_dir + str(i)):
            # mkdir(log_dir + str(i))
            log_dir = log_dir + str(i)
            break
        i = i+1
    

    net = Mininet(topo=topology, controller=lambda name: RemoteController(name, ip='127.0.0.1'), host=CPULimitedHost, link=TCLink,
                      switch=OVSSwitch, autoSetMacs=True, autoStaticArp=True)
    net.start()
    host_test = net.hosts
    print()
    print(host_test)
    for i in host_test:
        print(str(i))
    servers = random.sample(host_test, 2)
    clients = list(set(host_test)-set(servers))
    print("Servers :", servers)
    print("Client :", clients)
    # print()
    # print("-----------------------------------")
    # print("Time sleep for wait controller !!!")
    # print("-----------------------------------")
    # print()
    # time.sleep(15)
    # net.pingAll()
    # CLI(net)

    user_input = "QUIT"

    # run till user quits
    while True:
        # if user enters CTRL + D then treat it as quit
        try:
            user_input = input("GEN/CLI/QUIT: ")
        except EOFError as error:
            user_input = "QUIT"

        if user_input.upper() == "GEN":
            # experiment_duration = int(input("Experiment duration: "))
            experiment_duration = 1
            n_elephant_flows = int(input("No of elephant flows: "))
            n_mice_flows = int(input("No of mice flows: "))
            
            # experiment_duration = 1
            # n_elephant_flows = 1
            # n_mice_flows = 1

            generate_flows(n_elephant_flows, n_mice_flows, experiment_duration, net, log_dir)
            
        elif user_input.upper() == "CLI":
            info("Running CLI...\n")
            CLI(net)

        elif user_input.upper() == "QUIT":
            info("Terminating...\n")
            net.stop()
            break

        else:
            print("Command not found")


'''
Area for scratch pad

'''
