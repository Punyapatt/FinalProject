import threading
import requests
import time
import json

from requests.api import post

class myThread (threading.Thread):
    def __init__(self, swID):
        threading.Thread.__init__(self)
        self.swID = swID
        self.ports = {}
        self.count = 1
        self.before = {}
        self.bool = True
    def run(self):
        # print("Switch", self.swID)
        # monitor(self.swID, self.ports)
        while True:
            print("Switch %d : %d"% (self.swID, self.count))
            url_flow = "http://10.50.34.27:8080/stats/flow/"+str(self.swID)
            url_port = "http://10.50.34.27:8080/stats/port/"+str(self.swID)
            # url_queue = "http://10.50.34.27:8080/stats/queue/"+str(swID)
            res_flow = requests.get(url_flow)
            res_port = requests.get(url_port)
            # res_queue = requests.get(url_queue)

            data = res_flow.json()
            port_data = res_port.json()
            # print(json.dumps(data, indent=4, sort_keys=True))
            check = {}

            if self.bool:
                for i in port_data.get(str(self.swID)):
                    num_port = i.get("port_no")
                    if num_port != "LOCAL":
                        num_port = "OUTPUT:"+str(num_port)
                        self.before[num_port] = 0
                        self.ports[num_port] = []
            self.bool = False

            for i in data.get(str(self.swID)):
                port = i.get("actions")[0]
                byte_count = i.get("byte_count")
                if port != "OUTPUT:CONTROLLER":
                    if port not in check:
                        check[port] = byte_count   
                    else:
                        check[port] += byte_count
                    # self.before[port] = byte_count
                print("packet_count: %s" % i.get("packet_count"))
                print("byte_count: %s" % byte_count)
                print("actions: %s" % port)
                print()
            print()
            print("-------------------------------")
            print()
            print(self.swID, ' check :',check)
            print(self.swID, 'before :',self.before)
            for i in check:
                num = check[i] - self.before[i]
                self.before[i] = check[i]
                self.ports[i].append(num)
                # last = self.ports[i][(len(self.ports[i])-1)]
                # self.before[i] = last if last != [] else 0
                
            print(self.swID, ' ports :', self.ports)
            print()
            print("----------------------------------------------------------------------------------------")
            print()

            time.sleep(5)
            self.count += 1
            
def main():
    url = "http://10.50.34.27:8080/stats/switches"
    response = requests.get(url)
    print(response.json())

    thread = [myThread(i) for i in response.json()]
    for i in thread:
        i.start()


    # while True:
    #     for i in response.json():
    #         # url = "http://10.50.34.27:8080/stats/aggregateflow/"+str(i)
    #         url = "http://10.50.34.27:8080/stats/flow/"+str(i)
    #         res = requests.get(url)
    #         data = res.json()
            
    #         for j in data:
    #             print("Switch %s : %s"%(i, j))
    #             print(json.dumps(data, indent=4, sort_keys=True))
    #         # print("Switch %d  |  packet_count : %d  |  byte_count : %d"%(i, data[str(i)][0]["packet_count"], data[str(i)][0]["byte_count"]))
    #     time.sleep(5)
    #     print()
    #     print()
main()

