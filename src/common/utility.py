
import bisect
import json
from common import networkClasses
from random import seed, randint
import copy
from pickle import load, dump
from igraph import Graph
import csv

# helper functions

def loadjson(fp):
    """
    helper function to load json
    :param fp: file object
    :return: json object
    """
    return json.load(fp)


def loadcsv(fp):
    reader = csv.reader(fp)
    return reader


def getSaveFiles(datadir, name):
    nodeSaveFile = datadir + name + "/" + name + ".nodes"
    channelSaveFile = datadir + name + "/" + name + ".channels"
    gossipSaveFile = datadir + name + "/" + name + ".gossip"
    return nodeSaveFile, channelSaveFile, gossipSaveFile

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
        channelObj = networkClasses.Channel(None, None, json=currChannel)

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
            channelObj.setNode1(nodeObj1)
            channelObj.setNode2(nodeObj2)
            nodeObj1.addChannel(channelObj)
            nodeObj2.addChannel(channelObj)
            bisect.insort_left(nodeObj1.channels, channelObj)
            bisect.insort_left(nodeObj2.channels, channelObj)
            bisect.insort_left(channels, channelObj)

    return nodes, channels

def writeNetwork(network, gossipSequence, nodeSaveFile, channelSaveFile):
    """
    pickle write network to file.
    Format: #ofNodes, nodes, #ofChannels, channels
    :param network:
    :return:
    """
    f1 = open(nodeSaveFile, "wb")
    nodeNum = network.getNodeNum()
    dump(nodeNum, f1)
    nodes = network.getNodes()
    for n in range(0, nodeNum):
        dump(nodes[n], f1)
    f1.close()

    f2 = open(channelSaveFile, "wb")
    dump(gossipSequence, f2)
    dump(len(network.channels), f2)   # num of channels
    for c in network.channels:
        dump(networkClasses.Chan(c), f2)
    f2.close()

def loadNetwork(nodeSaveFile, channelSaveFile):
    """
    load network from file
    :param filename: filename
    :return: network
    """
    f1 = open(nodeSaveFile, "rb")
    numNodes = load(f1)
    nodes = []
    for i in range(0, numNodes):
        nodes += [load(f1)]
    f1.close()
    nodes.sort(key=sortByNodeId)


    f2 = open(channelSaveFile, "rb")
    gossipSequence = load(f2)
    numChannels = load(f2)
    channels = []
    es = []
    for i in range(0, numChannels):
        chan = load(f2)
        node1 = nodes[chan.node1id]
        node2 = nodes[chan.node2id]
        channel = networkClasses.Channel(node1, node2, scid=chan.scid)
        channels += [channel]
        es += [(channel.node1.nodeid, channel.node2.nodeid)]
    f2.close()
    network = networkClasses.Network(nodes, channels)
    network.igraph = Graph()
    network.igraph.add_vertices(len(network.fullConnNodes))
    network.igraph.add_edges(es)

    return network, gossipSequence

def setRandSeed(s):
    """
    set random seed for random module (not for cryptographic purposes)
    :param seed:some int
    :return: None
    """
    seed(s)


def getScid(height, tx):
    """
    creates scid from block int and tx int
    :param height: int
    :param tx: int (between 1 and 1023 inclusive)
    :return:scid bytearray
    """
    bheight = bytearray(height.to_bytes(3, "big"))
    btx = bytearray(tx.to_bytes(3, "big"))
    scidOutput = bytearray().fromhex("0001")  # output 1
    bscid = bheight + btx + scidOutput

    return bscid


def channelMaxSortKey(node):
    """
    Use in .sort() when you want to sort a list of nodes by maxChannels
    :param node: node
    :return: channelCount
    """
    return node.maxChannels


def sortByChannelCount(node):
    """
    Use in .sort() when you want to sort a list of nodes by channel count
    :param node: node
    :return: channelCount
    """ 
    return node.channelCount


def sortByNodeId(node):
    """
    Use in .sort() when you want to sort a list of nodes by nodeid
    :param node: node
    :return: nodeid
    """ 
    return node.nodeid


