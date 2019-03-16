from matplotlib import pyplot as plt
from scipy import optimize
import numpy as np
from common import graph, utility
from analysis import powerLawReg

def channelCapacityInNode(nodes, channels):
    #looking at corr value of otherNode in channel and channel capacity
    chanCount = 15
    ys = []
    ysPer = []
    perList = [[] for i in range(0, chanCount)]
    connList = [[] for i in range(0, chanCount)]
    for n in nodes:
        n.channels.sort(key=utility.sortByChanValue, reverse=True)
        for i in range(0, chanCount):
            if i == n.channelCount:
                break
            else:
                chan = n.channels[i]
                if n == chan.node1:
                    other = chan.node2
                else:
                    other = chan.node1
                connList[i] += [other.value - chan.value]
                perList[i] += [chan.value/n.value]
                # connList[i] += [other.channelCount - 1]
    xs = [i for i in range(0, chanCount, 1)]
    for i in range (0, len(connList)):
        ys += [sum(connList[i])/len(connList[i])]
        ysPer += [sum(perList[i])/len(perList[i])]

    paramsOther, covarianceOther = optimize.curve_fit(linearFunc, xs, ys)
    paramsPer, covariancePer = None, None
    # paramsPer, covariancePer = powerLawReg.powerLawRegressionParam(xs, ysPer)    #uncomment to see the reg results

    # # # uncomment to graph
    bounds = (0, 30, 1)
    # graph.simpleFreqPlot(xs, ysPer)
    xaxis = "channel in node ranked by capacity from least to greatest, maximum " + str(chanCount) + " channels"
    yaxis = "total capacity of other node in channel - capacity in channel"
    # plotFunding(linearFunc, params, bounds, xaxis, yaxis)
    # plt.autoscale()
    # plt.show()

    return (paramsOther, covarianceOther), (paramsPer, covariancePer, ysPer), chanCount


def nodeCapacityInNetPowLaw(nodes, channels):
    #power law of freq of capacity -> capacity
    yfreq = []
    interval = 100000
    for n in nodes:
        v = n.value
        if v > 0:
            scaledV = round(v/interval)
            yfreq += [0 for i in range(len(yfreq), scaledV+1)]
            yfreq[scaledV] += 1
    ys = yfreq
    #now add sliding window
    slide = 50
    ytup = (ys[i:] for i in range(0, slide))
    yzip = zip(*ytup)
    yset = list(yzip)
    ysWithZeros = [sum(yset[i]) for i in range(0, len(yset))]
    ys = []
    xs = []
    for i in range(0, len(ysWithZeros)):
        y = ysWithZeros[i]
        if y > 0:
            ys += [y]
            xs += [i]
    yProb = powerLawReg.freqDataToProbData(ys, sum(ys))
    params, covariance = powerLawReg.powerLawRegressionParam(xs, yProb)
    c, cProb = powerLawReg.findBestC(params[0], params[1])
    params = [params[0], params[1], c]

    # # # uncomment to graph:
    # print(params)
    # graph.simpleFreqPlot(xs, yProb)
    # bounds = (-1, 30000, 1)
    # xaxis = "capacity / 10^6 satoshis ; slide = " + str(slide)
    # yaxis = "prob"
    # plotFunding(powerLawReg.powerLawFuncC, params, bounds, xaxis, yaxis)
    # plt.autoscale()
    # plt.show()

    return params, covariance, interval



def getTotalNetworkSatoshis(targetNetwork):
    nodes = targetNetwork.getNodes()
    totVal = sum([nodes[i].value for i in range(0, len(nodes))])
    return totVal


def linearFunc(xs, a, b):
    ys = []
    for x in xs:
        ys += [(a*x) + b]
    return ys

def plotFunding(func, params, rangeTup, xaxis, yaxis):
    """
    plot a function over x range define in rangeTup
    :param func: function that maps x->y
    :param rangeTup: rangeTup where (starting, ending, discrete_interval)
    :return: None
    """
    rr = np.arange(rangeTup[0], rangeTup[1], rangeTup[2])
    plt.plot(rr, func(rr, *params))
    plt.xlabel(xaxis)
    plt.ylabel(yaxis)




#OLD EXPERIMENTS: 
# corr between max channel cap and channel count
# maxX = 0
# for n in nodes:
#     x = n.channelCount
#     if x > maxX:
#         maxX = x
# maxCapChan = [[] for i in range(0, maxX+1)]
# xs = []
# ys = []
# for n in nodes:
#     if n.channelCount > 100:
#         print(n.channelCount)
#         maxCap = 0
#         for c in n.channels:
#             if c.value > maxCap:
#                 maxCap = c.value
#         xs += [n.channelCount]
#         ys += [maxCap]
#         break
#

