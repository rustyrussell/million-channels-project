"""
Build network

Builds the network with a backtracking algorithm and network measures defined in measures.py
"""

import random
import networkClasses
import utility
import powerLawReg
import copy


##################### Current network measures to aim for. #####################
# When the program is done we will link the programs together, so we won't have these harded-coded constants about a specific snapshot of the network.
gini = 0.7362258902760351     # from gini_power_experiment
##################### Current network measures to aim for. #####################

#fields
noiseProb = .2    #on average, 1 out of every 5 nodes should be random
randGenNoiseTrials = 10  # the first 10 nodes will use randint the rest will be swapped at an interval of 1 out of every 10
finalNumChannels = 100 #1000000    # right now it is constant at 1,000,000. #TODO make this variable when the program gets more advanced
randSeed = 90                  #TODO make this variable when the program gets more advanced
channelFileName = "data/channels_1-18-18.json"
backtracksPerCheckpoint = 1
candidateNumber = 2
channelsPerRound = 10

#functions

def main():
    fp = open(powerLawReg.channelFileName)
    jn = utility.loadJson(fp)
    nodes, channels = utility.jsonToObject(jn)
    analysis = networkClasses.NetworkAnalysis(nodes)
    analysis.analyze()
    params = analysis.powerLaw[0]
    utility.setRandSeed(randSeed)
    newNodes = nodeDistribution(params, finalNumChannels)   #eventually a config command can turn on and off the rand dist
    # powerLawReg.powerLawExperiment(newNodes, reg=False, graph=True, params=params, bounds=(0,6000,1))
    newNodes = buildNetwork(newNodes, analysis)
    return newNodes



def buildNetwork(nodes, analysis):
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
    :return:
    """
    nodes = sortNodesByMaxChannel(nodes)
    totalChannels = 0
    params = networkClasses.ChannelGenParams()    # empty params
    bestNodes = [nodes, []]  #left side are nodes that can fit more channels, right side are nodes that can fit no more channels
    nodeNum = len(nodes)
    while (totalChannels + channelsPerRound) <= finalNumChannels:
        currNodes = bestNodes
        for t in range(0, backtracksPerCheckpoint):
            currNodesCopy = copy.deepcopy(currNodes)
            startingIndex = totalChannels % nodeNum
            newNodes = roundRec(currNodesCopy, startingIndex, params, analysis, None, 0)
            params, bestNodes = checkpointFunction(newNodes, bestNodes, params, analysis)
        totalChannels += channelsPerRound
        for i in range(len(bestNodes[0])-1, 0, -1): #checks if node is full. if it is, but the node into the "full" list
            if bestNodes[0][i].isFull():
                bestNodes[1] += [bestNodes[0][i]]
                bestNodes[0] = bestNodes[0][0:i] + bestNodes[0][i+1:]

    return bestNodes



def roundRec(nodes, startingIndex, params, analysis, bestNodes, i):
    """
    Backtracks though every permutation (channelsPerRound^candidateNumber permutations)
    :param nodes:
    :param startingIndex:
    :param params:
    :param i: 0-channelsPerRound-1
    :param j: 0-candidates-1
    :return:
    """

    unfullNodes = nodes[0]
    currNodeIndex = (startingIndex + i) % len(unfullNodes)
    currNode = unfullNodes[currNodeIndex]
    if i == channelsPerRound:
        params, bestNodes = checkpointFunction(nodes, bestNodes, params, analysis)
        return bestNodes

    candidates = generateCandidates(nodes, currNodeIndex, params)
    for c in range(0, candidateNumber):
        channel = createNewChannel(currNode, candidates[c])
        bestNodes = roundRec(nodes, startingIndex, params, analysis, bestNodes, i+1)
        undoChannel(channel)

    return bestNodes



def undoChannel(channel):
    """
    deletes channel
    :param channel: channel
    :return:
    """
    party1 = channel.party1
    party2 = channel.party2
    party1.removeChannel(channel)
    party2.removeChannel(channel)


def generateCandidates(nodes, index, params):
    """
    Generates candidateNumber number of candidates for backtracking
    :param nodes:
    :param index:
    :param params:
    :return:
    """
    allNodes = nodes[0] + nodes[1]



    return [allNodes[0], allNodes[1]]



def checkpointFunction(newNodes, bestNodes, oldParams, analysis):
    """
    Checkpoint function judges the network by:
    1. making sure ALL nodes with channels are connected
    2. calculates characteristic path length, average betweenness centrality, and average clustering
    3. the "best" network is closest to these 3 measures of the current network. We are trying to minimize the average percent change

    When the round is over, create the next round params

    Checkpoint function
    :param newNodes:
    :param bestNodes:
    :param oldParams:
    :param analysis:
    :return:
    """

    return oldParams, copy.deepcopy(newNodes)   #TODO change


def nodeDistribution(params, finalNumChannels):
    """
    There are two ways to choose the distribution of nodes. We can use randomness based on randint and the prob curve
    or we can create nodes exactly with the percentage of the prob curve.
    :param finalNumChannels: channels to create in the network
    :param randSeed: rand seed
    :param randomDist: if True, we generate with randint. Otherwise generate proportionally.
    :return: node list
    """
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



def createNewChannel(node1, node2):
    """
    creates channel between node1 and node2. NOTE: this does not check if adding this channel breaks the maximum
    :param node1: node obj
    :param node2: node obj
    :return: channel
    """
    channel = networkClasses.Channel(node1, node2)
    node1.addChannel(channel)
    node2.addChannel(channel)
    return channel



def newNodeId(i):        # todo when we starting adding tx to the blockchain
    """
    We are simply returning the number put in for now
    :param i:
    :return:
    """
    return i













main()


#defunct
def addNoise(sortedList):
    """
    adds noise to the sorted nodelist by swapping nodes.
    The first randGenNoiseTrials blocks will use randInt to select a node with noiseProb probability
    The rest of the blocks will get a swap every 1/noiseProb nodes. This is to reduce computation.
    :return:
    """
    length = len(sortedList)
    for i in range(0, length):
        if i < randGenNoiseTrials:
            #use randint
            pass
        else:
            #every 1/noiseProb nodes do a swap
            pass