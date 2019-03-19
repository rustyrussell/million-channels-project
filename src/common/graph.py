from igraph import drawing
from matplotlib import pyplot as plt
import numpy as np


def igraphDraw(ig, bbox=(0,0,2000,2000)):
    """
    draw graph using igraph obj
    :param ig: igraph obj
    :return:
    """
    ig.vs["label"] = ig.vs.indices
    drawing.plot(ig, bbox=bbox)


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


def plotFunction(func, params, rangeTup, xaxisDescription, yaxisDescription):
    """
    plot a function over x range define in rangeTup
    :param func: function that maps x->y
    :param rangeTup: rangeTup where (starting, ending, discrete_interval)
    :return: None
    """
    rr = np.arange(rangeTup[0], rangeTup[1], rangeTup[2])
    plt.plot(rr, func(rr, *params))
    plt.xlabel(xaxisDescription)
    plt.ylabel(yaxisDescription)

