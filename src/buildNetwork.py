"""
Build network

Builds the network with a backtracking algorithm and network measures defined in measures.py
"""

import random
from common import networkClasses
from common import utility
import powerLawReg
#from graph import graph
import pickle
import time
from config import *
import bisect



#functions

def main():
    ti = time.time()
    fp = open(powerLawReg.channelFileName)
    jn = utility.loadJson(fp)
    nodes, channels= utility.jsonToObject(jn)
    t0 = time.time()
    print("load json done", t0-ti)
    targetNetwork = networkClasses.Network(fullConnNodes=nodes)
    targetNetwork.channels = channels
    targetNetwork.analysis.analyze()
    utility.setRandSeed(randSeed)
    newNodes = nodeDistribution(targetNetwork, finalNumChannels)   # eventually a config command can turn on and off the rand dist
    t1 = time.time()
    print("nodeDistribution done", t1-t0)
    incompleteNetwork = networkClasses.IncompleteNetwork(fullConnNodes=[], disconnNodes=newNodes)
    t2 = time.time()
    newNetwork = buildNetwork(targetNetwork, incompleteNetwork)
    t3 = time.time()
    print("print build network done", t3-t2)
    print("num of channels", len(newNetwork.channels))
    t4 = time.time()
    newbsAvg = newNetwork.analysis.betweenness()
    t5 = time.time()
    print("new betweenness (", str(t5-t4), ")", newbsAvg)
    g = utility.makeigraphTargetNetwork(nodes, channels)
    targetNetwork.igraph = g
    t6 = time.time()
    orgbsAvg = targetNetwork.analysis.betweenness()
    t7 = time.time()
    print("original betweenness (", str(t7-t6), ")", orgbsAvg)

    #graph.graph_tool(newNetwork, str(finalNumChannels) + "network_2_21_shortestpath_~500_10can_1round<")
    f = open(networkSaveFile, "wb")
    pickle.dump(newNetwork, f)




def buildNetwork(targetNetwork, incompleteNetwork):
    """
    iterative algorithm for creating the network. The algorithm works as follows:
    1. go through each node from largest maxChannels to smallest maxChannels
    2. create 1 channel for each node for a certain amount of nodes per round (say 10).
    3. if the node has already reached its max channel limit, move on to the next node
    4. the 1 channel is chosen out of a sequence of candidate channels (say 3 candidates)
    5. we backtrack by trying all permutations of candidate channels for nodes. (say 3^10)
    6. each round has a final "best" output of nodes with channels that is carried onto the next round.
    7. the channel candidates are produced by the parameters the checkpoint creates
    8. the checkpoint creates parameters after each round
    :param nodes:
    :return: bestNetwork
    """

    # connect first node to second node (to bootstrap network)
    incompleteNetwork.unfullNodes.sort(key=utility.channelMaxSortKey, reverse=False)
    node1 = incompleteNetwork.popUnfull()
    node2 = incompleteNetwork.popUnfull()
    incompleteNetwork.pushUnfull(node1)
    incompleteNetwork.pushUnfull(node2)
    startingChannel = networkClasses.Channel(node1, node2)
    applyStateChanges(incompleteNetwork, [startingChannel])
    incompleteNetwork.addChannels([startingChannel])
    currNetwork = incompleteNetwork

    j = 1
    k = 1
    t100 = time.time()
    while len(currNetwork.unfullNodes) > 1:    #implicitly (totalChannels + channelsPerRound) <= finalNumChannels
        t0 = time.time()
        stateChanges, changeAnalysis, currChanges = roundRec(currNetwork, {}, [], [], [None,None,None], 0, 0)
        t1 = time.time()
        #print("bench roundRec:", t1-t0)
        t2 = time.time()
        applyStateChanges(currNetwork, stateChanges)
        t3 = time.time()
        #print("bench applyStateChanges:", t3-t2)
        #testing
        if j == 100:
            t100end = time.time()
            print("channel created:", k*100*channelsPerRound, t100end-t100)
            k += 1
            j = 1
            t100 = time.time()
        j += 1
        #testing

    return currNetwork


def applyStateChanges(network, channels):
    """
    once the ideal channel list is created, we apply it and finalize it here
    :param network: incomplete Network
    :param channels: channel list
    :return:
    """
    network.addChannels(channels)

    for c in channels:
        node1 = c.node1
        node2 = c.node2
        network.createNewChannel(node1, node2, temp=False)

    for i in range(0, len(channels)):
        network.pushUnfull(network.popUnfull())

    network.partConnNodes = []
    network.disconnNodes = []
    newUnfull = []
    for node in network.unfullNodes:
        if node.isFull():
            network.fullConnNodes += [node]
        elif node.channelCount == 0:
            network.disconnNodes += [node]
            newUnfull += [node]
        else:
            network.partConnNodes += [node]
            newUnfull += [node]
    network.unfullNodes = newUnfull




