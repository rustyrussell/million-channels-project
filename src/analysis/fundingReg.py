from matplotlib import pyplot as plt
from scipy import optimize
from common import graph as g, utility
from analysis import powerLawReg

def channelCapacityInNode(nodes, graph=False, powerReg=False):
    #looking at corr value of otherNode in channel and channel capacity
    interval = 100000
    rankingSize = 10
    ysOther = []
    ysPer = []
    perList = [[] for i in range(0, rankingSize)]
    connList = [[] for i in range(0, rankingSize)]
    for n in nodes:
        if len(n.channels) < rankingSize:
            continue
        n.channels.sort(key=utility.sortByChanValue, reverse=True)
        for i in range(0, rankingSize):
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
    xs = [i for i in range(0, rankingSize)]
    for i in range (0, len(connList)):
        ysOther += [int(round(sum(connList[i])/(len(connList[i])*interval)))]
        ysPer += [sum(perList[i])/len(perList[i])]

    ysOtherRev = ysOther.copy()
    ysOtherRev.reverse()
    paramsOther, covarianceOther = optimize.curve_fit(linearFunc, xs, ysOtherRev)
    paramsPer, covariancePer = powerLawReg.powerLawRegressionParam(xs, ysPer)

    if graph:
        #plot powerlaw
        plt.rcParams.update({'font.size': 14})
        fig, ax = plt.subplots()
        bounds = (0, rankingSize, 1)
        g.simpleFreqPlot(xs, ysPer)
        xaxis = "channel in node by capacity (top " + str(rankingSize) + " greatest to least)"
        yaxis = "% of node capacity"
        g.plotFunction(powerLawReg.powerLawFunc, paramsPer, bounds, xaxis, yaxis)
        plt.title("channels by % of node cap. (nodes >= " + str(rankingSize) + " channels)")
        props = dict(boxstyle="round", facecolor="wheat", alpha=.5)
        text = r'$\alpha$' + " = " + str(paramsPer[0])[0:5] + "\n" + r'$\beta$' + " = " + str(paramsPer[1])[0:5] + "\n" + "c = " + str(paramsPer[2])[0:5] 
        ax.text(.75, .95, text, fontsize=14, verticalalignment="top", transform=ax.transAxes, bbox=props)
        plt.autoscale()
        plt.show()

        #plot linear
        fig, ax = plt.subplots()
        bounds = (0, rankingSize, 1)
        g.simpleFreqPlot(xs, ysOtherRev)
        xaxis = "channel in node by capacity (top " + str(rankingSize) + " least to greatest)"
        yaxis = "cap. of connected node - chan. cap."
        g.plotFunction(linearFunc, paramsOther, bounds, xaxis, yaxis)
        plt.title("chan. cap. to connected cap. (nodes >= " + str(rankingSize) + " channels)")
        props = dict(boxstyle="round", facecolor="wheat", alpha=.5)
        text = r'$\alpha$' + " = " + str(int(round(paramsOther[0]))) + "\n" + r'$\beta$' + " = " + str(int(round(paramsOther[1]))) 
        ax.text(.10, .95, text, fontsize=14, verticalalignment="top", transform=ax.transAxes, bbox=props)
        plt.autoscale()
        plt.show()

    return (paramsOther, covarianceOther), (paramsPer, covariancePer, ysPer), rankingSize


def nodeCapacityInNetPowLaw(scalingUnits, nodes, graph=False):
    #power law of freq of capacity -> capacity
    yfreq = []
    interval = 1000000
    for n in nodes:
        v = n.value
        if v > 0:
            scaledV = int(round(v/interval))
            yfreq += [0 for i in range(len(yfreq), scaledV+1)]
            yfreq[scaledV] += 1
    ys = yfreq
    #now add sliding window
    slide = 100
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
        plt.rcParams.update({'font.size': 14})
        fig, ax = plt.subplots()
        g.simpleFreqPlot(xs, yProb)
        bounds = (1, max(xs), 1)
        xaxis = "capacity * 10^-6 satoshis (smoothed distribution)"
        yaxis = "probability"
        g.plotFunction(powerLawReg.powerLawFunc, params, bounds, xaxis, yaxis)
        plt.title("prob. dist. of total capacity of channels of a node")
        props = dict(boxstyle="round", facecolor="wheat", alpha=.5)
        text = r'$\alpha$' + " = " + str(params[0])[0:5] + "\n" + r'$\beta$' + " = " + str(params[1])[0:5] + "\n" + "c = " + str(params[2])[0:5] 
        ax.text(.75, .95, text, fontsize=14, verticalalignment="top", transform=ax.transAxes, bbox=props)
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

