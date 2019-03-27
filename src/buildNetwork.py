"""
Build network

Builds the network with a backtracking algorithm and network measures defined in measures.py
"""

import random
from common import networkClasses
from common import utility
from analysis import powerLawReg, fundingReg
import chain
from numpy.random import shuffle
import bisect


def buildNetwork(config):
    #load snapshot of network
    fp = open(config.listchannelsFile, encoding="utf-8")
    jn = utility.loadJson(fp)
    targetNodes, targetChannels = utility.listchannelsJsonToObject(jn)
    targetNetwork = networkClasses.Network(fullConnNodes=targetNodes)
    targetNetwork.channels = targetChannels
    #analyze snapshot of network
    targetNetwork.analysis.analyze()
    utility.setRandSeed(config.randSeed)
    #allocate number of channels per node for new network
    if config.maxChannels == "default":
        maxChannelsPerNodeUnscaled = getMaxChannels(targetNetwork)
        ratio = config.channelNum / targetNetwork.nodeNumber
        maxChannelsPerNode = int((ratio * maxChannelsPerNodeUnscaled) // 1)
        config.maxChannels = maxChannelsPerNode
    if config.maxFunding == "default":
        config.maxFunding = getMaxNodeFunding(targetNetwork)
    newNodes = nodeDistribution(config, targetNetwork)   # eventually a config command can turn on and off the rand dist
    network = networkClasses.IncompleteNetwork(fullConnNodes=[], disconnNodes=newNodes)
    # create channels
    gossipSequence = buildEdges(network)
    # create capacity of channels
    capacityDistribution(config, network, targetNetwork)
    scids(config, network)
    # create details of nodes
    buildNodeDetails(config, targetNetwork, network)
    utility.writeNetwork(network, gossipSequence, config.nodesFile, config.channelsFile)
    return network, targetNetwork, gossipSequence



def scids(config, network):
    """
    Creates scids by calculating the starting height after coinbase blocks and spending coinbase blocks
    :param config: config
    :param network: network
    :return:
    """
    chanBlocks = chain.blocksCoinbaseSpends(config, network.channels)
    coinbaseBlocksNum = chain.getNumBlocksToMine(chanBlocks)         # blocks to mine to fund the txs in the blockchain
    scidHeight = coinbaseBlocksNum + len(chanBlocks) + config.confirmations  # blocks to create coinbase + blocks to spend coinbases + 6 confirmations
    scidTx = 1

    for i in range(0, len(network.channels)):
        chan = network.channels[i]
        chan.setScid(networkClasses.Scid(scidHeight, scidTx))
        scidHeight, scidTx = incrementScid(config.maxTxPerBlock, scidHeight, scidTx)


def getMaxChannels(targetNetwork):
    maxC = 0
    for n in targetNetwork.getNodes():
        if n.maxChannels > maxC:
            maxC = n.maxChannels
    return maxC


def getMaxNodeFunding(targetNetwork):
    maxF = 0
    for n in targetNetwork.getNodes():
        if n.value > maxF:
            maxF = n.value
    return maxF

def buildEdges(network):
    """
    build network by creating all channels for nodes from largest max channels to smallest max channels.
    No duplicate channels are created between nodes.
    :param network: network
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


def incrementScid(maxFundingTxPerBlock, height, tx):
    """
    this will change in the future when 
    """
    if tx == maxFundingTxPerBlock:
        tx = 1
        height += 1
    else:
        tx += 1

    return height, tx


def nodeDistribution(config, network):
    """
    There are two ways to choose the distribution of nodes. We can use randomness based on randint and the prob curve
    or we can create nodes exactly with the percentage of the prob curve.
    :param finalNumChannels: channels to create in the network
    :param randSeed: rand seedchannel
    :param randomDist: if True, we generate with randint. Otherwise generate proportionally.
    :return: node list
    """
    channelsToCreate = 2 * config.channelNum

    params = network.analysis.channelDistPowLawParams[0]
    nodes = []
    nodeidCounter = 0
    totalChannels = 0
    x = powerLawReg.randToPowerLaw(params)
    maxChannelsPerNode = config.maxChannels
    while x > maxChannelsPerNode or x + totalChannels < channelsToCreate:
        if x == 0 or x > maxChannelsPerNode:
            pass
        else:
            totalChannels += x
            n = networkClasses.Node(nodeidCounter, maxChannels=x)
            nodes += [n]
            nodeidCounter += 1
        x = powerLawReg.randToPowerLaw(params)

    return nodes

def capacityDistribution(config, network, targetNetwork):

    nodeNum = len(network.getNodes())
    #start by generating a bunch of random capacities by generating random probs, and putting them in invert func
    #sort above list in reverse order, from largest cap to smallest
    capList = []
    params = targetNetwork.analysis.nodeCapacityInNetPowLawParams[0]
    interval = targetNetwork.analysis.nodeCapacityInNetPowLawParams[2]
    scaledMaxFunding = config.maxFunding/interval
    while len(capList) < nodeNum:
        x = powerLawReg.randToPowerLaw(params)
        while x == 0 or x > scaledMaxFunding:
            x = powerLawReg.randToPowerLaw(params)
        xSatoshis = round(x * interval)
        bisect.insort_left(capList, xSatoshis)

    #TODO do swapping in list to make it more random but for the most part sorted from greatest to least

    #sort network in reverse order by number of channels
    nodesByChans = network.getNodes().copy()
    nodesByChans.sort(key=utility.sortByChannelCount, reverse=False)

    #assign each node in reverse order a capacity in the order of the semi sorted list
    for i in range (nodeNum-1, -1, -1):
        currCap = capList[i]
        currNode = nodesByChans[i]
        currNode.setUnallocated(currCap)
        currNode.setAllocation(currCap)
        currNode.channels.sort(key=currNode.getValueLeftOfOtherNode, reverse=True)

    capPercent = targetNetwork.analysis.channelCapacityInNodeParams[1][2]
    rankingSize = targetNetwork.analysis.channelCapacityInNodeParams[2]
    begin = 0
    nodei = 0
    chani = 0 #index of channel in node. The ones before it already have capacities
    defaultMinSatoshis = 1000
    while begin < nodeNum: #while there are still nodes that have channels left to create
        currNode = nodesByChans[nodei]

        # determine how many channels left to create

        if chani+1 == currNode.channelCount: #we wrap around sooner because another node is complete
            begin += 1

        chan = currNode.channels[chani]

        if chan.value is None:
            if chani < rankingSize: #we choose based on linear reg
                per = capPercent[chani]
                alloc = currNode.allocation
                newCap = round(per*alloc)
                chan.value = newCap
                otherNode = currNode.getOtherNode(chan)
                otherNode.unallocated -= newCap
                otherNode.value += newCap
                currNode.unallocated -= newCap
                currNode.value += newCap
            else:   # we finish off node by randomly allocating rest of channels with even split of rest of capacity
                otherNode = currNode.getOtherNode(chan)
                otherUnalloc = otherNode.unallocated
                unalloc = currNode.unallocated
                chansLeft = currNode.channelCount - chani
                avgCap = unalloc / chansLeft
                if unalloc <= 0 or otherUnalloc <= 0:
                    chan.value = defaultMinSatoshis
                    otherNode.unallocated -= defaultMinSatoshis
                    otherNode.value += defaultMinSatoshis
                    currNode.unallocated -= defaultMinSatoshis
                    currNode.value += defaultMinSatoshis
                elif otherUnalloc - avgCap <= 0:
                    chan.value = otherUnalloc
                    otherNode.unallocated -= otherUnalloc
                    otherNode.value += otherUnalloc
                    currNode.unallocated -= otherUnalloc
                    currNode.value += otherUnalloc
                else:
                    chan.value = avgCap
                    otherNode.unallocated -= avgCap
                    otherNode.value += avgCap
                    currNode.unallocated -= avgCap
                    currNode.value += avgCap

        if nodei == nodeNum - 1:
            nodei = begin
            chani += 1
        else:
            nodei += 1

    #for each node, order channels by
    pass



def buildNodeDetails(config, targetNetwork, network=None):
    """
    :param targetNetwork:
    :param config:
    :param network:
    :return:
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
    noNodeAnnounce = 0
    naLen = len(matches)
    for na in matches:
        try:
            addrs = na[0]["addresses"]
            if len(addrs) == 0:
                noAddr += 1
            else:
                t = addrs[0]["type"]
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

    nodesCopy = network.fullConnNodes.copy()
    nodeNum = len(nodesCopy)
    shuffle(nodesCopy)
    shuffledNodes = nodesCopy

    ipv4NodeNum = round((ipv4/naLen)*nodeNum)
    ipv6NodeNum = round((ipv6/naLen)*nodeNum)
    torv2NodeNum = round((torv2/naLen)*nodeNum)
    torv3NodeNum = round((torv3/naLen)*nodeNum)
    noAddr = round((noAddr/naLen)*nodeNum)

    i = 0
    for j in range (i, ipv4NodeNum):
        node = shuffledNodes[j]
        node.setAddrType("ipv4")
        node.setAnnounce(True)
    i += ipv4NodeNum
    for j in range (i, ipv6NodeNum):
        node = shuffledNodes[j]
        node.setAddrType("ipv6")
        node.setAnnounce(True)
    i += ipv6NodeNum
    for j in range (i, torv2NodeNum):
        node = shuffledNodes[j]
        node.setAddrType("torv2")
        node.setAnnounce(True)
    i += torv2NodeNum
    for j in range (i, torv3NodeNum):
        node = shuffledNodes[j]
        node.setAddrType("torv3")
        node.setAnnounce(True)
    i += torv3NodeNum
    for j in range (i, noAddr):
        node = shuffledNodes[j]
        node.setAddrType(None)
        node.setAnnounce(True)
    i += noAddr
    for j in range (i, len(shuffledNodes)):
        node = shuffledNodes[j]
        node.setAddrType(None)
        node.setAnnounce(False)


def setAllChannelsDefaultValue(network, value):
    """
    This is a temporary function that simply sets each channel to the same default value
    :param network: network
    :param value: value
    """
    for channel in network.channels:
        channel.value = value
