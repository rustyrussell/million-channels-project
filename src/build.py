"""
Build network

Builds the network with a backtracking algorithm and network measures defined in measures.py
"""

import random
from common import networkClasses, utility, constants
from analysis import powerLawReg
from numpy.random import shuffle
import bisect
from math import floor


def buildNetwork(config, targetNetwork):
    #allocate number of channels per node for new network
    initBuild(config, targetNetwork)
    newNodes = nodeDistribution(config, targetNetwork)
    # create nodes
    network = networkClasses.IncompleteNetwork(fullConnNodes=[], disconnNodes=newNodes, scalingUnits=constants.scalingUnits)
    # create channels
    gossipSequence = buildEdges(network)
    tempScids(config, network)
    # create capacity of channels
    capacityDistribution(config, network, targetNetwork)
    # write/save network to file
    buildNodeDetails(config, targetNetwork, network)
    return network, targetNetwork, gossipSequence


def initBuild(config, targetNetwork):
    if config.maxChannels == "default":
        maxChannelsPerNodeUnscaled = utility.getMaxChannels(targetNetwork)
        ratio = config.channelNum / targetNetwork.nodeNumber
        maxChannelsPerNode = int((ratio * maxChannelsPerNodeUnscaled) // 1)
        config.maxChannels = maxChannelsPerNode
    if config.maxFunding == "default":
        config.maxFunding = utility.getMaxNodeFunding(targetNetwork)


def initTargetNetwork(config, graph):
    fp = open(config.listchannelsFile, encoding="utf-8")
    jn = utility.loadJson(fp)
    targetNodes, targetChannels = utility.listchannelsJsonToObject(jn)
    targetNetwork = networkClasses.Network(fullConnNodes=targetNodes, scalingUnits=constants.scalingUnits)
    targetNetwork.channels = targetChannels
    #analyze snapshot of network
    targetNetwork.analysis.analyze(graph)
    return targetNetwork


def nodeDistribution(config, network):
    """
    Create a node distribution based on power law curve with params measured from regression analysis
    :param config: config
    :param network: network
    :return: node list
    """
    channelsToCreate = 2 * config.channelNum

    params = network.analysis.channelDistPowLawParams[0]
    nodes = []
    nodeidCounter = 0
    totalChannels = 0
    maxChannelsPerNode = config.maxChannels
    x = powerLawReg.randToPowerLaw(params, bound=(0, maxChannelsPerNode))
    while x > maxChannelsPerNode or x + totalChannels < channelsToCreate:
        x = round(x, 0)
        if x == 0 or x > maxChannelsPerNode:
            pass
        else:
            totalChannels += x
            n = networkClasses.Node(nodeidCounter, maxChannels=x)
            nodes += [n]
            nodeidCounter += 1
        x = powerLawReg.randToPowerLaw(params, bound=(0, maxChannelsPerNode))

    return nodes


def buildEdges(network):
    """
    build network at random by creating all channels for nodes from largest max channels to smallest max channels.
    Guarantee the network is completely connected by the end. 
    No duplicate channels are created between nodes.
    Gossip sequence is used to make load balancing in gossip.py more efficient
    :param network: network
    :return: gossip sequence
    """
    # connect first node to second node (to bootstrap network)
    if len(network.getNodes()) < 1:
        raise ValueError("Less than 2 nodes in network. Set --maxChannels to lower number or raise --channelNum")

    network.unfullNodes.sort(key=utility.channelMaxSortKey, reverse=True)
    usedLst = [[] for i in range(0, len(network.unfullNodes))]
    nodes = network.unfullNodes
    nodeidSortedNodes = network.unfullNodes.copy()
    nodeidSortedNodes.sort(key=utility.sortByNodeId)
    nodesLeft = nodeidSortedNodes.copy()
    ig = network.igraph
    ig.add_vertices(len(nodes))
    es = []
    gossipSequence = []
    done = False
    nodes[0].setInNetwork(inNetwork=True) #the first node is part of the network by default
    for node in nodes:
        nodeDone = False
        beforeBound = len(network.channels)
        if not node.isFull():
            channelsToCreate = node.maxChannels - node.channelCount
            disConnNodes = []
            for i in range(0, int(channelsToCreate)):
                if len(nodesLeft) <= 1:
                    done = True
                    break
                if len(usedLst[node.nodeid]) == (network.nodeNumber - 1):
                    break
                r = random.randint(0, len(nodesLeft)-1)
                nodeToConnect = nodesLeft[r]
                b = nodeToConnect.isFull()
                eq = node.nodeid == nodeToConnect.nodeid
                used = node.nodeid in usedLst[nodeToConnect.nodeid]
                disConn = False
                if i == (channelsToCreate - 1):  # for last channel to connect to, make sure node is in the network
                    if not node.isInNetwork() and not nodeToConnect.isInNetwork():
                        disConn = True
                j = 0
                while (disConn or b or eq or used) and not nodeDone and not done:
                    disConn = False
                    if b:
                        nodesLeft.pop(r)
                    elif eq:
                        nodesLeft.pop(r)
                    if used:
                        j += 1
                    if len(nodesLeft) <= 1:
                        done = True
                    elif j == 5:
                        k = 0
                        while k < len(nodesLeft):
                            nodeDone = True
                            n = nodesLeft[k]
                            b = nodeToConnect.isFull()
                            if b:
                                nodesLeft.pop(k)
                            else:
                                k += 1

                            if n.nodeid not in usedLst[node.nodeid] and (n.isInNetwork() or node.isInNetwork()) and not n.isFull() and node.nodeid != n.nodeid:
                                r = k
                                nodeToConnect = n
                                nodeDone = False
                                b = False
                                eq = False
                                used = False
                                break

                    else:
                        r = random.randint(0, len(nodesLeft) - 1)
                        nodeToConnect = nodesLeft[r]
                        b = nodeToConnect.isFull()
                        eq = node.nodeid == nodeToConnect.nodeid
                        used = node.nodeid in usedLst[nodeToConnect.nodeid]
                        if i == (channelsToCreate - 1): #for last channel to connect to, make sure node is in the network
                            if not node.isInNetwork() and not nodeToConnect.isInNetwork():
                                disConn = True
                                j += 1

                if not done and not nodeDone:
                    if node.isInNetwork() and not nodeToConnect.isInNetwork(): #curr node brings new node into the network
                        nodeToConnect.setInNetwork(inNetwork=True)
                    elif not node.isInNetwork() and not nodeToConnect.isInNetwork(): #new node and curr node remains disconnected from network
                        disConnNodes += [nodeToConnect]
                    elif not node.isInNetwork() and nodeToConnect.isInNetwork(): #all disconn nodes join the network
                        node.setInNetwork(True)
                        for n in disConnNodes:
                            n.setInNetwork(True)
                        disConnNodes = []
                    channel = network.createNewChannel(node, nodeToConnect)
                    usedLst[node.nodeid] += [nodeToConnect.nodeid]
                    usedLst[nodeToConnect.nodeid] += [node.nodeid]
                    es += [(node.nodeid, nodeToConnect.nodeid)]
                else:
                    break
            afterBound = len(network.channels)

            #record gossip sequence
            if beforeBound-afterBound == 0:
                pass
            else:
                gossipSequence += [(node.nodeid, (beforeBound, afterBound))]

            if done:
                break
    ig.add_edges(es)
    network.fullConnNodes = network.disconnNodes
    network.disconnNodes = []
    network.unfullNodes = []

    return gossipSequence



def tempScids(config, network):
    """
    Creates scids by calculating the starting height after coinbase blocks and spending coinbase blocks
    :param config: config
    :param network: network
    """
    scidHeight = 1
    scidTx = 1
    for i in range(0, len(network.channels)):
        chan = network.channels[i]
        chan.setScid(networkClasses.Scid(scidHeight, scidTx))
        scidHeight, scidTx = incrementScid(constants.maxTxPerBlock, scidHeight, scidTx)

def incrementScid(maxFundingTxPerBlock, height, tx):
    if tx == maxFundingTxPerBlock:
        tx = 1
        height += 1
    else:
        tx += 1

    return height, tx



def capacityDistribution(config, network, targetNetwork):
    """
    Set satoshis of each channel.
    Since regtest has low halving (every 150 blocks) the capacities have to be smaller than in the normal network.
    View the capacities as having the denomination of the units defined in constants.scalingUnits, rather than satoshis
    :param config: config
    :param network: network
    :param targetNetwork: target network
    """
    nodesByChans = nodeCapacityDistribution(config, network, targetNetwork)
    channelCapacities(targetNetwork, nodesByChans)


def nodeCapacityDistribution(config, network, targetNetwork):
    """
    Set capacity distribution of the network such that total capacity of nodes is a power law which is observed in the real network
    :param config: config
    :param network: network
    :param target network: snapshot of lightning network
    """

    nodeNum = len(network.getNodes())
    #start by generating a bunch of random capacities by generating random probs, and putting them in invert func
    #sort above list in reverse order, from largest cap to smallest
    capList = []
    params = targetNetwork.analysis.nodeCapacityInNetPowLawParams[0]
    interval = targetNetwork.analysis.nodeCapacityInNetPowLawParams[2]
    scaledMaxFunding = config.maxFunding/interval
    #defaultMinSatoshis = 1000000
    #scaledMinFunding = defaultMinSatoshis / interval 
    x = powerLawReg.randToPowerLaw(params, bound=(0, scaledMaxFunding))
    while len(capList) < nodeNum:
        # x cannot be greater than reward taking into acount the fees that will be spent in the transactions on chain.
        # We do this because coinbase outputs -> funding txs so max size of channel will be 50 BTC, which is a resonable maximum
        if (x > ((constants.coinbaseReward-config.fee)/interval)) or x == 0:
            continue
        else:
            satoshis = x * interval   #back to full satoshis
            bisect.insort_left(capList, satoshis)
        x = powerLawReg.randToPowerLaw(params, bound=(0, scaledMaxFunding))

    nodesByChans = network.getNodes().copy()
    nodesByChans.sort(key=utility.sortByChannelCount, reverse=False)
    #sort network in reverse order by number of channels
    for i in range (nodeNum-1, -1, -1):
        currCap = capList[i]
        currNode = nodesByChans[i]
        currNode.setUnallocated(currCap)
        currNode.setAllocation(currCap)
        currNode.channels.sort(key=currNode.getValueLeftOfOtherNode, reverse=True)
        nodes = swapFunc(.25, currNode.channels)   # a really gross hardcoded non-generalizable hack to help get the distribution correct. 

    return nodesByChans


def channelCapacities(targetNetwork, nodesByChans):
    """
    Set capacities of specific channels so that 2 properties are met: 
    (1) positive relationship between (other_node_cap-channel_cap)-->(channel_cap/node_cap) as observed in the snapshot/target network
    (2) power law between capacity distribution inside node as observed in the network
    :param targetNetwork: snapshot of lightning network
    :param network: network
    """

    nodeNum = len(nodesByChans)
    capPercent = targetNetwork.analysis.channelCapacityInNodeParams[1][2]
    rankingSize = targetNetwork.analysis.channelCapacityInNodeParams[2]
    begin = 0
    nodei = 0
    chani = 0  # index of channel in node. The ones before it already have capacities
    while begin < nodeNum:  # while there are still nodes that have channels left to create
        currNode = nodesByChans[nodei]

        # determine how many channels left to create
        if chani + 1 == currNode.channelCount:  # we wrap around sooner because another node is complete
            begin += 1

        chan = currNode.channels[chani]
        otherNode = currNode.getOtherNode(chan)
      
        if chan.value is None:
            if chani < rankingSize:
                per = capPercent[chani]
                newCap = int(round(per * currNode.allocation))
                chan.value = newCap
                otherNode.value += newCap
                currNode.value += newCap
            else:
                alloc = currNode.allocation
                cap = int(round(alloc / currNode.channelCount))
                currNode.value += cap
                otherNode.value += cap
                chan.value = cap

        if nodei == nodeNum - 1:
            nodei = begin
            chani += 1
        else:
            nodei += 1


def swapFunc(prob, lst):
    swaps = int(round(prob * len(lst)))
    for i in range(0, swaps):
        r1 = random.randint(0, swaps-1)
        r2 = random.randint(0, swaps-1)
        temp = lst[r1]
        lst[r1] = lst[r2]
        lst[r2] = temp
    return lst


def buildNodeDetails(config, targetNetwork, network):
    """
    Set addreses of nodes and set if the nodes will announce themselves
    :param targetNetwork: target
    :param config: config
    :param network: network
    """
    fp = open(config.listnodesFile, encoding="utf-8")
    jn = utility.loadJson(fp)
    targetNodesJson = utility.listnodesJsonToObject(jn)
    # filter out node announcements that don't correspond to any channel announcement
    matches = []
    for nodeJson in targetNodesJson:
        nodeid = nodeJson["nodeid"]
        for node in targetNetwork.fullConnNodes:
            if node.nodeid == nodeid:
                matches += [(nodeJson, node)]
                break
            else:
                continue

    # scan through node announcements and seperate them into type
    ipv4 = 0
    ipv6 = 0
    torv2 = 0
    torv3 = 0
    noAddr = 0
    noNodeAnnounce = len(targetNetwork.getNodes()) - len(matches)
    for na in matches:
        try:
            addrs = na[0]["addresses"]
            if len(addrs) == 0:
                noAddr += 1
            for addr in addrs:
                    t = addr["type"]
                    if t == "ipv4":
                        ipv4 += 1
                    elif t == "ipv6":
                        ipv6 += 1
                    elif t == "torv2":
                        torv2 += 1
                    elif t == "torv3":
                        torv3 += 1
        except KeyError:
            noNodeAnnounce += 1

    naLen = ipv4 + ipv6 + torv3 + torv2 + noAddr + noNodeAnnounce
    nodesCopy = network.getNodes().copy()
    nodeNum = len(nodesCopy)
    shuffle(nodesCopy)
    shuffledNodes = nodesCopy
    nextIPv4 = [127, 0, 0, 1, 38, 7]
    nextIPv6 = [254, 72, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 38, 7]    # fe48:: is private addr space for ipv6

    if config.addrTypes == "all":
        ipv4NodeNum = floor((ipv4/naLen)*nodeNum)
        ipv6NodeNum = floor((ipv6/naLen)*nodeNum)
        torv2NodeNum = floor((torv2/naLen)*nodeNum)
        torv3NodeNum = floor((torv3/naLen)*nodeNum)
        noAddr = floor((noAddr/naLen)*nodeNum)

        i = 0
        for j in range (i, ipv4NodeNum):
            currIPV4 = nextIPv4
            node = shuffledNodes[j]
            node.setAddrType("ipv4")
            node.setAnnounce(True)
            node.addrList += [bytearray(currIPV4)]
            nextIPv4 = getNextIPv4(currIPV4)
        i += ipv4NodeNum
        for j in range (i, i+ipv6NodeNum):
            currIPv6 = nextIPv6
            node = shuffledNodes[j]
            node.setAddrType("ipv6")
            node.setAnnounce(True)
            node.addrList += [bytearray(currIPv6)]
            nextIPv6 = getNextIPv6(currIPv6)
        i += ipv6NodeNum
        for j in range (i, i+torv2NodeNum):
            node = shuffledNodes[j]
            node.setAddrType("torv2")
            node.setAnnounce(True)
            node.addrList += [bytearray(getRandomTor(v=2))]
        i += torv2NodeNum
        for j in range (i, i+torv3NodeNum):
            node = shuffledNodes[j]
            node.setAddrType("torv3")
            node.setAnnounce(True)
            node.addrList += [bytearray(getRandomTor(v=3))]
        i += torv3NodeNum
        for j in range (i, i+noAddr):
            node = shuffledNodes[j]
            node.setAddrType(None)
            node.setAnnounce(True)
        i += noAddr
        for j in range (i, len(shuffledNodes)):
            node = shuffledNodes[j]
            node.setAddrType(None)
            node.setAnnounce(False)
    elif config.addrTypes == "ipv4":
        for i in range (0, len(network.getNodes())):
            currIPv4 = nextIPv4
            node = network.getNodes()[i]
            node.setAddrType("ipv4")
            node.setAnnounce(True)
            node.addrList += [bytearray(currIPv4)]
            nextIPv4 = getNextIPv4(currIPv4)


    setChannelsToAnnounceNodes(shuffledNodes)


def getNextIPv4(ipv4):
    """
    :param ipv4: 6 elements in a list: first 4 are ip and last 2 are port
    :return:
    """
    for i in range(3, 0, -1):
        if ipv4[i] == 255:
            ipv4[i] = 0
        else:
            ipv4[i] += 1
            break

    return ipv4

def getNextIPv6(ipv6):
    """
    :param ipv6: 18 elements, first 16 are ip, last 2 are port
    :return:
    """
    for i in range(15, 1, -1):
        if ipv6[i] == 255:
            ipv6[i] = 0
        else:
            ipv6[i] += 1
            break
    return ipv6


def getRandomTor(v):
    port = [38, 7]  # 9735 in decimal
    if v == 2:
        addr = [random.randint(0, 255) for i in range(0, 10)]
        return addr + port
    elif v == 3:
        addr = [random.randint(0, 255) for i in range(0, 35)]
        return addr + port


def setChannelsToAnnounceNodes(nodes):
    for node in nodes:
        if node.announce:
            node.channels[0].setNodeToWrite(node)


def setAllChannelsDefaultValue(network, value):
    """
    This is a temporary function that simply sets each channel to the same default value
    :param network: network
    :param value: value
    """
    for channel in network.channels:
        channel.value = value
