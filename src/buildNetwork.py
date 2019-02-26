"""
Build network

Builds the network with a backtracking algorithm and network measures defined in measures.py
"""

import random
from common import networkClasses
from common import utility
import powerLawReg
import pickle
import time
from config import *
import bisect
import igraph

# #functions
#
# def main():
#     ti = time.time()
#     fp = open(powerLawReg.channelFileName)
#     jn = utility.loadJson(fp)
#     nodes, channels= utility.jsonToObject(jn)
#     t0 = time.time()
#     print("load json done", t0-ti)
#     targetNetwork = networkClasses.Network(fullConnNodes=nodes)
#     targetNetwork.channels = channels
#     targetNetwork.analysis.analyze()
#     utility.setRandSeed(randSeed)
#     newNodes = nodeDistribution(targetNetwork, finalNumChannels)   # eventually a config command can turn on and off the rand dist
#     t1 = time.time()
#     print("nodeDistribution done", t1-t0)
#     incompleteNetwork = networkClasses.IncompleteNetwork(fullConnNodes=[], disconnNodes=newNodes)
#     t2 = time.time()
#     newNetwork = buildNetwork(targetNetwork, incompleteNetwork)
#     t3 = time.time()
#     print("print build network done", t3-t2)
#     print("num of channels", len(newNetwork.channels))
#     t4 = time.time()
#     newbsAvg = newNetwork.analysis.betweenness()
#     t5 = time.time()
#     print("new betweenness (", str(t5-t4), ")", newbsAvg)
#     g = utility.makeigraphTargetNetwork(nodes, channels)
#     targetNetwork.igraph = g
#     t6 = time.time()
#     orgbsAvg = targetNetwork.analysis.betweenness()
#     t7 = time.time()
#     print("original betweenness (", str(t7-t6), ")", orgbsAvg)
#     writeCompactNetwork(newNetwork)
#     print("done writing")
#
#     from graph import graph
#     graph.graph_tool(newNetwork, str(finalNumChannels) + "2_24_4r_1c_removingscanning")

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
    utility.setRandSeed(2)
    newNodes = nodeDistribution(targetNetwork, finalNumChannels)   # eventually a config command can turn on and off the rand dist
    t1 = time.time()
    print("nodeDistribution done", t1-t0)
    incompleteNetwork = networkClasses.IncompleteNetwork(fullConnNodes=[], disconnNodes=newNodes)
    t2 = time.time()
    ig = buildNetworkFast(incompleteNetwork)
    # for v in ig.vs:
    #     print(v)
    t3 = time.time()
    print("buildNetworkFast", t3-t2)
    draw(ig)

def writeCompactNetwork(network):
    f = open(networkSaveFile, "wb")
    pickle.dump(len(network.channels), f)   # num of channels
    for c in network.channels:
        pickle.dump(networkClasses.Chan(c), f)


def buildNetworkFast(incompleteNetwork):
    # connect first node to second node (to bootstrap network)
    incompleteNetwork.unfullNodes.sort(key=utility.channelMaxSortKey, reverse=True)
    usedLst = [[] for i in range(0, len(incompleteNetwork.unfullNodes))]
    nodes = incompleteNetwork.unfullNodes
    nodeidSortedNodes = incompleteNetwork.unfullNodes.copy()
    nodeidSortedNodes.sort(key=utility.sortByNodeId)
    nodesLeft = nodeidSortedNodes.copy()
    channels = []
    ig = incompleteNetwork.igraph
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
            channel = networkClasses.Channel(node, nodeToConnect)
            node.addChannel(channel, True)
            nodeToConnect.addChannel(channel, True)
            usedLst[node.nodeid] += [nodeToConnectId]
            usedLst[nodeToConnectId] += [node.nodeid]
            channels += [channel]
            es += [(node.nodeid, nodeToConnectId)]
        print("done with", n)
        n += 1
        if done:
            break
    ig.add_edges(es)
    return ig


def draw(ig):
    igraph.drawing.plot(ig, bbox=(0,0,2000,2000))




