"""
Build network

Builds the network with a backtracking algorithm and network measures defined in measures.py
"""

import random
from common import networkClasses
from common import utility
from analysis import  powerLawReg
import time
import igraph


def main(channelNum, maxChannelsPerNode, defaultValue, analysisFile, nodeSaveFile, channelSaveFile, randSeed):
    fp = open(analysisFile)
    t0 = time.time()
    jn = utility.loadJson(fp)
    t1 = time.time()
    print("json load complete", t1-t0)
    nodes, channels = utility.jsonToObject(jn)
    t0 = time.time()
    targetNetwork = networkClasses.Network(fullConnNodes=nodes)
    targetNetwork.channels = channels
    targetNetwork.analysis.analyze()
    utility.setRandSeed(randSeed)
    newNodes = nodeDistribution(targetNetwork, channelNum, maxChannelsPerNode)   # eventually a config command can turn on and off the rand dist
    t1 = time.time()
    print("nodeDistribution done", t1-t0)
    network = networkClasses.IncompleteNetwork(fullConnNodes=[], disconnNodes=newNodes)
    t2 = time.time()
    gossipSequence = buildNetworkFast(network, maxChannelsPerNode)
    t3 = time.time()
    print("buildNetworkFast", t3-t2)
    t4 = time.time()
    setAllChannelsDefaultValue(network, defaultValue);
    generateScids(network);
    #generateChanValues(network);
    utility.writeNetwork(network, gossipSequence, nodeSaveFile, channelSaveFile)
    return network, gossipSequence    

def buildNetworkFast(network, maxChannelsPerNode):
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
    scidBlock = 1
    scidTx = 1
    for node in nodes:
        beforeBound = len(network.channels)
        if node.isFull():
            pass
        else:
            channelsToCreate = node.maxChannels - node.channelCount
            for i in range(0, int(channelsToCreate)):
                if len(nodesLeft) - 1 == 0:
                    done = True
                    break
                if len(usedLst[node.nodeid]) == (len(nodesLeft) - 1):  #if all nodes left are already connected to, go to the next node
                    break
                r = random.randint(0, len(nodesLeft)-1)
                nodeToConnect = nodesLeft[r]
                nodeToConnectId = nodeToConnect.nodeid
                b = nodeToConnect.isFull()
                eq = node.nodeid == nodeToConnectId
                while b or eq or node.nodeid in usedLst[nodeToConnectId]:
                    if b:
                        nodesLeft.pop(r)
                    if eq:
                        nodesLeft.pop(r)
                    if len(nodesLeft)-1 == 0:
                        done = True
                        break
                    r = random.randint(0, len(nodesLeft) - 1)
                    nodeToConnect = nodesLeft[r]
                    nodeToConnectId = nodeToConnect.nodeid
                    b = nodeToConnect.isFull()
                    eq = node.nodeid == nodeToConnectId
                channel = network.createNewChannel(node, nodeToConnect)
                channel.setScid(utility.getScid(scidBlock, scidTx))
                scidBlock, scidTx = incrementScid(scidBlock, scidTx, maxChannelsPerNode)
                usedLst[node.nodeid] += [nodeToConnectId]
                usedLst[nodeToConnectId] += [node.nodeid]
                es += [(node.nodeid, nodeToConnectId)]
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
    x = powerLawReg.inversePowLawFuncC([r], a, b, c)[0]
    channelsForNode = round(x, 0)
    while channelsForNode > maxChannelsPerNode:
        x = powerLawReg.inversePowLawFuncC([r], a, b, c)
        channelsForNode = round(x, 0)
    totalChannels += channelsForNode

    while totalChannels < finalNumChannels:     # this is why I wish python had do-while statements!!!
        n = networkClasses.Node(nodeidCounter, maxChannels=channelsForNode)
        nodes += [n]
        nodeidCounter += 1
        r = random.uniform(0, pMax)
        x = powerLawReg.inversePowLawFuncC([r], a, b, c)[0]
        channelsForNode = round(x, 0)
        while channelsForNode > maxChannelsPerNode:
            x = powerLawReg.inversePowLawFuncC([r], a, b, c)
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
        channel.value = value;


def generateScids(network):

    pass

def draw(ig, bbox=(0,0,2000,2000)):
    """
    draw graph using igraph obj
    :param ig: igraph obj
    :return:
    """
    ig.vs["label"] = ig.vs.indices
    igraph.drawing.plot(ig, bbox=bbox)
