import random
def randomtopology3():
    """
    maxLink <= amountSwitch
    amountSwitch: switch on topology > 1
    amountHost: host on topology
    
    """
    amountSwitch = 10
    amountHost = 10
    maxLink = 5
    listSw = [random.randint(1, maxLink) for i in range(amountSwitch)] #among link connected
    listHs = [random.randint(1, amountSwitch) for i in range(amountHost)]
    vertices = [[0 for i in range(amountSwitch)] for i in range(amountSwitch)]
    dicSw = dict()
    dicHs = dict()
    dicLs = dict()
    dicIp = dict()
    #sumLink = sum(listSw)
    freeSw = set([i for i in range(amountSwitch)]) #switch that have free port

    #case1 link ตรงกัน
    #case2 link เป็นเลขคี่
    #case3 link ไม่กระจายจนมี sw ที่ขาดการเชื่อมต่อ
    #case4 link ไม่เชื่อมต่อกันทั้งหมด

    #fix case3
    setSw = set(range(amountSwitch))
    setSwEnd = set()
    while (len(setSwEnd)<amountSwitch): 
        if (len(setSwEnd) == 0):
            sw = random.randint(0, amountSwitch-1)
        else:
            index = random.randint(0, len(setSw)-1)
            sw = list(setSw)[index]
            indexcon = random.randint(0, len(setSwEnd)-1)
            swcon = list(setSwEnd)[indexcon]
            vertices[sw][swcon] = 1
            vertices[swcon][sw] = 1
        setSwEnd.add(sw)
        setSw -= set([sw])

    #random topo
    for i in range(amountSwitch-1): # port สุดท้ายไม่ต้องทำ
        if (i not in freeSw): # ถ้า port ไม่เหลือไปดูตัวอื่น
            continue
        count = listSw[i] - 1 # -1 คือลบอันก่อนหน้า
        listSw[i] = 0
        freeSw.remove(i)
        while (count > 0):
            while len(freeSw) > 0:
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
    #check all switch connect case4
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
    #random ip host
    while True:
        listip = ["10."+str(random.randint(1, 254))+"."+str(random.randint(1, 254))+"."+str(random.randint(1, 254)) for _ in range(amountHost)]
        if (len(set(listip)) == amountHost):
            break
    #process list
    for i in range(amountSwitch):
        dicSw.update({'s'+str(i+1): vertices[i]})
    for i in range(amountHost):
        dicHs.update({'h'+str(i+1): 's'+str(listHs[i])})
    linkl = list()
    for i in range(amountSwitch):
        templist = list()
        for j in range(amountSwitch):
            if (vertices[i][j] == 1):
                templist.append("s"+str(j+1))
        linkl.append(templist)
    for i in range(amountHost):
        linkl[listHs[i]-1].append("h"+str(i+1))
    for i in range(amountSwitch):
        dicLs.update({'s'+str(i+1): linkl[i]})

    for i in range(amountHost):
        dicIp.update({'h'+str(i+1): listip[i]})
 
    sumdict = dict()
    
    sumdict.update({'switch': dicSw})
    sumdict.update({'host': dicHs})
    sumdict.update({'link': dicLs})
    sumdict.update({'ip': dicIp})
    return sumdict


if __name__ == "__main__":
    print(randomtopology3())
