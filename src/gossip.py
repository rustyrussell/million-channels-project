"""
Generates lightning gossip
"""

from common import wif
from common import utility
import buildNetwork
import pickle
import os
import subprocess
from config import *
import signal
from lightning import LightningRpc
from bitcoin.rpc import Proxy
from bitcoin import SelectParams
import time
import threading

def main():
    network = loadNetwork(buildNetwork.networkSaveFile)
    network.setBaseDataDir(lightingExpBaseDir)
    SelectParams("regtest")
    brpc = Proxy(btc_conf_file=regtestConfPath)
    genAddr = brpc.getnewaddress()
    genAddr = str(genAddr)
    #fundBitcoind(brpc, genAddr, 1000)  # creates 100 blocks
    channelSeq = genChanCreateSeq(network)
    # #delete
    # nodes = []
    # j = 0
    # for c in channelSeq:
    #     if j == 5: break
    #     else: j+=1
    #     node1 = c.node1
    #     node2 = c.node2
    #     if node1 not in nodes: nodes += [node1]
    #     if node2 not in nodes: nodes += [node2]
    # channelSeq = channelSeq[0:5]
    # #delete
    watcherpid = startWatcherNode(network)

    try:
        createAllNodes(network, nodes=None)
        fundAllLightningAddrs(network, brpc, genAddr, nodes=None)
        brpc.call("generatetoaddress", 6, genAddr)  # 6 confirmations
        genAllChannels(network, channelSeq, brpc, genAddr)

        watcherRPC = network.watcherRPC
        ch = watcherRPC.listchannels()
        ns = watcherRPC.listnodes()
        print("all watched channels: ")
        print(ch)
        print("all watched nodes: ")
        print(ns)

        nodes = network.fullConnNodes + network.partConnNodes
        for node in nodes:
            killLightningNode(node)


        os.kill(int(watcherpid), signal.SIGTERM)    #kill watcher

    # except:  #kill all nodes
    finally:
        nodes = network.fullConnNodes + network.partConnNodes
        for node in nodes:
            killLightningNode(node)

        os.kill(int(watcherpid), signal.SIGTERM)  # kill watcher



def createAllNodes(network, nodes=None):
    """
    we turn nodes on and off so that the address can be generated. This way coins can be allocated to those addresses on regtest chain
    :param network:
    :param nodes:
    :return:
    """
    threads = []
    if nodes == None:
        nodes = network.fullConnNodes + network.partConnNodes
    for node in nodes:
        exists = os.path.exists(network.baseDataDir + str(node.nodeid) + "/")
        if exists:
            thread = threading.Thread(target=startNewLightningNode, args=(network, node, False))
        else:
            thread = threading.Thread(target=startNewLightningNode, args=(network, node, True))
        threads += [thread]

    for t in threads:
        t.start()

    #thread loop for killing all. Do this after multithreading fundAllLightningAddr and genAllChannels
    # killLightningNode(node)


    for t in threads:
        t.join()


def fundAllLightningAddrs(network, brpc, genAddr, nodes=None):
    """
    send money to lightning addresses and create blocks
    :param network:
    :param brpc:
    :return:
    """
    if nodes == None:
        nodes = network.fullConnNodes + network.partConnNodes
    j = 0
    for node in nodes:
        if j == 2000:               #TODO: this is very unsophisticated. We put 2000 tx in each block.
            brpc.call("generatetoaddress", 1, genAddr)
            j = 0
        else:
            j += 1
        addr = node.addrList[0]   #just take first address. There has to be an address because of startNewLightningNode
        c = node.channelCount
        fee = 100    # satoshis
        amount = c*100000 + c*fee
        while True:
            try:
                brpc.sendtoaddress(addr, amount)
                break
            except BrokenPipeError:
                pass
    if len(brpc.getrawmempool(verbose=True)) > 0:   # if mempool not empty
        brpc.call("generatetoaddress", 1, genAddr)


def genAllChannels(network, channels, brpc, genAddr):
    """
    Generates all channels
    :param network:
    :param channels:
    :return:
    """

    t = 0
    for channel in channels:
        # if t == 5:
        #     brpc.call("generatetoaddress", 1, genAddr)
        #     t = 0
        # else:
        #     t += 1
        node1 = channel.node1
        node2 = channel.node2
        if node1.on == False:
            startNewLightningNode(network, node1, new=False)
        if node2.on == False:
            startNewLightningNode(network, node2, new=False)
        createChannel(node1, node2)
        if node1.realChannelCount == node1.channelCount:
            killLightningNode(node1)
        if node2.realChannelCount == node2.channelCount:
            killLightningNode(node2)
        brpc.call("generatetoaddress", 1, genAddr)   # gen every time for now. There may be an error where outputs are spent and we are trying to create a new channel