def roundRec(network, changeDict, currChanges, bestChanges, bestChangesAnalysis, i, t):
    """
    Backtracks though every permutation (channelsPerRound^candidateNumber permutations)
    :param nodes:
    :param startingIndex:
    :param params:
    :param i: 0-channelsPerRound-1
    :param j: 0-candidates-1
    :return:
    """
    nodes = network.unfullNodes
    currNode = None
    candidates = 0
    if len(nodes) > 0:
        currNode = network.popUnfull()    #pop from queue
        network.pushUnfull(currNode)
        t0 = time.time()
        candidates = generateCandidates(network, currNode)
        t1 = time.time()
        #print("bench generateCandidates", t1 - t0)

    if i == channelsPerRound or len(nodes) <= 1 or len(candidates) == 0:  # if rounds complete or no more unfull nodes or no candidates
        t0 = time.time()
        bestChanges, bestChangesAnalysis = checkpointFunction(network, changeDict, currChanges, bestChanges, bestChangesAnalysis)
        t1 = time.time()
        #print("bench checkpoint", t1-t0)
        return bestChanges, bestChangesAnalysis, currChanges

    for c in range(0, len(candidates)):
        other = candidates[c]   #cand c
        addChangeDict(changeDict, currNode, other)  # must happen before add channel
        t0 = time.time()
        channel = network.createNewChannel(currNode, other, temp=True)    # create temp channel (meaning don't add to nodes' channel lists)
        t1 = time.time()
        #print("bench createNewChannel", t1 - t0)
        currChanges += [channel] # add channel to current changes
        bestChanges, bestChangesAnalysis, currChanges = roundRec(network, changeDict, currChanges, bestChanges, bestChangesAnalysis, i+1, t)
        currChanges = currChanges[0:-1] # delete the last change
        t0 = time.time()
        network.removeChannel(channel, temp=True) # reverse previous temp channel add
        t1 = time.time()
        #print("bench removeChannel", t1 - t0)
        removeChangeDict(changeDict, currNode, other) # must happen after remove channel

    return bestChanges, bestChangesAnalysis, currChanges


def addChangeDict(changeDict, currNode, other):
    """
    Change dict tracks when nodes are added to the network.
    :param changeDict:
    :param currNode:
    :param other:
    :return:
    """
    if not currNode.inNetwork():
        changeDict[str(currNode.nodeid)] = True
    else:
        changeDict[str(currNode.nodeid)] = False
    if not other.inNetwork():
        changeDict[str(other.nodeid)] = True
    else:
        changeDict[str(other.nodeid)] = False


def removeChangeDict(changeDict, currNode, other):
    """
    Set to false is node falls out of network
    :param changeDict:
    :param currNode:
    :param other:
    :return:
    """
    if not currNode.inNetwork():
        changeDict[str(currNode.nodeid)] = False
    if not other.inNetwork():
        changeDict[str(other.nodeid)] = False


def generateCandidates(network, node):
    """
    Generates candidateNumber number of candidates for backtracking
    :param network
    :param node
    :return: cand list
    """
    #get node list to select from
    if node.inNetwork():
        nodes = network.disconnNodes + network.partConnNodes
    else:
        nodes = network.partConnNodes
    nodesToSelectFrom = []
    # for n in nodes:  #instead of this, we allow full nodes to go through and then we check in the final for loop
    #     if not n.isFull():
    #         nodesToSelectFrom += [n]
    nodesToSelectFrom = nodes

    #set number of candidates
    numNodes = len(nodesToSelectFrom)
    if numNodes - 1 < candidateNumber:
        candNumber = numNodes - 1
    else:
        candNumber = candidateNumber

    # generate candNumber unique candidates
    candidateList = []
    for i in range(0, candNumber):
        cand = genRandomCand(nodesToSelectFrom, node)
        while cand in candidateList or cand.isFull():
            cand = genRandomCand(nodesToSelectFrom, node)
        candidateList += [cand]
    return candidateList[0:candNumber]


def genRandomCand(nodesToSelectFrom, node):
    # the second candidate will be random
    r1 = random.randint(0, len(nodesToSelectFrom) - 1)
    randNode = nodesToSelectFrom[r1]
    while randNode == node:
        r1 = random.randint(0, len(nodesToSelectFrom) - 1)
        randNode = nodesToSelectFrom[r1]
    return randNode


