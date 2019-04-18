from common import crypto, utility
import sys
from bitcoin import SelectParams
from lightning import LightningRpc, RpcError 
from config import *
from random import randint
import time

def main():
    SelectParams("regtest")
    argv = sys.argv    #TODO: add argparse 
    if argv[1] == "route": #input a source and destination
        network, gs = utility.loadNetwork(nodesFile, channelSaveFile)
        if argv[2] == "i":
            si = int(argv[3])  #source
            di = int(argv[4])  #destination
            sPub = getPubKey(si)
            dPub = getPubKey(di)
            print(sPub, dPub)
        else:
            sPub = argv[2]  # source
            dPub = argv[3]  # destination

        fail = False
        try:
            routeL = getRouteLightning(sPub, dPub)
        except RpcError:
            fail = True

        if not fail:
            printLightningRoute(routeL, sPub)
        else:
            print("failed. here is igraph route")
            routesI = getRouteigraph(si, di, network.igraph)
            printigraphRoutes(routesI)

    elif argv[1] == "avg":  #benchmark shortest routes and find the average
        if len(argv) == 4:  
            trials = int(argv[2])
            nodeNum = int(argv[3])
        else:
            raise ValueError("need more arguments")
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
            print(routeL)
            t1 = time.time()
            totHops += len(routeL["route"])
            totTime += t1 - t0
        avgHops = totHops/trials
        avgTime = totTime/trials
        print("avg hops:", avgHops)
        print("avg time:", avgTime)

    elif argv[1] == "all":  #benchmark shortest routes and find the average
        if len(argv) == 4:  
            lower = int(argv[2])
            upper = int(argv[3])
        else:
            raise ValueError("need more arguments")
        ifailures = 0 
        failures = []
        totTime = 0
        totHops = 0
        pubkeylist = []
        for i in range(lower, upper+1):
            pubkeylist += [getPubKey(i)]
    
        for i in range(0, len(pubkeylist)):
            sPub = pubkeylist[i]
            for j in range(i+1, len(pubkeylist)):
                if i != j:
                    dPub = pubkeylist[j]
                    try:
                        routeL = getRouteLightning(sPub, dPub)
                    except RpcError:
                        ifailures += 1
                        failures += [(i, j)]
            print("done with", i)

        if ifailures > 0:
            network, gs = utility.loadNetwork(nodesFile, channelSaveFile)
      
        for f in failures:
            print("cannot find", f[0], "-->", f[1])
            routesI = getRouteigraph(f[0], f[1], network.igraph)
            printigraphRoutes(routesI)
            

def getPubKey(nodeid):
    pub = bytearray(crypto.compPubKey(crypto.makeSinglePrivKeyNodeId(nodeid))).hex()
    return pub


def getRouteLightning(source, dest):
    lrpc = LightningRpc(lightningrpc)
    route = lrpc.getroute(dest, 1, 0, fromid=source)
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