def createChannel(node1, node2):
    """
    Create single channel
    :param node1: node1
    :param node2: node2
    :return:
    """
    rpcNode1 = node1.rpc
    rpcNode2 = node2.rpc
    rpcNode1.connect(node2.id, node2.ip, defaultLightningPort)
    print(node1.ip, node2.ip)
    funds1 = rpcNode1.listfunds()
    funds2 = rpcNode2.listfunds()
    t1 = time.time()
    while len(funds1["outputs"]) == 0 or len(funds2["outputs"]) == 0:
        time.sleep(.25)
        funds1 = rpcNode1.listfunds()
        funds2 = rpcNode2.listfunds()
    t2 = time.time()
    print(funds1)
    print(funds2)
    print("time:", str(t2-t1))
    rpcNode1.fundchannel(node2.id, defaultContractFunding, defaultFeerate, True)
    print("channel successful")
    print()
    node1.addToRealChannelCount()
    node2.addToRealChannelCount()


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



def startWatcherNode(network):
    """
    the watcher node is connected to all nodes and is 127.0.0.1
    :param network: network
    :return:
    """
    os.chdir(lightningdDir)
    watcherDir = network.baseDataDir + "watcher/"
    createLightningNewDataDir(watcherDir)
    subprocess.run(["./lightningd", "--bitcoin-cli", bitcoinCliPath, "--daemon", "--network=regtest", "--lightning-dir=" + watcherDir, "--addr", "127.0.0.1"])
    rpcPath = watcherDir + "lightning-rpc"
    lrpc = LightningRpc(rpcPath)
    info = lrpc.getinfo()
    network.setWatcher(info["id"], lrpc)
    fp = open(watcherDir + "lightningd-regtest.pid", "r")
    pid = ""
    for line in fp:
        pid = line
        break
    return pid



def startNewLightningNode(network, node, new=False):
    """
    when a new lightning node starts we must:
    create a new data directory,
    run lightningd with pointing to lightning-dir in --daemon mode,
    run cli pointing to correct rpc and lightning-dir,
    and save pid of process for killing later on
    :return: bool is successfully started
    """
    nodeid = node.nodeid + 2
    nodeDataDir = network.baseDataDir + str(nodeid) + "/"    # creates new data dir
    createLightningNewDataDir(nodeDataDir)
    node.setDataDir(nodeDataDir)
    os.chdir(lightningdDir)
    ip = getLoopbackIPAddr(nodeid)
    o = subprocess.run(["./lightningd", "--bitcoin-cli", bitcoinCliPath, "--daemon", "--network=regtest", "--lightning-dir="+nodeDataDir, "--addr", ip], capture_output=True)
    rpcPath = nodeDataDir + "lightning-rpc"
    lrpc = LightningRpc(rpcPath)
    lrpc.connect(network.watcherId, host="127.0.0.1", port=9735)    # connect to watcher
    node.setRPC(lrpc)
    node.on = True
    node.setpid()
    if new:
        node.setIP(ip)
        info = lrpc.getinfo()
        node.setId(info["id"])
        addr = lrpc.newaddr()
        node.addToAddrList(addr["address"])


def getLoopbackIPAddr(nodeid):
    """
    Generates loopback ip addr based on nodeid.
    :param nodeid: num
    :return: ip str
    """
    ip = [0, 0, 1]
    i = nodeid + 2    # because we must start at 127.0.0.2. Therefore we add 2 because nodeid starts at 1. 127.0.0.1 is reserved for watching node
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


def createLightningNewDataDir(dir):
    """
    creates a new data directory under baseDataDir/currExperimentDir/experimentName
    :return: bool if directory exists
    """

    exists = os.path.exists(dir)
    if not exists:
        os.mkdir(dir)
    return exists


def killLightningNode(node):
    try:
        os.kill(int(node.pid), signal.SIGTERM)
    except ProcessLookupError:
        pass
    node.on = False



def fundBitcoind(brpc, genAddr, n):
    brpc.call("generatetoaddress", n, genAddr)


assert(checkGossipFields() == True)
if __name__ == "__main__":
    main()



