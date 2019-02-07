"""
Contains measures for the network creation backtracking algo defined in build_network.py
"""
from common import utility
import numpy as np

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

def clustering(nodes):
    """
    calculate clustering which is defined as C(p) = edges_between_neighbors/total_possible_between_neightbors
    :param nodes: nodes
    :return: average clustering
    """
    clusterList = []
    clusterDict = dict()        # building dict just in case we want to return it and use it in the future
    for i in range(0, len(nodes)):
        node = nodes[i]
        cluster = calcNodeCluster(node)
        clusterDict[node.nodeid] = cluster
        clusterList += [cluster]

    s = sum(clusterList)
    averageCluster = s/len(nodes)
    return averageCluster, clusterDict


def calcNodeCluster(node):
    """
    calculate clustering of 1 node
    :param node:
    :return:
    """
    ns = node.neighbors
    n = len(ns)
    if n > 1:
        maxCluster = n * (n - 1) / 2
        cluster = 0
        for neighbor in ns:
            nns = neighbor.neighbors
            for neighborNeighbor in nns:
                if neighborNeighbor != node and neighborNeighbor != neighbor and neighborNeighbor in ns:
                    cluster += 1
        percent = cluster / maxCluster
        return percent
    else:
        return 0


def getClusterFreqData(nodes, clusterDict):
    """
    x axis is # of channels
    y axis is # of nodes
    :param nodes: list of nodes (sorted)
    :return: (x, y) in the form of an x list and y list (easy format for graphing in matplotlib)
    """
    channelCountList = []
    for node in nodes:
        channelCountList += [node]
    x = []
    y = []
    j = 0
    clusterY = []
    channelCountList.sort(key=utility.channelMaxSortKey)
    channelsOfPrevNode = None
    for i in range(0, len(channelCountList)):
        node = channelCountList[i]
        channelsOfNodei = node.maxChannels
        freq = 1
        if channelsOfPrevNode == None:
            x = [channelsOfNodei]
            y = [1]
            clusterY = [clusterDict[node.nodeid]]
            channelsOfPrevNode = channelsOfNodei
        elif channelsOfNodei == channelsOfPrevNode:
            y[j] += 1
            clusterY[j] += clusterDict[node.nodeid]
        else:
            j += 1
            x += [channelsOfNodei]
            y += [1]
            clusterY += [clusterDict[node.nodeid]]
            channelsOfPrevNode = channelsOfNodei

    for c in range(0, len(x)):
        clusterY[c] = clusterY[c] / y[c]

    return x,y,clusterY


def betweennessCentrality(igraph, node):
    bs = igraph.betweenness([node.id])
    print(bs)
    return bs


def shortestPath(network, node1, node2):
    pass





