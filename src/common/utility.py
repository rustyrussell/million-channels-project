
import bisect
import json
from common import networkClasses
from random import seed, randint
import copy
from pickle import load, dump
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
            nodeObj1.addChannel(channelObj)
            nodeObj2.addChannel(channelObj)
            bisect.insort_left(channels, channelObj)

    return nodes, channels,

def writeCompactNetwork(network, filename):
    """
    pickle write network to file
    :param network:
    :return:
    """
    f = open(filename, "wb")
    dump(len(network.channels), f)   # num of channels
    for c in network.channels:
        dump(networkClasses.Chan(c), f)


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


def loadNetwork(networkFilename):
    fp = open(networkFilename, "rb")
    network = load(fp)
    return network



