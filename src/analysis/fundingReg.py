from matplotlib import pyplot as plt
from scipy import optimize
import numpy as np
from common import graph

def fundingRegExperiment(nodes, channels):
    """
    Find if there is a correlation between # of channels and total value
    :param channels:
    :return:
    """
    maxX = 0
    for n in nodes:
        x = n.channelCount
        if x > maxX:
            maxX = x
    diffFromMean = [[] for i in range(0, maxX+1)]



    # # run funding
    #first reg is len(node.channels) -> sum(node.channels[i].cap)     linear reg.
    ys = []
    xs = []
    for n in nodes:
        x = n.channelCount
        y = n.value/x
        diffFromMean[x] += [y]
        xs += [x]
        ys += [y]


    # # # taking the avg diff from the mean    #noise doesn't work
    ys = []
    xs = []
    scaling = 100000
    for i in range(0, len(diffFromMean)):
        n = len(diffFromMean[i])
        if n > 40:
            s = sum(diffFromMean[i])
            avg = s / n
            diff = []
            for v in diffFromMean[i]:
                diff += [abs(v - avg)]
            diffSum = sum(diff)
            diffAvg = diffSum/n
            ys += [diffAvg/scaling]
            xs += [i]


    # #num channels node1 and node2 have -> capacity between them    #NO CORRELATION!
    # for c in channels:
    #     n1 = c.node1
    #     n2 = c.node2
    #     y = c.value // 10000
    #     x = n1.channelCount + n2.channelCount
    #     ys += [y]
    #     xs += [x]

    #what if we tried to correlate "economic value" with channel. How do I even



    params, covariance = optimize.curve_fit(linearFunc, xs, ys)
    print(covariance)
    bounds = (0, 75, 1)
    graph.simpleFreqPlot(xs, ys)
    plotFunding(linearFunc, params, bounds)
    plt.autoscale()
    plt.show()

    return params, covariance


def linearFunc(xs, a, b):
    ys = []
    for x in xs:
        ys += [(a*x) + b]
    return ys

def plotFunding(func, params, rangeTup):
    """
    plot a function over x range define in rangeTup
    :param func: function that maps x->y
    :param rangeTup: rangeTup where (starting, ending, discrete_interval)
    :return: None
    """
    rr = np.arange(rangeTup[0], rangeTup[1], rangeTup[2])
    plt.plot(rr, func(rr, params[0], params[1]))
    plt.xlabel("channel count")
    plt.ylabel("noise to avg capacity")
