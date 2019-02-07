"""
Build network

Builds the network with a backtracking algorithm and network measures defined in measures.py
"""

import random
from networkClasses import  *
import utility
import powerLawReg
#import graph
import pickle
import time
from config import *




#functions

def main():
    fp = open(powerLawReg.channelFileName)
    jn = utility.loadJson(fp)
    nodes, channels = utility.jsonToObject(jn)
    targetNetwork = Network(fullConnNodes=nodes, analysis=True)
    utility.setRandSeed(randSeed)
    newNodes = nodeDistribution(targetNetwork, finalNumChannels)   # eventually a config command can turn on and off the rand dist
    incompleteNetwork = IncompleteNetwork(fullConnNodes=[], disconnNodes=newNodes)
    t1 = time.time()
    newNetwork = buildNetwork(targetNetwork, incompleteNetwork)
    t2 = time.time()
    print("time: " + str(t2-t1))
    print(len(newNetwork.channels))
    #graph.graph_tool(newNetwork, str(finalNumChannels) + "backtracking_with_betweenness_allcandrandom_seed1_30sample_3cand"
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
    incompleteNetwork.createNewChannel(node1, node2)

    channelGenParams = ChannelGenParams(targetNetwork, incompleteNetwork)    # empty params
    bestNetwork = incompleteNetwork

    j = 0
    while len(bestNetwork.unfullNodes) > 1:    #implicitly (totalChannels + channelsPerRound) <= finalNumChannels
        currNetwork = bestNetwork
        # for t in range(0, backtracksPerCheckpoint):
        params, stateChanges, changeAnalysis = roundRec(currNetwork, targetNetwork, [], [], [], channelGenParams, 0, 0)
        applyStateChanges(currNetwork, stateChanges)
        currNetwork.addChannels(stateChanges)
        if len(currNetwork.unfullNodes) < channelsPerRound:
            shift = len(currNetwork.unfullNodes)
        else:
            shift = channelsPerRound
        for i in range(0, shift):
            currNetwork.pushUnfull(currNetwork.popUnfull())
        #channelGenParams, bestNetwork = checkpointFunction(currNetwork, bestNetwork, targetNetwork, channelGenParams)
        # print(j)
        j += 1

    return bestNetwork



def roundRec(network, targetNetwork, currChanges, bestChanges, bestChangesAnalysis, channelGenParams, i, t):
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

    if i == channelsPerRound or len(nodes) <= 1:  # if rounds complete or no more unfull nodes
        channelGenParams, bestChanges, bestChangesAnalysis = checkpointFunction(network, targetNetwork, currChanges, bestChanges, bestChangesAnalysis, channelGenParams)
        return channelGenParams, bestChanges, bestChangesAnalysis

    currNode = network.popUnfull()    #pop from queue
    network.pushUnfull(currNode)

    candidates = generateCandidates(network, currNode, channelGenParams)
    for c in range(0, candidateNumber):
        other = candidates[c]
        channel = network.createNewChannel(currNode, other)
        currChanges += [channel]
        channelGenParams, bestChanges, bestChangesAnalysis = roundRec(network, targetNetwork, currChanges, bestChanges, bestChangesAnalysis, channelGenParams, i+1, t)
        network.removeChannel(channel) # reverse previous channel add
        network.unfullNodes = nodes # revert to old unfill queue
        currChanges = currChanges[0:-1] # revert to old changes

    return channelGenParams, bestChanges, bestChangesAnalysis


def applyStateChanges(network, channels):
    """
    once the ideal channel list is created, we apply it and finalize it here
    :param network: incomplete Network
    :param channels: channel list
    :return:
    """
    for c in channels:
        node1 = c.node1
        node2 = c.node2
        network.createNewChannel(node1, node2)