def buildNetworkOld(targetNetwork, incompleteNetwork):
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

    #analyze
    maxChannelsSPPercent = .25 # selects for lower x% of nodes
    pl = targetNetwork.analysis.powerLaw
    params = pl[0]
    maxChannelsSP = powerLawReg.culmPowLawC(maxChannelsSPPercent, params[0], params[1], params[2])
    print("maxChennelsSP", maxChannelsSP)
    target = [maxChannelsSP]

    flushInterval = 50

    # connect first node to second node (to bootstrap network)
    incompleteNetwork.unfullNodes.sort(key=utility.channelMaxSortKey, reverse=True)
    index = 0
    node1 = incompleteNetwork.unfullNodes[0]
    node2 = incompleteNetwork.unfullNodes[1]
    startingChannel = networkClasses.Channel(node1, node2)
    applyStateChanges(incompleteNetwork, [startingChannel], index)
    flushNetwork(incompleteNetwork)
    incompleteNetwork.addChannels([startingChannel])
    currNetwork = incompleteNetwork

    j = 1
    k = 1
    f = 1
    t100 = time.time()
    sumBench = 0
    while len(currNetwork.unfullNodes) > 1:    #implicitly (totalChannels + channelsPerRound) <= finalNumChannels
        stateChanges, changeAnalysis, spliceArray, currChanges, index, bench = roundRec(currNetwork, index, target, {}, [], [], [], [None,None,None], 0, [])
        spliceArray()
        # sumBench += sum(bench)

        #print("bench roundRec:", t1-t0)
        #t2 = time.time()
        #t0 = time.time()
        applyStateChanges(currNetwork, stateChanges, index)
        #t1 = time.time()
        sumBench += sum(bench)

        if f == flushInterval:
                t0 = time.time()
                flushNetwork(currNetwork)
                t1 = time.time()
                print("flush", t1-t0)
                f = 0
        f += 1

        #benchmarking
        if j == 50:
            t100end = time.time()
            print("channel created:", k*50*channelsPerRound, t100end-t100)
            print("avg first half checkpoint bench:", sumBench)
            k += 1
            j = 1
            t100 = time.time()
            sumBench = 0
        j += 1
        #benchmarking

    return currNetwork


def applyStateChanges(network, channels, i):
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

    #add channels to igraph
    vs = []
    es = []

    for c in channels:
        node1 = c.node1
        node2 = c.node2

        if node1.channelCount == 0:  # if disconnected
            self.igraph.add_vertex(str(node1.nodeid))  # add to igraph

        if node2.channelCount == 0:  # if disconnected
            self.igraph.add_vertex(str(node2.nodeid))  # add to igraph

    network.igraph.add

    i += len(channels)

    return i

def flushNetwork(network):
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


def roundRec(network, index, target, changeDict, spliceArray, currChanges, bestChanges, bestChangesAnalysis, i, bench):
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
    numNodes = len(nodes)
    if numNodes > 0:
        index = index % len(nodes)
        currNode = nodes[index]
        while currNode.isFull():
            spliceArray += [index]
            index += 1
            if index > numNodes-1:
                index = 0
            currNode = nodes[index]
        index += 1
        candidates, spliceArray = generateCandidates(network, target, currNode, spliceArray)


    if i == channelsPerRound or numNodes <= 1 or len(candidates) == 0:  # if rounds complete or no more unfull nodes or no candidates
        bestChanges, bestChangesAnalysis, bench = checkpointFunction(network, target, changeDict, currChanges, bestChanges, bestChangesAnalysis, bench)
        return bestChanges, bestChangesAnalysis, spliceArray, currChanges, index, bench

    for c in range(0, len(candidates)):
        other = candidates[c]   #cand c
        addChangeDict(changeDict, currNode, other)  # must happen before add channel
        channel = network.createNewChannel(currNode, other, temp=True)    # create temp channel (meaning don't add to nodes' channel lists)
        currChanges += [channel] # add channel to current changes
        bestChanges, bestChangesAnalysis, spliceArray, currChanges, index, savedBench = roundRec(network, index, target, changeDict, spliceArray, currChanges, bestChanges, bestChangesAnalysis, i+1, bench)
        currChanges = currChanges[0:-1] # delete the last change
        network.removeChannel(channel, temp=True) # reverse previous temp channel add
        removeChangeDict(changeDict, currNode, other) # must happen after remove channel

    return bestChanges, bestChangesAnalysis, spliceArray, currChanges, index, bench


