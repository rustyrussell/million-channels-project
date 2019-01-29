"""
Build network

Builds the network with a backtracking algorithm and network measures defined in measures.py
"""

# import test
import random
import networkClasses
import utility
import powerLawReg



##################### Current network measures to aim for. #####################
# When the program is done we will link the programs together, so we won't have these harded-coded constants about a specific snapshot of the network.
gini = 0.7362258902760351     # from gini_power_experiment
##################### Current network measures to aim for. #####################

#fields
noiseProb = .2    #on average, 1 out of every 5 nodes should be random
randGenNoiseTrials = 10  # the first 10 nodes will use randint the rest will be swapped at an interval of 1 out of every 10
finalNumChannels = 1000000    # right now it is constant at 1,000,000. #TODO make this variable when the program gets more advanced
randSeed = 90                  #TODO make this variable when the program gets more advanced
channelFileName = "data/channels_1-18-18.json"


#functions

def main():
    fp = open(powerLawReg.channelFileName)
    jn = utility.loadJson(fp)
    nodes, channels = utility.jsonToObject(jn)
    params, x, yProb = analyzeCurrentNetwork(nodes)
    utility.setRandSeed(randSeed)
    newNodes = nodeDistribution(params, finalNumChannels)   #eventually a config command can turn on and off the rand dist
    powerLawReg.powerLawExperiment(newNodes, reg=False, graph=True, params=params, bounds=(0,6000,1))
    # newNodes = buildNetwork(newNodes, 0)


def analyzeCurrentNetwork(nodes):
    """
    get power law reg and clustering coefficient
    :param nodes:
    :return:
    """
    params, covariance, x, yProb = powerLawReg.powerLawExperiment(nodes, graph=False, completeNetwork=True)
    #TODO add call to clustering coefficient function

    return params, x, yProb

def buildNetwork(nodes, i):
    """
    :param nodes:
    :return:
    """
    sortedNodes = sortNodesByChannelCount(nodes)
    # noiseNodes = addNoise(sortedNodes)


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
    pass

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