def generateCandidates(network, node, channelGenParams):
    """
    Generates candidateNumber number of candidates for backtracking
    :param nodes:
    :param index:
    :param params:
    :return:
    """
    candidateList = []

    # this clustering bit is too slow!
    # if node.maxChannels > 1:
    #     sampleSize = 5
    #     # maxChannels = node.maxChannels
    #     # analysis = channelGenParams.targetNetwork.analysis
    #     # myCluster = measures.calcNodeCluster(node)
    #     # targetCluster = analysis.cluster
    #     # clusterParams = targetCluster[3]
    #     # targetClusterY = powerLawReg.negExpFunc(maxChannels, clusterParams[0], clusterParams[1], clusterParams[2])
    #
    #     ns = node.neighbors
    #     #collecting neighbors of neighbors that are not neighbors or oneself or full
    #     nns = []
    #     for n in ns:
    #         s = n.neighbors
    #         for nn in s:
    #             if nn not in ns and nn != node and not nn.isFull():
    #                 nns += [nn]
    #
    #     if len(nns) == 0:
    #         candidateList += [genRandomCand(network, node)]
    #     else:
    #         # if myCluster <= targetCluster:
    #
    #         sample = []
    #         for i in range(0, sampleSize):
    #             if i+1 > len(nns):
    #                 break
    #             r = random.randint(0, len(nns)-1)
    #             if r not in sample:
    #                 sample += [r]
    #
    #
    #         #find nn that has highest (nnn that are in ns)/(total nnn)
    #         interconnList = []
    #         largest = 0
    #         largestNN = None
    #         for i in range(0, len(sample)):
    #             nn = nns[sample[i]]
    #             nnns = nn.neighbors
    #             if len(nnns) == 0:
    #                 continue
    #             elif nn.maxChannels == 1:
    #                 continue
    #             else:
    #                 s = 0
    #                 for nnn in nnns:
    #                     if nnn in ns:
    #                         s += 1
    #                 s = s / len(nnns)
    #                 interconnList += [(nn, s)]
    #                 if largest < s:
    #                     largestNN = nn
    #                     largest = s
    #
    #         if largestNN is None:
    #             candidateList += [genRandomCand(network, node)]
    #         else:
    #             candidateList += [largestNN]
    #
    #         # if myCluster <= targetCluster:
    #         #     #gather neighbors of neighbors that you are not connected to
    #         #     #choose highest (this is greedy)
    #         #     pass
    #         # elif myCluster > targetCluster:
    #         #     pass
    #
    # else:
    #     candidateList += [genRandomCand(network, node)]
    candidateList += [genRandomCand(network, node)]
    candidateList += [genRandomCand(network, node)]
    candidateList += [genRandomCand(network, node)]


    return candidateList[0:candidateNumber]


def genRandomCand(network, node):
    # the second candidate will be random
    if node.inNetwork():
        nodesToSelectFrom = network.disconnNodes + network.partConnNodes
    else:
        nodesToSelectFrom = network.partConnNodes

    r1 = random.randint(0, len(nodesToSelectFrom) - 1)
    randNode = nodesToSelectFrom[r1]
    while randNode == node:
        r1 = random.randint(0, len(nodesToSelectFrom) - 1)
        randNode = nodesToSelectFrom[r1]
    return randNode


def checkpointFunction(network, targetNetwork, currChanges, bestChanges, bestChangesAnalysis, channelGenParams):
    """
    Checkpoint function judges the network by:
    1. making sure ALL nodes with channels are connected
    2. calculates characteristic path length, average betweenness centrality
    3. the "best" network is closest to these 3 measures of the current network. We are trying to minimize the average percent change

    When the round is over, create the next round params

    Checkpoint function
    :param newNodes:
    :param bestNodes:
    :param oldParams:
    :param analysis:
    :return:
    """

    betweennessSampleSize = 30
    nodes = network.fullConnNodes + network.partConnNodes

    if bestChangesAnalysis == []:
        numSample = utility.constructSample(betweennessSampleSize, (0, len(nodes)-1))
        igraph = network.igraph
        bs = igraph.betweenness(numSample)
        avgB = sum(bs)/betweennessSampleSize
        bestChanges = currChanges
        bestChangesAnalysis = [numSample, avgB]
    else:
        numSample = bestChangesAnalysis[0]
        avgB = bestChangesAnalysis[1]

        igraph = network.igraph
        newbs = igraph.betweenness(numSample)
        newAvgB = sum(newbs) / betweennessSampleSize

        if newAvgB < avgB:
            bestChanges = currChanges
            bestChangesAnalysis = [numSample, newAvgB]


    return channelGenParams, bestChanges.copy(), bestChangesAnalysis  #TODO do I need .copy() ?


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
    x = powerLawReg.inversePowLawFuncC([r],a,b,c)[0]
    channelsForNode = round(x, 0)
    while channelsForNode > powerLawReg.maxChannelsPerNode:
        x = powerLawReg.inversePowLawFuncC([r], a, b, c)
        channelsForNode = round(x, 0)
    totalChannels += channelsForNode

    while totalChannels < finalNumChannels:     # this is why I wish python had do-while statements!!!
        n = Node(nodeidCounter, maxChannels=channelsForNode)
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




if __name__ == "__main__":
    main()
