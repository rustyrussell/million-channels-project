
import bisect
import json
from common import networkClasses
from random import seed, randint
import copy
from pickle import load
from igraph import Graph

# helper functions

def loadJson(fp):
    """
    helper function to load json
    :param fp: file object
    :return: json object
    """
    return json.load(fp)


def search(a, x):
    """
    The search helper function. Searches for a element in a list of objects. Objects MUST have __eq__
    :param a: list
    :param x: element
    :return: -1 for false, the element index for true
    """
    i = bisect.bisect_left(a, x)
    if i != len(a) and a[i].__eq__(x):
        return i
    return -1

def jsonToObject(jn):
    """
    Loads json that is from running the listchannels rpccommand and saving the output.
    Uses binary search and sorted lists for faster loading
    :param jn: json object
    :return: a sorted list of nodes, a sorted list of channels
    """
    channelsJson = jn["channels"]
    channels = []
    nodes = []
    for i in range(0, len(channelsJson)):
        #print("channel " + str(i))
        currChannel = channelsJson[i]
        nodeid1 = channelsJson[i]["source"]
        nodeid2 = channelsJson[i]["destination"]
        channelObj = networkClasses.Channel(None, None, currChannel)

        nodeObj1 = networkClasses.Node(nodeid1)
        nodeObj2 = networkClasses.Node(nodeid2)

        node1Exists = search(nodes, nodeObj1)
        if node1Exists != -1:
            nodeObj1 = nodes[node1Exists]
        else:
            bisect.insort_left(nodes, nodeObj1)

        node2Exists = search(nodes, nodeObj2)
        if node2Exists != -1:
            nodeObj2 = nodes[node2Exists]
        else:
            bisect.insort_left(nodes, nodeObj2)


        pair = False
        if node1Exists != -1 and node2Exists != -1:
            node1Channels = nodeObj1.channels
            channelExists = search(node1Channels, channelObj)
            if channelExists != -1:
                pair = True

        if pair == False:
            channelObj.setParty1(nodeObj1)
            channelObj.setParty2(nodeObj2)
            nodeObj1.addChannel(channelObj, temp=False)
            nodeObj2.addChannel(channelObj, temp=False)
            bisect.insort_left(channels, channelObj)

    return nodes, channels,


def makeigraphTargetNetwork(nodes, channels):
    g = Graph(directed=False)

    for n in nodes:
        g.add_vertex(str(n.nodeid))

    for ch in channels:
        nodeid1 = ch.node1.nodeid
        nodeid2 = ch.node2.nodeid
        g.add_edge(nodeid1, nodeid2)

    return g


def setRandSeed(s):
    """
    set random seed for random module (not for cryptographic purposes)
    :param seed:some int
    :return: None
    """
    seed(s)



def channelMaxSortKey(node):
    """
    Use in .sort() when you want to sort a list of channels by channelCount
    :param node: node
    :return: channelCount
    """
    return node.maxChannels


def sortByChannelCount(node):
    return node.channelCount


def sortByNodeId(node):
    return node.nodeid



def constructSample(sampleSize, bounds, full):
    """
    Construct num sample. if full is True, then we make sampleSize elements. If it is false, we don't force the size.
    This distinction is useful for some applications.
    TODO: consider binary search for checking for duplicates
    :param sampleSize: sample size num
    :param bounds: bounds of generated number
    :param full: bool
    :param list of nums to avoid
    :return:
    """

    sample = []
    if full:
        while len(sample) < sampleSize:
            r = randint(bounds[0], bounds[1])  # note: range is inclusive
            if r not in sample:
                sample += [r]
    else:
        for i in range(0, sampleSize):
            r = randint(bounds[0], bounds[1])   #note: range is inclusive
            if r not in sample:
                sample += [r]
    return sample

def numSampleToNodeid(nodes, numSample):
    nodeidSample = []
    for num in numSample:
        nodeid = str(nodes[num].nodeid)
        nodeidSample += [nodeid]
    return nodeidSample

def loadNetwork(networkFilename):
    fp = open(networkFilename, "rb")
    network = load(fp)
    return network


def duplicateIncompleteNetwork(network):
    return networkClasses.IncompleteNetwork(fullConnNodes=copy.deepcopy(network.fullConnNodes),
                                            disconnNodes=copy.deepcopy(network.disconnNodes),
                                            partConnNodes=copy.deepcopy(network.partConnNodes),
                                            unfullNodes=copy.deepcopy(network.unfullNodes))


