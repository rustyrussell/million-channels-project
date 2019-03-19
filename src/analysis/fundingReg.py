from matplotlib import pyplot as plt
from scipy import optimize
from common import graph as g, utility
from analysis import powerLawReg

def channelCapacityInNode(nodes, graph=False, powerReg=False):
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

    if powerReg:
        paramsPer, covariancePer = powerLawReg.powerLawRegressionParam(xs, ysPer)    #uncomment to see the reg results

        if graph:
            bounds = (0, 30, 1)
            g.simpleFreqPlot(xs, ysPer)
            xaxis = "channel in node ranked by capacity from least to greatest, maximum " + str(chanCount) + " channels"
            yaxis = "channel capacity"
            g.plotFunction(powerLawReg.powerLawFunc, paramsPer, bounds, xaxis, yaxis)
            plt.autoscale()
            plt.show()

    if graph:
        bounds = (0, 30, 1)
        g.simpleFreqPlot(xs, ysPer)
        xaxis = "channel in node ranked by capacity from least to greatest, maximum " + str(chanCount) + " channels"
        yaxis = "total capacity of other node in channel - capacity in channel"
        g.plotFunction(linearFunc, paramsOther, bounds, xaxis, yaxis)
        plt.autoscale()
        plt.show()

    return (paramsOther, covarianceOther), (paramsPer, covariancePer, ysPer), chanCount


def nodeCapacityInNetPowLaw(nodes, graph=False):
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

    if graph:
        print(params)
        g.simpleFreqPlot(xs, yProb)
        bounds = (-1, 30000, 1)
        xaxis = "capacity / 10^6 satoshis ; slide = " + str(slide)
        yaxis = "prob"
        g.plotFunction(powerLawReg.powerLawFunc, params, bounds, xaxis, yaxis)
        plt.autoscale()
        plt.show()

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

