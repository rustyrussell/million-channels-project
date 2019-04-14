"""
This program aims to test two centralization measures for modeling the lightning network: gini coefficient and power log

The latest commit only tests power_law. gini coefficient has not been done yet.
"""

from matplotlib import pyplot as plt
from scipy import optimize
from math import pow
from common import utility, graph as g
import random



#functions

#regression and power law function
def powerLawExperiment(nodes, reg=True, params=None, graph=False, completeNetwork=False, bounds=(0, 1000, 1)):
    """
    The power law experiment fits a regression to the data and plots the data and the regression power law curve
    :return: alpha, covariance
    """
    if completeNetwork:
        utility.setMaxChannels(nodes)
    x, y = getChannelFreqData(nodes)
    yProb = freqDataToProbData(y, len(nodes))
    covariance = None
    if reg:  #for doing regression
        params, covariance = powerLawRegressionParam(x, yProb)
        params = [params[0], params[1], params[2]]
    if graph:    #for plotting power law curve from experiment against new nodes scatterplot (called in build network)
        fig, ax = plt.subplots()
        g.simpleFreqPlot(x, yProb, plot=plt)
        g.plotFunction(powerLawFunc, params, bounds, xaxisDescription="channels", yaxisDescription="probability", plot=plt)
        plt.title("prob. dist. of a node with X amount of channels. Power Law fitted to data.")
        props = dict(boxstyle="round", facecolor="wheat", alpha=.5)
        text = r'$\alpha$' + " = " + str(params[0])[0:5] + "\n" + r'$\beta$' + " = " + str(params[1])[0:5] + "\n" + "c = " + str(params[2])[0:5] 
        ax.text(.75, .95, text, fontsize=14, verticalalignment="top", transform=ax.transAxes, bbox=props)
        plt.autoscale()
        plt.show()
    return params, covariance, x, yProb


def boundIntergral(func, params, a, b):
    return func(b, *params) - func(a, *params)

def powLawIntegral(x, a, b, c):
    y = (c*pow(x+b, (-1 * a)+1) / ((-1 * a)+1))
    return y


def inversePowLawIntegral(y, a, b, c):
    lower = (((y) * ((-1* a)+1))/c)
    upper = (1/((-1*a)+1))
    x = pow(lower, upper) - b
    return x

def randToPowerLaw(params, bound):
    lower = powLawIntegral(bound[0],  params[0], params[1], params[2])
    upper = powLawIntegral(bound[1],  params[0], params[1], params[2])
    r = random.uniform(lower, upper)
    x = inversePowLawIntegral(r, params[0], params[1], params[2])
    return x


def powerLawFunc(xs, a, b, c):
    """
    Power law function for regression
    :param xs: x list of data
    :param a: alpha
    :return: y
    """
    #c is chosen so that integral 0<x<inf = 1.
    y = []
    for x in xs:
        y += [(c*pow(x+b, -1*a))]
    return y

def inversePowLawFunc(ys, a, b):
    """
    The reverse pow law is used for randomly generating the network
    :param ys: y values
    :param a: alpha
    :param b: beta
    :param c: c scaling constant
    :return: x's
    """
    xs = []
    for y in ys:
        xs += [(y)**(1/a) - b]
    return xs


def culmPowLaw(p, a, b):
    #this is discrete rudimentary integration
    ch = 1  #num of channels
    s = 0
    y = 0
    while s < p:
        s += y
        y = powerLawFunc([ch], a, b)[0]
        ch += 1
    return ch - 1

def getChannelFreqData(nodes):
    """
    x axis is # of channels
    y axis is # of nodes
    :param nodes: list of nodes (sorted)
    :return: (x, y) in the form of an x list and y list (easy format for graphing in matplotlib)
    """
    channelCountList = []
    for node in nodes:
        channelCountList += [node.maxChannels]
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

def powerLawRegressionParam(x, y):
    """
    Performs a regression analysis on power law function
    :return:
    """
    alpha, covariance = optimize.curve_fit(powerLawFunc, x, y)
    return alpha, covariance


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