# def roundIter(network, index, target, changeDict, spliceArray, currChanges):
#
#     #
#

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


def generateCandidates(network, target, node, spliceArray):
    randCands, spliceArray = getRandomCands(network, target, node, spliceArray)
    cands = []
    if len(randCands) > 1:
        nodes = network.fullConnNodes + network.partConnNodes
        numNodes = len(nodes)
        igraph = network.igraph
        source = []
        for cand in randCands:
            source += [igraph.vs._name_index[str(cand.nodeid)]]
        destNodes = nodes
        shortestPathsPerNode = 5
        if shortestPathsPerNode >= len(destNodes):
            shortestPathsPerNode = len(destNodes) - 1
        numSample = utility.constructSample(shortestPathsPerNode, (0, numNodes - 1), full=True)
        nodeidSample, nodeSample = utility.numSampleToNodeid(destNodes, numSample)
        destlist = []
        s = []
        mini = 0
        for nodeid in nodeidSample:
            destlist += [igraph.vs._name_index[nodeid]]
            if destlist != []:
                sp = igraph.shortest_paths_dijkstra(source, destlist)
                for p in sp:
                    s += sum(p)
                for i in range(0, len(s)):
                    if s[i] < s[mini]:
                        mini = i
        cands += nodeSample[mini]
    else:
        return cands, spliceArray

def getRandomCands(network, target, node, spliceArray):
    """
      Generates candidateNumber number of candidates for backtracking
      :param network
      :param node
      :return: cand list
      """
    # get node list to select from
    if node.inNetwork():
        nodes = network.unfullNodes
    else:
        nodes = network.partConnNodes
    # nodesToSelectFrom = []
    # for n in nodes:  #instead of this, we allow full nodes to go through and then we check in the final for loop
    #     if not n.isFull():
    #         nodesToSelectFrom += [n]
    nodesToSelectFrom = nodes

    # set number of candidates
    numNodes = len(nodesToSelectFrom)
    if numNodes - 1 < candidateNumber:
        candNumber = numNodes - 1
    else:
        candNumber = candidateNumber

    maxChannelsSP = target[0]  # if highly connected, we don't give a shit about backtracking
    if node.maxChannels > maxChannelsSP:
        candNumber = 1

    if nodesToSelectFrom == [node]:
        candNumber = 0

    # generate candNumber unique candidates
    candidateList = []
    for i in range(0, candNumber):
        cand, r = genRandomCand(nodesToSelectFrom, node)
        j = 0
        while cand in candidateList or cand.isFull():
            if cand.isFull():
                spliceArray += [r]
            cand, r = genRandomCand(nodesToSelectFrom, node)
            if j == 10:
                return candidateList, spliceArray  # this is very hacky. But this is the only efficent way I can find without filtering out full nodes beforehand (which is o(n))
            j += 1

        candidateList += [cand]

    return candidateList[0:candNumber], spliceArray

def genRandomCand(nodesToSelectFrom, node):
    # the second candidate will be random
    r1 = random.randint(0, len(nodesToSelectFrom) - 1)
    randNode = nodesToSelectFrom[r1]
    while randNode == node:
        r1 = random.randint(0, len(nodesToSelectFrom) - 1)
        randNode = nodesToSelectFrom[r1]
    return randNode, r1


