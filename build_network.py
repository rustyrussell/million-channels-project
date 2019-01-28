"""
Build network

Builds the network with a backtracking algorithm and network measures defined in measures.py
"""

import gini_power_experiment   # TODO: eventually change this
from random import randint
import networkClasses

##################### Current network measures to aim for. #####################
# When the program is done we will link the programs together, so we won't have these harded-coded constants about a specific snapshot of the network.
gini = 0.7362258902760351     # from gini_power_experiment
##################### Current network measures to aim for. #####################

#fields
noiseProb = .2    #on average, 1 out of every 5 nodes should be random
randGenNoiseTrials = 10  # the first 10 nodes will use randint the rest will be swapped at an interval of 1 out of every 10
finalNumChannels = 1000000    # right now it is constant at 1,000,000. #TODO make this variable when the program gets more advanced
randSeed = 0                  #TODO make this variable when the program gets more advanced

#functions

def main():
    fp = open(gini_power_experiment.channelFileName)
    jn = gini_power_experiment.loadJson(fp)
    nodes, channels = gini_power_experiment.jsonToObject(jn)
    alpha, x, yProb = analyzeCurrentNetwork(nodes)
    newNodes = nodeDistribution(alpha, finalNumChannels, randSeed, randomDist=False)   #eventually a config command can turn on and off the rand dist
    newNodes = buildNetwork(newNodes, 0)



def analyzeCurrentNetwork(nodes):
    """

    :param nodes:
    :return:
    """
    alpha, covariance, x, yProb = gini_power_experiment.powerLawExperiment(nodes)
    #TODO add call to clustering coefficient function

    return alpha, x, yProb

def buildNetwork(nodes, i):
    """
    :param nodes:
    :return:
    """
    sortedNodes = sortNodesByChannelCount(nodes)
    # noiseNodes = addNoise(sortedNodes)


def nodeDistribution(alpha, finalNumChannels, randSeed, randomDist=True):
    """
    There are two ways to choose the distribution of nodes. We can use randomness based on randint and the prob curve
    or we can create nodes exactly with the percentage of the prob curve.
    :param finalNumChannels: channels to create in the network
    :param randSeed: rand seed
    :param randomDist: if True, we generate with randint. Otherwise generate proportionally.
    :return:
    """
    nodes = []
    if randomDist:
        pass #TODO
    else:
        totalChannels = 0
        maxChannelsPerNode = 1    # channels per node
        p1 = gini_power_experiment.powerLawFunc([maxChannelsPerNode], alpha)[0]
        channelsToCreate = p1 * finalNumChannels
        totalChannels += channelsToCreate
        nodeIdCounter = 0
        while totalChannels <= finalNumChannels:
            # create channelsToCreate # of channels
            for i in range(0, channelsToCreate):
                currNodeId = newNodeId(nodeIdCounter)
                newNode = networkClasses.Node(currNodeId, maxChannelsPerNode)
                nodes += [newNode]
            maxChannelsPerNode += 1
            p = gini_power_experiment.powerLawFunc([maxChannelsPerNode], alpha)[0]
            channelsToCreate = p * finalNumChannels
            totalChannels += channelsToCreate
    return nodes



def sortNodesByChannelCount(nodes):
    """
    sorts nodes in decreasing order by channel count
    :param nodes: node obj list
    :return: sorted list
    """
    sortedNodes = nodes.sorted(key=channelCountSortKey, reverse=True)
    return sortedNodes


def decideNumChannels(probDist, func, args):
    """
    Decides randomly how many
    :param probDist:
    :param func:
    :param args:
    :return:
    """

def createNewNode():
    pass


#helper functions

def channelCountSortKey(node):
    """
    Use in .sort() when you want to sort a list of channels by channelCount
    :param node: node
    :return: channelCount
    """
    return node.channelCount


def newNodeId(i):        # todo when we starting adding tx to the blockchain
    """
    We are simply returning the number put in for now
    :param i:
    :return:
    """
    return i













x = [1, 2, 3, 4, 5]
y = gini_power_experiment.powerLawFunc(x, 2.3)
print(y)
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