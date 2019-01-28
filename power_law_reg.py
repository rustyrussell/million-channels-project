"""
This program aims to test two centralization measures for modeling the lightning network: gini coefficient and power log

The latest commit only tests power_law. gini coefficient has not been done yet.
"""

from matplotlib import pyplot as plt
from scipy import optimize
from math import pow
import numpy as np
import utility

#fields

channelFileName = "data/channels_1-18-18.json"


#functions

def main():
    """
    Opens json file, creates node and channel objects objects, runs gini coefficient and power log tests.
    :return:
    """
    fp = open(channelFileName)
    jn = utility.loadJson(fp)

    #experiments
    nodes, channels = utility.jsonToObject(jn)
    #power law
    params, covariance, x, y, c= powerLawExperiment(nodes)
    print("power Law experiment results: ")
    print("alpha,beta,c: " + str(params[0]) + "," + str(params[1]) + "," + str(c))
    print("covariance: ", end="" )
    print(covariance)
    xs = [1,2,3,4]
    ys = powerLawFuncC(xs, params[0], params[1],c)
    print("x=1-4: ", end="")
    print(ys)


#regression and power law function
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
    c, cProb = findBestC(params[0], params[1])
    params = [params[0], params[1], c]
    plotPowLaw(powerLawFuncC, params, (0, 1000, 1))
    plt.autoscale()
    return params, covariance, x, y, c


def powerLawFunc(xs, a, b):
    """
    Power law function for regression
    :param xs: x list of data
    :param a: alpha
    :return: y
    """
    #c is chosen so that integral 0<x<inf = 1.
    y = []
    for x in xs:
        y += [(pow(x+b, -1*a))]
    return y


def powerLawFuncC(xs, a, b, c):
    """
    scaled power law function where discrete integral from 1<=x<inf ~= 1 from a custom c value.
    :param xs: x list of data
    :param a: alpha
    :return: y
    """
    y = []
    for x in xs:
        y += [(c*pow(x+b, -1*a))]
    return y

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

    # x= x[0:-5]
    # y = y[0:-5]
    return x, y, nodeNumber

def powerLawRegressionParam(x, y):
    """
    Performs a regression analysis on power law function
    :return:
    """
    alpha, covariance = optimize.curve_fit(powerLawFunc, x, y)
    return alpha, covariance


def findBestC(a, b):
    """
    Finds best C by finding the C that leads to a prob closest to and not above 1 with an accuracy of .01 for c
    :param a:
    :param b:
    :return:
    """
    target = 1
    bestC = 0
    bestCProb = 0
    currC = 0
    cProb = 0
    while (target-cProb) <= (target - bestCProb):
        bestC = currC
        bestCProb = cProb
        currC += .01
        y = powerLawFuncC(range(1, 100000), a, b, currC)
        cProb = sum(y)
        if cProb > 1: break
    return bestC, bestCProb





#graphing

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


def plotPowLaw(func, params, rangeTup):
    """
    plot a function over x range define in rangeTup
    :param func: function that maps x->y
    :param rangeTup: rangeTup where (starting, ending, discrete_interval)
    :return: None
    """
    rr = np.arange(rangeTup[0], rangeTup[1], rangeTup[2])
    plt.plot(rr, func(rr, params[0], params[1], params[2]))
    plt.title("power law reg. on channel freq. prob. distribution")
    plt.xlabel("channels")
    plt.ylabel("probability")
    # plt.box(on=True)
    # plt.figtext(.45, .85, "y = x^(-" + str(a) + ")")



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