# #looking at avg max cap channel capacity and channel count
# maxX = 0
# for n in nodes:
#     x = n.channelCount
#     if x > maxX:
#         maxX = x
# maxCapChan = [[] for i in range(0, maxX+1)]
# xs = []
# ys = []
# for n in nodes:
#     print(n.channelCount)
#     maxCap = 0
#     for c in n.channels:
#         if c.value > maxCap:
#             maxCap = c.value
#     maxCapChan[n.channelCount] += [maxCap]
# for i in range (0, len(maxCapChan)):
#     maxs = maxCapChan[i]
#     if len(maxs) > 0 and i < 30:
#         xs += [i]
#         ys += [sum(maxs)/len(maxs)]


# #num channels node1 and node2 have -> capacity between them    #NO CORRELATION!
# for c in channels:
#     n1 = c.node1
#     n2 = c.node2
#     y = c.value // 10000
#     x = n1.channelCount + n2.channelCount
#     ys += [y]
#     xs += [x]

# #nodes with channel count withing range -> avg spread between capacity of channels in the nodes in that channel count range   #NO CORRELATION
# maxX = 0
# for n in nodes:
#     x = n.channelCount
#     if x > maxX:
#         maxX = x
# variPerN = [[] for i in range(0, maxX+1)]
# for n in nodes:
#     chans = n.channels
#     if len(chans) < 100:
#         avg = n.value/len(chans)
#         vari = sum(abs(chans[i].value - avg) for i in range(0, len(chans)))/len(chans)
#         variPerN[len(chans)] += [vari]
# xs = []
# ys = []
# varislst = []
# for i in range(0, len(variPerN)):
#     varis = variPerN[i]
#     if len(varis) > 0:
#         varislst += varis
#     if i % 10 == 0:
#         if len(varislst) > 0:
#             xs += [i]
#             ys += [sum(varislst)/len(varislst)]
#             varislst = []

# # # # taking the avg diff from the mean    #noise doesn't work
# for n in nodes:
#     x = n.channelCount
#     y = n.value/x
#     diffFromMean[x] += [y]
#     xs += [x]
#     ys += [y]
# ys = []
# xs = []
# scaling = 100000
# for i in range(0, len(diffFromMean)):
#     n = len(diffFromMean[i])
#     if n > 40:
#         s = sum(diffFromMean[i])
#         avg = s / n
#         diff = []
#         for v in diffFromMean[i]:
#             diff += [abs(v - avg)]
#         diffSum = sum(diff)
#         diffAvg = diffSum/n
#         ys += [diffAvg/scaling]
#         xs += [i]

# #looking at corr value of otherNode in channel and channel capacity for a given chanCount
# chanCount = 10
# xs = []
# ys = []
# connList = [[] for i in range(0, chanCount)]
# for n in nodes:
#     if n.channelCount == chanCount:
#         n.channels.sort(key=utility.sortByChanValue, reverse=False)
#         for i in range(0, n.channelCount):
#             chan = n.channels[i]
#             if n == chan.node1:
#                 other = chan.node2
#             else:
#                 other = chan.node1
#             connList[i] += [other.value - chan.value]
#             # connList[i] += [other.channelCount - 1]
#
# xs = [i for i in range(1, chanCount+1)]
# for i in range (0, len(connList)):
#     ys += [sum(connList[i])/len(connList[i])]

# #looking at avg max cap channel capacity and channel count
# maxX = 0
# for n in nodes:
#     x = n.channelCount
#     if x > maxX:
#         maxX = x
# chanCount = 15
# xs = []
# ys = []
# connList = [[] for i in range(0, chanCount)]
# for n in nodes:
#     if n.channelCount == chanCount:
#         n.channels.sort(key=utility.sortByChanValue, reverse=False)
#         for i in range(0, n.channelCount):
#             chan = n.channels[i]
#             if n == chan.node1:
#                 other = chan.node2
#             else:
#                 other = chan.node1
#             connList[i] += [other.value - chan.value]
#             # connList[i] += [other.channelCount - 1]
#
# xs = [i for i in range(1, chanCount+1)]
# for i in range (0, len(connList)):
#     ys += [sum(connList[i])/len(connList[i])]
