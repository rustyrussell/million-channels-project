"""
Build network

Builds the network with a backtracking algorithm and network measures defined in measures.py
"""

import random
from common import networkClasses
from common import utility
import powerLawReg
import time
from config import *
import igraph


def main():
    fp = open(powerLawReg.channelFileName)
    t0 = time.time()
    jn = utility.loadJson(fp)
    t1 = time.time()
    print("json load complete", t1-t0)
    nodes, channels= utility.jsonToObject(jn)
    t0 = time.time()
    targetNetwork = networkClasses.Network(fullConnNodes=nodes)
    targetNetwork.channels = channels
    targetNetwork.analysis.analyze()
    utility.setRandSeed(randSeed)
    newNodes = nodeDistribution(targetNetwork, finalNumChannels)   # eventually a config command can turn on and off the rand dist
    t1 = time.time()
    print("nodeDistribution done", t1-t0)
    network = networkClasses.IncompleteNetwork(fullConnNodes=[], disconnNodes=newNodes)
    t2 = time.time()
    buildNetworkFast(network)
    t3 = time.time()
    print("buildNetworkFast", t3-t2)
    utility.writeCompactNetwork(network, channelSaveFile)
    draw(network.igraph)

def buildNetworkFast(network):
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
    n = 0
    done = False
    for node in nodes:
        if node.isFull():
            continue
        channelsToCreate = node.maxChannels - node.channelCount
        for i in range(0, int(channelsToCreate)):
            if len(nodesLeft) - 1 == 0:
                done = True
                break
            r = random.randint(0, len(nodesLeft)-1)
            nodeToConnect = nodesLeft[r]
            nodeToConnectId = nodeToConnect.nodeid
            b = nodeToConnect.isFull()
            eq = node.nodeid == nodeToConnectId
            j = 0
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
                if j == 100:
                    j = 0
                j += 1
            channel = network.createNewChannel(node, nodeToConnect)
            usedLst[node.nodeid] += [nodeToConnectId]
            usedLst[nodeToConnectId] += [node.nodeid]
            es += [(node.nodeid, nodeToConnectId)]
        print("done with", n)
        n += 1
        if done:
            break
    ig.add_edges(es)


def nodeDistribution(network, finalNumChannels):
    """
    There are two ways to choose the distribution of nodes. We can use randomness based on randint and the prob curve
    or we can create nodes exactly with the percentage of the prob curve.
    :param finalNumChannels: channels to create in the network
    :param randSeed: rand seed
    :param randomDist: if True, we generate with randint. Otherwise generate proportionally.
    :return: node list
    """
    params = network.analysis.powerLaw[0]
    nodes = []
    a,b,c = params[0],params[1],params[2]
    nodeidCounter = 0
    totalChannels = 0
    pMax = powerLawReg.powerLawFuncC([1], a, b, c)[0]
    r = random.uniform(0, pMax)
    x = powerLawReg.inversePowLawFuncC([r], a, b, c)[0]
    channelsForNode = round(x, 0)
    while channelsForNode > powerLawReg.maxChannelsPerNode:
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
        while channelsForNode > powerLawReg.maxChannelsPerNode:
            x = powerLawReg.inversePowLawFuncC([r], a, b, c)
            channelsForNode = round(x, 0)
        totalChannels += channelsForNode

    return nodes


def draw(ig, bbox=(0,0,2000,2000)):
    """
    draw graph using igraph obj
    :param ig: igraph obj
    :return:
    """
    igraph.drawing.plot(ig, bbox=bbox)


assert(checkBuildNetworkFields()==True)
if __name__ == "__main__":
    main()
