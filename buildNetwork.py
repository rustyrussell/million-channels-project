"""
Build network

Builds the network with a backtracking algorithm and network measures defined in measures.py
"""

import random
from networkClasses import  *
import utility
import powerLawReg
import copy
# import graph
import measures


##################### Current network measures to aim for. #####################
# When the program is done we will link the programs together, so we won't have these harded-coded constants about a specific snapshot of the network.
gini = 0.7362258902760351     # from gini_power_experiment
##################### Current network measures to aim for. #####################

#fields
noiseProb = .2    #on average, 1 out of every 5 nodes should be random
randGenNoiseTrials = 10  # the first 10 nodes will use randint the rest will be swapped at an interval of 1 out of every 10
finalNumChannels = 1000 #1000000    # right now it is constant at 1,000,000. #TODO make this variable when the program gets more advanced
randSeed = 90                  #TODO make this variable when the program gets more advanced
channelFileName = "data/channels_1-18-18.json"
backtracksPerCheckpoint = 1
candidateNumber = 1
channelsPerRound = 10
attempts = candidateNumber**channelsPerRound

#functions

def main():
    fp = open(powerLawReg.channelFileName)
    jn = utility.loadJson(fp)
    nodes, channels = utility.jsonToObject(jn)
    targetNetwork = Network(fullConnNodes=nodes, analysis=True)
    utility.setRandSeed(randSeed)
    newNodes = nodeDistribution(targetNetwork, finalNumChannels)   # eventually a config command can turn on and off the rand dist
    incompleteNetwork = IncompleteNetwork(fullConnNodes=[], disconnNodes=newNodes)
    newNetwork = buildNetwork(targetNetwork, incompleteNetwork)

    print(len(newNetwork.channels))
    # graph.graph_tool(newNetwork, str(finalNumChannels) + "cluster1")
    return newNetwork



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
        for t in range(0, backtracksPerCheckpoint):
            if j == 3:
                print("3")
            j += 1
            stateChanges = roundRec(currNetwork, targetNetwork, [], [], channelGenParams, 0, 0)
            applyStateChanges(currNetwork, stateChanges)
            currNetwork.addChannels(stateChanges)
            if len(currNetwork.unfullNodes) < channelsPerRound:
                shift = len(currNetwork.unfullNodes)
            else:
                shift = channelsPerRound
            for i in range(0, shift):
                currNetwork.pushUnfull(currNetwork.popUnfull())
            #channelGenParams, bestNetwork = checkpointFunction(currNetwork, bestNetwork, targetNetwork, channelGenParams)
            print("done with round")


    return bestNetwork



def roundRec(network, targetNetwork, currChanges, bestChanges, channelGenParams, i, t):
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
        params, bestChanges = checkpointFunction(network, targetNetwork, currChanges, bestChanges, channelGenParams)
        return bestChanges

    currNode = network.popUnfull()    #pop from queue
    network.pushUnfull(currNode)

    candidates = generateCandidates(network, currNode, channelGenParams)
    for c in range(0, candidateNumber):
        other = candidates[c]
        channel = network.createNewChannel(currNode, other)
        currChanges += [channel]
        bestChanges = roundRec(network, targetNetwork, currChanges, bestChanges, channelGenParams, i+1, t)
        network.removeChannel(channel) # reverse previous channel add
        network.unfullNodes = nodes # revert to old unfill queue
        currChanges = currChanges[0:-1] # revert to old changes

    return bestChanges


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



def generateCandidates(incompleteNetwork, node, channelGenParams):
    """
    Generates candidateNumber number of candidates for backtracking
    :param nodes:
    :param index:
    :param params:
    :return:
    """
    candidateList = []

    # maxChannels = node.maxChannels
    # analysis = channelGenParams.targetNetwork.analysis
    # myCluster = measures.calcNodeCluster(node)
    # targetCluster = analysis.myCluster
    # clusterParams = targetCluster[3]
    # targetClusterY = powerLawReg.negExpFunc(maxChannels, clusterParams[0], clusterParams[1], clusterParams[2])
    # if myCluster <= targetCluster:
    #     #gather neighbors of neighbors that you are not connected to
    #     #check (n-n-n that are connected to n-n)/(total n-n-n)  of each n-of-n
    #     #choose highest (this is greedy)
    #     pass
    # elif myCluster > targetCluster:
    #     pass


    # the second candidate will be random
    if node.inNetwork():
        nodesToSelectFrom = incompleteNetwork.disconnNodes + incompleteNetwork.partConnNodes
    else:
        nodesToSelectFrom = incompleteNetwork.partConnNodes

    r1 = random.randint(0, len(nodesToSelectFrom)-1)
    randNode = nodesToSelectFrom[r1]
    while randNode == node:
        r1 = random.randint(0, len(nodesToSelectFrom) - 1)
        randNode = nodesToSelectFrom[r1]
    candidateList += [randNode]

    # r2 = random.randint(0, len(nodesToSelectFrom)-1)
    # randNode = nodesToSelectFrom[r2]
    # while randNode == node:
    #     r2 = random.randint(0, len(nodesToSelectFrom) - 1)
    #     randNode = nodesToSelectFrom[r2]
    # candidateList += [randNode]

    return candidateList




def checkpointFunction(network, targetNetwork, currChanges, bestChanges, channelGenParams):
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

    return channelGenParams, copy.copy(currChanges) #copy.deepcopy(incompleteNetwork) #TODO change


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













main()