def checkpointFunction(network, changeDict, currChanges, bestChanges, bestChangesAnalysis):
    """
    Checkpoint function judges the network by:
    1. making sure ALL nodes with channels are connected
    2. calculates characteristic path length, average betweenness centrality
    3. the "best" network is closest to these 3 measures of the current network. We are trying to minimize the average percent change
    :param newNodes:
    :param bestNodes:
    :param oldParams:
    :param analysis:
    :return:
    """
    igraph = network.igraph
    nodes = network.fullConnNodes + network.partConnNodes
    lst = []
    for c in currChanges:
        node1 = c.node1
        node2 = c.node2
        if changeDict[str(node1.nodeid)]:
            if node1 not in lst:
                nodes += [node1]
                lst += [node1]
        if changeDict[str(node2.nodeid)]:
            if node2 not in lst:
                nodes += [node2]
                lst += [node2]


    numNodes = len(nodes)
    shortestPath = True
    betweenness = False
    connectivity = False

    if shortestPath:
        shortestPathsPerNode = 10
        if shortestPathsPerNode >= len(nodes):
            shortestPathsPerNode = len(nodes) - 1
        s = 0
        n = 0
        # numSample = utility.constructSample(10, (0, 1), full=True)  # random size 10 sequence of 0s and 1s
        for ch in currChanges:
            node1 = ch.node1
            node2 = ch.node2
            if node2.maxChannels < node1.maxChannels:
                nodeToUse = node2
            else:
                nodeToUse = node1
            numSample = utility.constructSample(shortestPathsPerNode, (0, numNodes - 1), full=True)
            nodeidSample = utility.numSampleToNodeid(nodes, numSample)
            # while nodeToUse.nodeid not in nodeidSample:  #TODO I can make this faster--for now it is good
            #     nodeidSample = utility.numSampleToNodeid(nodes, numSample)

            destlist = []
            for nodeid in nodeidSample:
                if nodeid != str(nodeToUse.nodeid):
                    destlist += [igraph.vs._name_index[nodeid]]
            source = [igraph.vs._name_index[str(nodeToUse.nodeid)]]

            for i in range(0, len(destlist)):
                for j in range(0, len(destlist)):
                    if i != j and destlist[i] == destlist[j]:
                        print("error")

            if destlist != []:
                t0 = time.time()
                sp = igraph.shortest_paths(source, destlist)
                t1 = time.time()
                print("bench shortest paths", t1-t0)
                for p in sp:
                    s += p[0]
                n += len(destlist)
        newAvgS = s / n

        if bestChangesAnalysis[0] == None:
            bestChanges = currChanges
            bestChangesAnalysis[0] = newAvgS
        else:
            currAvgS = bestChangesAnalysis[0]
            if newAvgS < currAvgS:
                bestChanges = currChanges
                bestChangesAnalysis[0] = currAvgS

    elif betweenness:
        sampleSize = 30
        numSample = utility.constructSample(sampleSize, (0, numNodes - 1), full=False)
        nodeidSample = utility.numSampleToNodeid(nodes, numSample)
        newbs = igraph.betweenness(nodeidSample)
        newAvgB = sum(newbs) / sampleSize
        #save changes
        if bestChangesAnalysis[1] == None:
            bestChanges = currChanges
            bestChangesAnalysis[1] = newAvgB
        else:
            currAvgB = bestChangesAnalysis[1]
            if newAvgB < currAvgB:
                bestChanges = currChanges
                bestChangesAnalysis[1] = newAvgB
    elif connectivity:
        sampleSize = 30
        s = 0
        for i in range(0, sampleSize): #TODO we might need a larger sample because a random highly connected node will skew the results up (this is a prob because we resample every time)
            numSample = utility.constructSample(2, (0, numNodes - 1), full=True)
            nodeidSample = utility.numSampleToNodeid(nodes, numSample)
            i1 = igraph.vs.find(nodeidSample[0]).index
            i2 = igraph.vs.find(nodeidSample[1]).index
            cn = igraph.edge_connectivity(i1, i2)
            s += cn
        newAvgC = s/sampleSize

        if bestChangesAnalysis[2] == None:
            bestChanges = currChanges
            bestChangesAnalysis[2] = newAvgC
        else:
            currAvgC = bestChangesAnalysis[2]
            if newAvgC > currAvgC:
                bestChanges = currChanges
                bestChangesAnalysis[2] = currAvgC


    return bestChanges.copy(), bestChangesAnalysis  #TODO do I need .copy() ?


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



def sortNodesByMaxChannel(nodes):
    """
    sorts nodes in decreasing order by channel count
    :param nodes: node obj list
    :return: sorted list
    """
    sortedNodes = sorted(nodes, key=utility.channelMaxSortKey, reverse=True)
    return sortedNodes



def newNodeId(i):        # todo when we starting adding tx to the blockchain
    """
    We are simply returning the number put in for now
    :param i:
    :return:
    """
    return i



assert(checkBuildNetworkFields()==True)
if __name__ == "__main__":
    main()
