"""
This program aims to test two centralization measures for modeling the lightning network: gini coefficient and power log

The latest commit only tests power_law. gini coefficient has not been done yet.
"""

import json
import bisect
from matplotlib import pyplot as plt
from scipy import optimize
from math import pow
import numpy as np

#fields

channelFileName = "data/channels_1-18-18.json"


#classes

class Node:
    """
    Node class
    """
    def __init__(self, nodeid, channels=None):
        if channels == None:
            self.channels = []
            self.value = 0
            self.channelCount = 0
        else:
            self.channelList = channels
            for channel in channels:
                self.value += channel.value
            self.channelCount = len(channels)
        self.nodeid = nodeid

    def addChannel(self, channel):
        bisect.insort_left(self.channels, channel)
        self.value += channel.value
        self.channelCount += 1

    def __lt__(self, otherNode):
        return self.nodeid < otherNode.nodeid

    def __gt__(self, otherNode):
        return self.nodeid > otherNode.nodeid

    def __eq__(self, otherNode):
        return self.nodeid == otherNode.nodeid


class Channel:
    """
    Channel class
    """
    def __init__(self, party1, party2, json):
        self.party1 = party1
        self.party2 = party2
        self.json = json
        self.channelid = json["short_channel_id"]
        self.value = json["satoshis"]

    def setParty1(self, party1):
        self.party1 = party1

    def setParty2(self, party2):
        self.party2 = party2

    def __lt__(self, otherChannel):
        return self.channelid < otherChannel.channelid

    def __gt__(self, otherChannel):
        return self.channelid > otherChannel.channelid

    def __eq__(self, otherChannel):
        return self.channelid == otherChannel.channelid



#functions

def main():
    """
    Opens json file, creates node and channel objects objects, runs gini coefficient and power log tests.
    :return:
    """
    fp = open(channelFileName)
    jn = loadJson(fp)

    #experiments
    nodes, channels = jsonToObject(jn)
    #power law
    alpha, covariance = powerLawExperiment(nodes)
    print("power Law experiment results: ")
    print("alpha: "+str(alpha[0]))
    print("covariance: " + str(covariance[0][0]))

    print()
    #gini
    giniCoefficient = giniCoefficientExperiment(nodes)
    print("gini coefficient results:")
    print("gini: " + str(giniCoefficient))

    plt.show()

def powerLawExperiment(nodes):
    """
    The power law experiment fits a regression to the data and plots the data and the regression power law curve
    :return: alpha, covariance
    """
    x, y = getChannelFreqData(nodes)
    yProb = freqDataToProbData(y, len(nodes))
    simpleFreqPlot(x, yProb)
    alpha, covariance = powerLawRegressionParam(x, yProb)
    plotPowLaw(powerLawFunc, alpha[0], (1.75, 1000, .25))
    plt.autoscale()
    return alpha, covariance

def giniCoefficientExperiment(nodes):
    """
    finds gini coefficient
    :return: gini coefficient
    """
    channelCountList = []
    for node in nodes:
        channelCountList += [float(node.channelCount)]
    channelCountListArray = np.array(channelCountList)
    giniCoefficient = gini(channelCountListArray)
    return giniCoefficient

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
        channelObj = Channel(None, None, currChannel)

        nodeObj1 = Node(nodeid1)
        nodeObj2 = Node(nodeid2)

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

    return nodes, channels


def getChannelFreqData(nodes):
    """
    x axis is # of channels
    y axis is # of nodes
    :param nodes: list of nodes (sorted)
    :return: (x, y) in the form of an x list and y list (easy format for graphing in matplotlib)
    """
    channelCountList = []
    for node in nodes:
        channelCountList += [node.channelCount]
    x = []
    y = []
    j = 0
    channelCountList.sort()
    channelsOfPrevNode = None
    for i in range(0, len(channelCountList)):
        channelsOfNodei = channelCountList[i]
        freq = 1
        if channelsOfPrevNode == None:
            x = [channelsOfNodei]
            y = [1]
            channelsOfPrevNode = channelsOfNodei
        elif channelsOfNodei == channelsOfPrevNode:
            y[j] += 1
        else:
            j += 1
            x += [channelsOfNodei]
            y += [1]
            channelsOfPrevNode = channelsOfNodei

    return x,y

def simpleFreqPlot(x, y, xscale=False, yscale=False):
    """
    Create simple scatterplot in matplotlib library
    :param x: x list
    :param y: y list
    :param xscale: bool log scale on x axis
    :param yscale: bool log scale on y axis
    :return:
    """
    plt.scatter(x, y)

    if xscale:
        plt.xscale('log')      # this axis scales in log better than y-axis log scale
    if yscale:
        plt.yscale('log')

#power law

def plotPowLaw(func, a, rangeTup):
    """
    plot a function over x range define in rangeTup
    :param func: function that maps x->y
    :param rangeTup: rangeTup where (starting, ending, discrete_interval)
    :return: None
    """
    rr = np.arange(rangeTup[0], rangeTup[1], rangeTup[2])
    plt.plot(rr, func(rr, a))
    plt.title("power law reg. on channel freq. prob. distribution")
    plt.xlabel("channels")
    plt.ylabel("probability")
    # plt.box(on=True)
    plt.figtext(.45, .85, "y = x^(-" + str(a) + ")")
def freqDataToProbData(y, nodeNumber):
    """
    gives prob distribution which is used for power law calculation
    :param y: # of channels
    :param nodeNumber: total numbers
    :return:
    """
    newy = []
    for ele in y:
        newy += [ele/nodeNumber]
    return newy


def powerLawRegressionParam(x, y):
    """
    Performs a regression analysis on power law function
    :return:
    """
    alpha, covariance = optimize.curve_fit(powerLawFunc, x, y)
    return alpha, covariance


def powerLawFunc(x, a):
    """
    Power law function.
    :param x: x list of data
    :param a: alpha
    :return: y
    """
    c = 1  #c is chosen so that integral 0<x<inf = 1.
    y = []
    for e in x:
        y += [c*(pow(e, -1*a))]
    return y


#gini coefficient

"""
The function below is from https://github.com/oliviaguest/gini
"""
def gini(array):
    """Calculate the Gini coefficient of a numpy array."""
    # based on bottom eq:
    # http://www.statsdirect.com/help/generatedimages/equations/equation154.svg
    # from:
    # http://www.statsdirect.com/help/default.htm#nonparametric_methods/gini.htm
    # All values are treated equally, arrays must be 1d:
    array = array.flatten()
    if np.amin(array) < 0:
        # Values cannot be negative:
        array -= np.amin(array)
    # Values cannot be 0:
    array += 0.0000001
    # Values must be sorted:
    array = np.sort(array)
    # Index per array element:
    index = np.arange(1,array.shape[0]+1)
    # Number of array elements:
    n = array.shape[0]
    # Gini coefficient:
    return ((np.sum((2 * index - n  - 1) * array)) / (n * np.sum(array)))



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


# test functions


def testIfNodesDuplicates(nodes):
    """
    Tests if there are dupicates in nodes list
    :param nodes: list of node objects
    :return: bool passing or failing test
    """
    for i in range(0, len(nodes)):
        for j in range(0, len(nodes)):
            if nodes[i].nodeid == nodes[j].nodeid and i != j:
                print("ERROR: duplicateNodes!" +  "i: " + str(i) + "; j: " + str(j))
                return False
    return True


def testProbDataSumsTo1(y):
    """
    prob dist must add to 1
    :param y:
    :return:
    """
    s = sum(y)
    print(s)
    return s == 1


main()