def checkpointFunction(network, target, changeDict, currChanges, bestChanges, bestChangesAnalysis, bench):
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
    # t0 = time.time()

    maxChannelsSP = target[0]
    igraph = network.igraph
    nodes = network.fullConnNodes + network.partConnNodes
    numNodes = len(nodes)
    shortestPathNodes = []
    highlyConnNodes = []
    for ch in currChanges:
        # t0 = time.time()
        node1 = ch.node1
        node2 = ch.node2
        if node1.maxChannels < maxChannelsSP and node1.nodeid not in shortestPathNodes:
            shortestPathNodes += [igraph.vs._name_index[str(node1.nodeid)]]
        elif node1.nodeid not in highlyConnNodes:
            highlyConnNodes += [igraph.vs._name_index[str(node1.nodeid)]]
        if node2.maxChannels < maxChannelsSP and node2.nodeid not in shortestPathNodes:
            shortestPathNodes += [igraph.vs._name_index[str(node2.nodeid)]]
        elif node2.nodeid not in highlyConnNodes:
            highlyConnNodes += [igraph.vs._name_index[str(node2.nodeid)]]

    t0 = time.time()

    if shortestPathNodes != []: #low nodes
        destNodes = nodes
        source = shortestPathNodes
        shortestPathsPerNode = 5
        if shortestPathsPerNode >= len(destNodes):
            shortestPathsPerNode = len(destNodes) - 1
        s = 0
        n = 0
        # numSample = utility.constructSample(10, (0, 1), full=True)  # random size 10 sequence of 0s and 1s
        # t0 = time.time()


        numSample = utility.constructSample(shortestPathsPerNode, (0, numNodes - 1), full=True)
        nodeidSample = utility.numSampleToNodeid(destNodes, numSample)
        # while nodeToUse.nodeid not in nodeidSample:  #TODO I can make this faster--for now it is good
        #     nodeidSample = utility.numSampleToNodeid(nodes, numSample)

        destlist = []
        for nodeid in nodeidSample:
            # if nodeid != str(nodeToUse.nodeid):
            destlist += [igraph.vs._name_index[nodeid]]
        # source = [igraph.vs._name_index[str(nodeToUse.nodeid)]]

            #t1 = time.time()

            if destlist != []:
                #t0 = time.time()
                sp = igraph.shortest_paths_dijkstra(source, destlist)
                #t1 = time.time()
                #print("bench shortest paths", t1-t0)
                for p in sp:
                    s += p[0]
                n += len(destlist)
        newAvgS = s / n
        # t1 = time.time()

        if bestChangesAnalysis[0] == None:
            bestChanges = currChanges
            bestChangesAnalysis[0] = newAvgS
        else:
            currAvgS = bestChangesAnalysis[0]
            if newAvgS < currAvgS:
                bestChanges = currChanges
                bestChangesAnalysis[0] = currAvgS
    elif highlyConnNodes != []:
        bestChanges = currChanges



    # elif betweenness:
    #     sampleSize = 30
    #     numSample = utility.constructSample(sampleSize, (0, numNodes - 1), full=False)
    #     nodeidSample = utility.numSampleToNodeid(nodes, numSample)
    #     newbs = igraph.betweenness(nodeidSample)
    #     newAvgB = sum(newbs) / sampleSize
    #     #save changes
    #     if bestChangesAnalysis[1] == None:
    #         bestChanges = currChanges
    #         bestChangesAnalysis[1] = newAvgB
    #     else:
    #         currAvgB = bestChangesAnalysis[1]
    #         if newAvgB < currAvgB:
    #             bestChanges = currChanges
    #             bestChangesAnalysis[1] = newAvgB
    # elif connectivity:
    #     sampleSize = 30
    #     s = 0
    #     for i in range(0, sampleSize): #TODO we might need a larger sample because a random highly connected node will skew the results up (this is a prob because we resample every time)
    #         numSample = utility.constructSample(2, (0, numNodes - 1), full=True)
    #         nodeidSample = utility.numSampleToNodeid(nodes, numSample)
    #         i1 = igraph.vs.find(nodeidSample[0]).index
    #         i2 = igraph.vs.find(nodeidSample[1]).index
    #         cn = igraph.edge_connectivity(i1, i2)
    #         s += cn
    #     newAvgC = s/sampleSize
    #
    #     if bestChangesAnalysis[2] == None:
    #         bestChanges = currChanges
    #         bestChangesAnalysis[2] = newAvgC
    #     else:
    #         currAvgC = bestChangesAnalysis[2]
    #         if newAvgC > currAvgC:
    #             bestChanges = currChanges
    #             bestChangesAnalysis[2] = currAvgC


    t1 = time.time()
    return bestChanges, bestChangesAnalysis, bench #+ [t1-t0] #TODO do I need .copy() ?


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
