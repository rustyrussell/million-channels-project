"""
Generates lightning gossip
"""


import wif
import utility
import buildNetwork
import pickle
import os
import subprocess
from config import *
import signal


def main():
    network = loadNetwork(buildNetwork.networkSaveFile)
    network.setBaseDataDir(baseDataDir + currExperimentDir)
    channelSeq = genChanCreateSeq(network)

    testNode1 = channelSeq[0].node1
    print("nodeid: " + str(testNode1.nodeid))
    startNewLightningNode(network, testNode1)
    print("ip: " + testNode1.ip)
    print("pid: " + str(testNode1.pid))
    killLightningNode(testNode1)
    testNode2 = channelSeq[0].node2
    print("nodeid: " + str(testNode2.nodeid))
    startNewLightningNode(network, testNode2)
    print("ip: " + testNode2.ip)
    print("pid: " + str(testNode2.pid))
    killLightningNode(testNode2)


    print(channelSeq)


def loadNetwork(networkFilename):
    fp = open(networkFilename, "rb")
    network = pickle.load(fp)
    return network

def genPrivKey(pk):
    """
    convert pk num into WIF
    :param pk:
    :return:
    """
    wifPK = wif.privToWif(pk)
    return wifPK


def testGenPrivKey(pk):
    wifpk = genPrivKey(pk)
    print(wifpk)
    fullPK = wif.wifToPriv(wifpk)
    print(fullPK)
    return wifpk


def genChanCreateSeq(network):
    """
    Generates the order of channel creation
    :param network:
    :return:
    """
    nodes = network.fullConnNodes + network.partConnNodes
    nodes.sort(key=utility.sortByChannelCount)   # from low to high channel count
    channels = []
    for node in nodes:
        myChan = node.channels
        for ch in myChan:
            if ch in channels:
                continue
            else:
                channels += [ch]
    return channels



def startNewLightningNode(network, node):
    """
    when a new lightning node starts we must:
    create a new data directory,
    run lightningd with pointing to lightning-dir in --daemon mode,
    run cli pointing to correct rpc and lightning-dir,
    and save pid of process for killing later on
    :return: bool is successfully started
    """
    nodeid = node.nodeid
    nodeDataDir = network.baseDataDir + str(nodeid) + "/"    # creates new data dir
    print(nodeDataDir)
    createLightningNewDataDir(nodeDataDir)
    node.setDataDir(nodeDataDir)
    os.chdir(lightningdDir)
    print(lightningdDir)
    ip = getLoopbackIPAddr(nodeid)
    node.setIP(ip)
    subprocess.run(["./lightningd", "--bitcoin-cli", bitcoinCliPath, "--daemon", "--network=regtest", "--lightning-dir="+nodeDataDir, "--addr", ip])
    node.setpid()
    rpcPath = nodeDataDir + "lightning-rpc"
    checkRPCConnection(rpcPath)   # I don't think this will work because it takes a few seconds before rpc connections work



def getLoopbackIPAddr(nodeid):
    """
    Generates loopback ip addr based on nodeid.
    :param nodeid: num
    :return: ip str
    """
    ip = [0, 0, 1]
    i = nodeid + 1    # because we must start at 127.0.0.1
    j = -1
    while i != 0:
        b = i % 256
        ip[j] = b
        i = i // 256
        j -= 1
    strIP = "127"
    for b in ip:
        strIP = strIP + "." + str(b)
    return strIP



def checkRPCConnection(rpcLocation):
    """
    checks if a node is up by calling its rpc interface and checking the output
    :param rpcLocation: path
    :return: bool
    """
    pass


def createLightningNewDataDir(dir):
    """
    creates a new data directory under baseDataDir/currExperimentDir
    :return: bool if directory exists
    """

    exists = os.path.exists(dir)
    if not exists:
        os.mkdir(dir)
    return exists


def killLightningNode(node):
    os.kill(int(node.pid), signal.SIGTERM)



assert(checkGossipFields() == True)
if __name__ == "__main__":
    main()

# testGenPrivKey("0000010000000000000000000000000000000000000000000000000000000001")


