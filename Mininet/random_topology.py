import random
def randomtopology3():
    """
    maxLink < amountSwitch
    amountSwitch: switch on topology 
    amountHost: host on topology
    """
    amountSwitch = 10
    amountHost = 10
    maxLink = 3
    listSw = [random.randint(1, maxLink) for i in range(amountSwitch)] #among link connected
    listHs = [random.randint(1, amountSwitch) for i in range(amountHost)]
    vertices = [[0 for i in range(amountSwitch)] for i in range(amountSwitch)]
    dicSw = dict()
    dicHs = dict()
    freeSw = set([i for i in range(amountSwitch)]) #switch that have free port
    
    #case link ตรงกัน
    #case link เป็นเลขคี่
    #case link ไม่กระจายจนมี sw ที่ขาดการเชื่อมต่อ
    
    for i in range(amountSwitch-1): # port สุดท้ายไม่ต้องทำ
        if (i not in freeSw): # ถ้า port ไม่เหลือไปดูตัวอื่น
            continue
        count = listSw[i]
        listSw[i] = 0
        freeSw.remove(i)
        while (count > 0):
            while (len(freeSw) > 0):
                connect = random.randint(0, len(freeSw)-1)
                port = list(freeSw)[connect]
                if (connect != i and listSw[port] > 0):
                    listSw[port] -= 1
                    vertices[port][i], vertices[i][port] = 1, 1
                    if (listSw[port] <= 0):
                        freeSw.remove(port)
                    break    
            count -= 1
    #Check amount link connect
    linkConnectSwitch = [vertices[i].count(1) for i in range(amountSwitch)]
    #check all switch connect
    for i in range(amountSwitch):
        if (linkConnectSwitch[i] == 0):
            #can call random for gen topology
            freeSw = [1 if (linkConnectSwitch[j] < maxLink and j != i) else 0 for j in range(amountSwitch)]
            if (freeSw.count(1) == 0):
                freeSw = [sw for sw in range(amountSwitch)]
                freeSw = set(freeSw).remove(i)     
            else:
                freeSwtemp = set()
                for i in range(amountSwitch):
                    if (freeSw[i] == 1):
                        freeSwtemp.add(i)
                freeSw = freeSwtemp
            connect = random.randint(0, len(freeSw)-1)
            port = list(freeSw)[connect]
            vertices[i][port] = 1
            vertices[port][i] = 1

    for i in range(amountSwitch):
        dicSw.update({'s'+str(i+1): vertices[i]})
    for i in range(amountHost):
        dicHs.update({'h'+str(i+1): 's'+str(listHs[i])})
    sumdict = dict()
    sumdict.update({'switch': dicSw})
    sumdict.update({'host': dicHs})
    return sumdict

if __name__ == "__main__":
    print(randomtopology3())
