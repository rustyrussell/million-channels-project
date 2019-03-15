"""
Build network

Builds the network with a backtracking algorithm and network measures defined in measures.py
"""

import random
from common import networkClasses
from common import utility
from analysis import powerLawReg, fundingReg
import time
from numpy.random import shuffle


def buildNetwork(config):
    fp = open(config.listchannelsFile)
    t0 = time.time()
    jn = utility.loadjson(fp)
    t1 = time.time()
    print("json load complete", t1-t0)
    targetNodes, targetChannels = utility.listchannelsJsonToObject(jn)
    t0 = time.time()
    targetNetwork = networkClasses.Network(fullConnNodes=targetNodes)
    targetNetwork.channels = targetChannels
    targetNetwork.analysis.analyze()
    utility.setRandSeed(config.randSeed)
    newNodes = nodeDistribution(targetNetwork, config.channelNum, config.maxChannelsPerNode)   # eventually a config command can turn on and off the rand dist
    t1 = time.time()
    print("nodeDistribution done", t1-t0)
    network = networkClasses.IncompleteNetwork(fullConnNodes=[], disconnNodes=newNodes)
    t2 = time.time()
    gossipSequence = buildEdges(network, config.maxChannelsPerNode)
    t3 = time.time()
    print("buildNetworkFast", t3-t2)

    buildNodeDetails(targetNetwork, config, network)
    #buildChannelDetails(targetNetwork, config)
    utility.writeNetwork(network, gossipSequence, config.nodeSaveFile, config.channelSaveFile)
    return network, targetNetwork, gossipSequence



def buildNodeDetails(targetNetwork, config, network=None):
    """
    :param targetNetwork:
    :param config:
    :param network:
    :return:
    """
    fp = open(config.listnodesFile)
    jn = utility.loadjson(fp)
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

def buildChannelDetails(targetNetwork, config, network=None):   #TODO add network as param

    # run funding reg
    # channels that connect hubs are set to high capacity as determined by funding reg
    # for the rest of the channels, find channel on reg line and

    params = targetNetwork.analysis.fundingReg


    return


def buildEdges(network, maxChannelsPerNode):
    """
    build network by creating all channels for nodes from largest max channels to smallest max channels.
    No duplicate channels are created between nodes.
    :param network: network
    """
    # connect first node to second node (to bootstrap network)
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
    scidHeight = 101 #first 100 blocks are only coinbase
    scidTx = 1
    nodes[0].setInNetwork(inNetwork=True) #the first node is part of the network by default
    for node in nodes:
        nodeDone = False
        beforeBound = len(network.channels)
        if not node.isFull():
            channelsToCreate = node.maxChannels - node.channelCount
            disConnNodes = []
            for i in range(0, int(channelsToCreate)):
                if len(nodesLeft) - 1 == 0:
                    done = True
                    break
                # if len(usedLst[node.nodeid]) == (len(nodesLeft) - 1):  #if all nodes left are already connected to, go to the next node  #FIXME
                #     break
                r = random.randint(0, len(nodesLeft)-1)
                nodeToConnect = nodesLeft[r]
                nodeToConnectId = nodeToConnect.nodeid
                b = nodeToConnect.isFull()
                eq = node.nodeid == nodeToConnectId
                used = node.nodeid in usedLst[nodeToConnectId]
                disConn = False
                if i == (channelsToCreate - 1):  # for last channel to connect to, make sure node is in the network
                    if not node.isInNetwork() and not nodeToConnect.isInNetwork():
                        disConn = True
                j = 0
                while (disConn or b or eq or used) and not nodeDone and not done:
                    disConn = False
                    if b:
                        nodesLeft.pop(r)
                    if eq:
                        nodesLeft.pop(r)
                    if used:
                        j += 1
                    if len(nodesLeft)-1 == 0:
                        done = True
                    elif j == 5:
                        for n in nodesLeft:
                            nodeDone = True
                            if n.nodeid not in usedLst[node.nodeid] and n.isInNetwork():
                                nodeToConnect = n
                                nodeDone = False
                                break
                    else:
                        r = random.randint(0, len(nodesLeft) - 1)
                        nodeToConnect = nodesLeft[r]
                        nodeToConnectId = nodeToConnect.nodeid
                        b = nodeToConnect.isFull()
                        eq = node.nodeid == nodeToConnectId
                        used = node.nodeid in usedLst[nodeToConnectId]
                        if i == (channelsToCreate - 1): #for last channel to connect to, make sure node is in the network
                            if not node.isInNetwork() and not nodeToConnect.isInNetwork():
                                disConn = True
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
                    channel.setScid(utility.getScid(scidHeight, scidTx))
                    scidHeight, scidTx = incrementScid(scidHeight, scidTx, maxChannelsPerNode)
                    usedLst[node.nodeid] += [nodeToConnectId]
                    usedLst[nodeToConnectId] += [node.nodeid]
                    es += [(node.nodeid, nodeToConnectId)]
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


def incrementScid(height, tx, maxChannelsPerNode):
    """
    this will change in the future when 
    """
    maxFundingTxPerBlock = 1023
    if tx == maxFundingTxPerBlock:
        tx = 1
        height += 1
    elif tx < maxChannelsPerNode:
        tx += 1
    else:
        raise ValueError("incrementScid: tx cannot be greater than ", str(maxFundingTxPerBlock))
    return height, tx

def nodeDistribution(network, finalNumChannels, maxChannelsPerNode):
    """
    There are two ways to choose the distribution of nodes. We can use randomness based on randint and the prob curve
    or we can create nodes exactly with the percentage of the prob curve.
    :param finalNumChannels: channels to create in the network
    :param randSeed: rand seedchannel
    :param randomDist: if True, we generate with randint. Otherwise generate proportionally.
    :return: node list
    """
    channelsToCreate = 2 * finalNumChannels

    params = network.analysis.powerLaw[0]
    nodes = []
    a,b,c = params[0],params[1],params[2]
    nodeidCounter = 0
    totalChannels = 0
    pMax = powerLawReg.powerLawFuncC([1], a, b, c)[0]
    r = random.uniform(0, pMax)
    # r = random.uniform(0, 1)
    x = powerLawReg.inversePowLawFuncC([r], a, b, c)[0]
    channelsForNode = round(x, 0)
    while channelsForNode > maxChannelsPerNode or channelsForNode < 1:
        r = random.uniform(0, pMax)
        # r = random.uniform(0, 1)
        x = powerLawReg.inversePowLawFuncC([r], a, b, c)[0]
        channelsForNode = round(x, 0)
    totalChannels += channelsForNode

    while totalChannels < channelsToCreate:     # this is why I wish python had do-while statements!!!
        n = networkClasses.Node(nodeidCounter, maxChannels=channelsForNode)
        nodes += [n]
        nodeidCounter += 1
        r = random.uniform(0, pMax)
        # r = random.uniform(0, 1)
        x = powerLawReg.inversePowLawFuncC([r], a, b, c)[0]
        channelsForNode = round(x, 0)
        while channelsForNode > maxChannelsPerNode or channelsForNode < 1:
            r = random.uniform(0, pMax)
            # r = random.uniform(0, 1)
            x = powerLawReg.inversePowLawFuncC([r], a, b, c)[0]
            channelsForNode = round(x, 0)
        totalChannels += channelsForNode

    return nodes


def setAllChannelsDefaultValue(network, value):
    """
    This is a temporary function that simply sets each channel to the same default value
    :param network: network
    :param value: value
    """
    for channel in network.channels:
        channel.value = value


def generateScids(network):
    pass

