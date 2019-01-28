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
import networkClasses

#fields

channelFileName = "data/channels_1-18-18.json"


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
    params, covariance, x, y, c= powerLawExperiment(nodes)
    print("power Law experiment results: ")
    print("alpha: " + str(params[0]))
    print("covariance: ", end="" )
    print(covariance)
    xs = [1,2,3,4,5]
    #c, cProbTotal = findBestC(params[0])
    # print(powerLawFuncC(xs, params[0], c))
    print(c)
    print()
    #gini
    giniCoefficient = giniCoefficientExperiment(nodes)
    print("gini coefficient results:")
    print("gini: " + str(giniCoefficient))

    plt.show()


def findBestC(a):
    target = 1
    bestC = 0
    bestCProb = 0
    currC = 0
    cProb = 0
    y = []
    while (target-cProb) <= (target - bestCProb):
        bestC = currC
        bestCProb = cProb
        currC += .01
        y = powerLawFuncC(range(1, 100000), a, currC)
        cProb = sum(y)
        if cProb > 1: break
    print(y)
    print(bestC, bestCProb)
    return bestC, bestCProb

def powerLawExperiment(nodes):
    """
    The power law experiment fits a regression to the data and plots the data and the regression power law curve
    :return: alpha, covariance
    """
    x, y = getChannelFreqData(nodes)
    x, y, nodeNumber = removeOutliers(x, y, len(nodes))
    yProb = freqDataToProbData(y, nodeNumber)
    simpleFreqPlot(x, yProb)
    params, covariance = powerLawRegressionParam(x, yProb)
    c, cProb = findBestC(params[0])
    params = [params[0], c]
    plotPowLaw(powerLawFuncC, params, (1, 1000, 1))
    plt.autoscale()
    return params, covariance, x, y, c

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

def plotPowLaw(func, params, rangeTup):
    """
    plot a function over x range define in rangeTup
    :param func: function that maps x->y
    :param rangeTup: rangeTup where (starting, ending, discrete_interval)
    :return: None
    """
    rr = np.arange(rangeTup[0], rangeTup[1], rangeTup[2])
    plt.plot(rr, func(rr, params[0], params[1]))
    plt.title("power law reg. on channel freq. prob. distribution")
    plt.xlabel("channels")
    plt.ylabel("probability")
    # plt.box(on=True)
    # plt.figtext(.45, .85, "y = x^(-" + str(a) + ")")
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


def removeOutliers(x, y, nodeNumber):
    """
    Removing outliers to get a better fit
    :param x:
    :param y:
    :return:
    """

    x= x[0:-5]
    y = y[0:-5]
    return x, y, nodeNumber

def powerLawRegressionParam(x, y):
    """
    Performs a regression analysis on power law function
    :return:
    """
    alpha, covariance = optimize.curve_fit(powerLawFunc, x, y)
    return alpha, covariance


def powerLawFunc(xs, a):
    """
    Power law function.
    :param xs: x list of data
    :param a: alpha
    :return: y
    """
    #c is chosen so that integral 0<x<inf = 1.
    y = []
    constantY = dict()
    constantY[1] = 0.2038
    constantY[2] = 0.1329
    constantY[3] = 0.1086
    constantY[4] = 0.0713

    for x in xs:
        if x < 5:
            y += [constantY[x]]
        else:
            y += [(pow(x, -1*a))]     #power law
        # y += [c*(pow(x, -1*a))*pow(e, -1*x*b)]        #power law with cutoff
        # y += [pow(e, -1*a*x)]     #exponential
        #
    return y


def powerLawFuncC(xs, a, c):
    """
    Power law function.
    :param xs: x list of data
    :param a: alpha
    :return: y
    """
    #c is chosen so that integral 0<x<inf = 1.
    y = []
    constantY = dict()
    constantY[1] = 0.2038
    constantY[2] = 0.1329
    constantY[3] = 0.1086
    constantY[4] = 0.0713

    for x in xs:
        if x < 5:
            y += [constantY[x]]
        else:
            y += [(c*pow(x, -1*a))]     #power law
        # y += [c*(pow(x, -1*a))*pow(e, -1*x*b)]        #power law with cutoff
        # y += [pow(e, -1*a*x)]     #exponential
        #
    return y

def c_calculation(alpha, xmin=1):
    c = (alpha-1)*pow(xmin, alpha-1)
    return c


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

if __name__ == "__main__":
    main()