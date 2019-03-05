from common import crypto, utility
import sys
from bitcoin import SelectParams
from lightning import LightningRpc
from config import *
from random import randint
import time

def main():
    SelectParams("regtest")
    network, gs = utility.loadNetwork(nodeSaveFile, channelSaveFile)
    argv = sys.argv
    if len(argv) == 3: #input a source and destination
        si = int(argv[1])  #source
        di = int(argv[2])  #destination
        sPub = getPubKey(si)
        dPub = getPubKey(di)
        routeL = getRouteLightning(sPub, dPub)
        printLightningRoute(routeL, sPub)
        routesI = getRouteigraph(si, di, network.igraph)
        printigraphRoutes(routesI)

    elif len(argv) == 1:  #benchmark 1000 shortest routes and find the average
        trials = 1000
        nodeNum = len(network.getNodes())
        totTime = 0
        totHops = 0
        for i in range(0, trials):
            r1 = randint(0, nodeNum-1)
            r2 = randint(0, nodeNum-1)
            while r2 == r1:
                r2 = randint(0, nodeNum - 1)
            sPub = getPubKey(r1)
            dPub = getPubKey(r2)
            t0 = time.time()
            routeL = getRouteLightning(sPub, dPub)
            t1 = time.time()
            totHops += len(routeL["route"])
            totTime += t1 - t0
        avgHops = totHops/trials
        avgTime = totTime/trials
        print("avg hops:", avgHops)
        print("avg time:", avgTime)


def getPubKey(nodeid):
    pub = bytearray(crypto.compPubKey(crypto.makeSinglePrivKeyNodeId(nodeid))).hex()
    return pub


def getRouteLightning(source, dest):
    lrpc = LightningRpc(lightningrpc)
    route = lrpc.getroute(dest, 10000, 20, fromid=source)
    return route


def getRouteigraph(si, di, ig):
    route = ig.get_shortest_paths(si, to=[di])
    return route


def printigraphRoutes(routes):
    print("igraph routes: ")
    for i in range(0, len(routes)):
        print("route", str(i) + ":")
        for j in range(0, len(routes[i])):
            print("    " + str(j) + ": " + str(getPubKey(routes[i][j])))


def printLightningRoute(route, source):
    print("lightning route:")
    print("    " + "0: " + source)
    hops = route["route"]
    for i in range(0, len(hops)):
        print("    " + str(i+1) + ": " + str(hops[i]["id"]))


main()
