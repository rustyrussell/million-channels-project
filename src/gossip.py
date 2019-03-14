import os
from common import utility, crypto
from bitcoin import SelectParams
import hashlib
import time
from copy import deepcopy
from multiprocessing import Process, Lock


def main(config, network=None, gossipSequence=None):
    """
    creates and writes all gossip from the files nodeSaveFile and channelSaveFile defined in config 
    Writes this information to gossipSaveFile
    Each channel has 1 channel annoucement and 2 channel updates. Keys and scids are determined determinisically based on node id.
    """
    utility.setRandSeed(config.randSeed)
    SelectParams("regtest")
    initGossip(config.gossipSaveFile)
    t0 = time.time()
    if network == None:
        network, gossipSequence = utility.loadNetwork(config.nodeSaveFile, config.channelSaveFile)
        t1 = time.time()
        print("loading network complete", t1-t0)

    print(len(network.fullConnNodes))
    t2 = time.time()
    generateAllGossip(network, gossipSequence, config.gossipSaveFile, config.processNum)
    t3 = time.time()
    print("generating/writing gossip complete", t3-t2)

    return network


def generateAllGossip(network, rawGossipSequence, gossipSaveFile, processNum):
    """
    generates and writes all gossip. 
    First use the gossipSequence generated in buildNetwork.py and stored in channelStoreFile to seperate channels into lists of channels 
    Second, based on thread count, create lists of channel allococaters called tindex which helps with load balancing. A sequence of channels is called a bundle. 
    Bundles will be assigned to each process.
    Last, we make a group of processes running genGossip
    """
    channels = network.channels
    network.fullConnNodes.sort(key=utility.sortByNodeId, reverse=False)
    nodes = network.getNodes()
    gossipSequence = []
    for bound in rawGossipSequence:
        i = bound[0]
        bound = bound[1]
        gossipSequence += [(nodes[i], channels[bound[0]:bound[1]])]

    #if processNum is 5, we allocate seq1 to t1, seq2 to t2 ... seq5 to t5. 
    #Then we set t2 as first, so seq6 to t2, seq7 to t3, seq10 to t1
    #This is a greedy way to get fairly equal load balancing.  
    tindex = [[] for i in range(0, processNum)]
    for i in range(0, processNum):
        tindex[0] += [i]
    for i in range(1, processNum):
        tindex[i] = [tindex[i - 1][-1]] + tindex[i - 1][0:-1]

    bundles = [[] for i in range(0, processNum)]

    i = 0
    j = 0
    for b in range(0, len(gossipSequence)):
        gs = gossipSequence[b]
        ti = tindex[i][j]
        bundles[ti] += [gs]
        if j == processNum-1:
            i += 1
        j += 1
        i = i % processNum
        j = j % processNum

    pList = []
    l = Lock()
    for i in range(0, processNum):
        p = Process(target=genGossip, args=(bundles[i],gossipSaveFile, l))
        p.start()
        pList += [p]
    for i in range(0, processNum):
        pList[i].join()



def genGossip(bundles, gossipSaveFile, l):
    """
    Given bundles, we create annoucements and updates for each channel in each bundle
    Since key generation is pricey because of CBitcoinSecret objects, we save the keys so that they can be used again any other time that key is encountered in the process 
    :param: bundles: list of channel lists
    """
    w = 0
    pList = []
    writeList = []
    for bundle in bundles:
        genNode = bundle[0]
        channels = bundle[1]
        
        if not genNode.hasKeys:
            crypto.makeKeyOnDemand(genNode)
          
        for channel in channels:
            scid = channel.scid
            value = channel.value
            node1 = channel.node1
            node2 = channel.node2
            if node1 == genNode:
                otherNode = node2
            else:
                otherNode = node1

            if not otherNode.hasKeys:
                crypto.makeKeyOnDemand(otherNode)

            a = createChannelAnnouncement(channel, scid)
            u1, u2 = createChannelUpdates(channel, a, btimestamp, scid, value)

            ba = a.serialize(full=True)
            bu1 = u1.serialize(full=True)
            bu2 = u2.serialize(full=True)

            bn1 = None
            bn2 = None
            #
            # ba = None
            # bu1 = None
            # bu2 = None

            if channel.n1Write:
                n1 = createNodeAnnouncment(node1)
                bn1 = n1.serialize(full=True)
            if channel.n2Write:
                n2 = createNodeAnnouncment(node2)
                bn2 = n2.serialize(full=True)

            writeList += [(ba, (bu1, bu2), (bn1, bn2))]

            # TODO: write every x number of channels
            if w == 100:
                p = Process(target=writeProcess, args=(writeList,gossipSaveFile, l))
                pList += [p]
                p.start()
                writeList = []
                w = 0
            w += 1
        # print("done with bundle", genNode.nodeid, "channel count:", genNode.channelCount)
    p = Process(target=writeProcess, args=(writeList,gossipSaveFile, l))
    pList += [p]
    p.start()
    # print("done with thread")
    for p in pList:
        p.join()
    # print("done with thread and writing")


#annoucement creation

chainHash = bytearray.fromhex('06226e46111a0b59caaf126043eb5bbf28c34f3a5e332a1fc7b2b73cf188910f')
channelType = bytearray().fromhex("0100") #256
featureLen = bytearray().fromhex("0000")
features = bytearray()

GOSSIP_CHANNEL_ANNOUNCEMENT = "announcement"
GOSSIP_CHANNEL_UPDATE = "update"

def createChannelAnnouncement(channel, scid):
    """
    create a channel announcement
    :param channel: network classes channel obj
    :return: announcement
    """
    nodeA = channel.node1
    nodeB = channel.node2
    if nodeA.nodeCompPub < nodeB.nodeCompPub:   #in bolt 7, node_id_1 is the pubkey that is "numerically-lesser" of the two
        node1 = nodeA
        node2 = nodeB
    else:
        node1 = nodeB
        node2 = nodeA
    a = ChannelAnnouncement()
    a.setFeatureLen(featureLen)
    a.setFeatures(features)
    a.setscid(scid)
    a.setNodeid1(node1.nodeCompPub)
    a.setNodeid2(node2.nodeCompPub)
    a.setBitcoinKey1(node1.bitcoinCompPub)
    a.setBitcoinKey2(node2.bitcoinCompPub)
    h = a.hashPartial()
    nodesig1 = bytearray(crypto.sign(node1.nodeCPrivObj, h))
    nodesig2 = bytearray(crypto.sign(node2.nodeCPrivObj, h))
    bitcoinSig1 = bytearray(crypto.sign(node1.bitcoinCPrivObj, h))
    bitcoinSig2 = bytearray(crypto.sign(node2.bitcoinCPrivObj, h))
    a.setNodeSig1(nodesig1)
    a.setNodeSig2(nodesig2)
    a.setBitcoinSig1(bitcoinSig1)
    a.setBitcoinSig2(bitcoinSig2)

    return a


#update fields
updateType = bytearray().fromhex("0102") #258
initialTimestamp = 1550513768     # timestamp is from time.time(). We increment this number by 1 for every new channel pairs of updates
btimestamp = bytearray(initialTimestamp.to_bytes(4, byteorder="big"))
cltvDelta = 10
cltvDelta = bytearray(cltvDelta.to_bytes(2, byteorder="big"))
htlcMSat = 10000
htlcMSat = bytearray(htlcMSat.to_bytes(8, byteorder="big"))
feeBaseMSat = 1000
feeBaseMSat = bytearray(feeBaseMSat.to_bytes(4, byteorder="big"))
feePropMill = 1000
feePropMill = bytearray(feePropMill.to_bytes(4, byteorder="big"))

def createChannelUpdates(channel, a, timestamp, scid, value):
    """
    create channel updates for node1 and node2 in a channel
    :param channel: network classes channel obj
    :param a: announcement
    :return: updates for node 1 and node 2
    """
    node1 = channel.node1
    node2 = channel.node2

    # #channel updates
    u = ChannelUpdate()
    u.setscid(scid)
    u.setTimestamp(timestamp)
    u.setcltv(cltvDelta)
    u.setHTLCMSat(htlcMSat)
    u.setFeeBaseMSat(feeBaseMSat)
    u.setFeePropMill(feePropMill)
    #value = channel.value
    #bValue = bytearray(value.to_bytes(8, byteorder="big"))
    #u.setHTLCMaxMSat(bValue) #TODO: once final capacity generation is inplace, uncomment this line. 
    u1 = createChannelUpdate(channel, node1, deepcopy(u), a)
    u2 = createChannelUpdate(channel, node2, deepcopy(u), a)

    return u1, u2


def createChannelUpdate(channel, node, u, a):
    """
    create one channel update
    :param channel: network classes channel obj
    :param node:  network classes node obj
    :param u: incomplete update
    :param a: announcement
    :return: complete update
    """
    mFlags = ""
    cFlags = ""
    if node.nodeCompPub == a.id1:
        mFlags = "00"
        cFlags = "0"
    elif node.nodeCompPub == a.id2:
        mFlags = "80"
        cFlags = "8"
    if node == channel.node1:
        cFlags += "0"
    elif node == channel.node2:
        cFlags += "1"
    u.setmFlags(bytearray().fromhex(mFlags))
    u.setcFlags(bytearray().fromhex(cFlags))
    # update for node 1
    s1 = crypto.sign(node.nodeCPrivObj, u.hashPartial())
    u.setSig(s1)

    return u


nodeType = bytearray().fromhex("0101") #257
RGBColor = 0    # <--very boring color
bRGBColor = bytearray(RGBColor.to_bytes(3, "big"))
addrLen = 1
bAddrLen = addrLen.to_bytes(2, "big")
b1Addresses = bytearray([1])
loopback = bytearray([127,0,0,1,0,42])  # a loopback addr port 127.0.0.1:42 for fun!
bAddresses = b1Addresses + loopback

def createNodeAnnouncment(node):
    """
    make new node announcement for node
    :param node: node obj
    :return: node announcement obj
    """
    n = NodeAnnouncment()
    n.setTimestamp(btimestamp)
    n.setNodeid(node.nodeCompPub)
    n.setRGBColor(bRGBColor)

    # set alias as nodeid in ascii
    alias = str(node.nodeid)
    zeros = 32 - len(alias)
    zero = "".join(["0" for i in range(0, zeros)])
    alias = zero + alias
    n.setAlias(bytearray(alias.encode("utf-8")))
    n.setAddrLen(bAddrLen)
    n.setAddresses(bAddresses)

    h = n.hashPartial()
    sig = bytearray(crypto.sign(node.nodeCPrivObj, h))
    n.setNodeSig(sig)

    return n


#writing functions

def initGossip(filename):
    """
    initialze gosip store by making a new one and writing gossip store version (3)
    :param filename: gossip_store filename
    """
    if os.path.exists(filename):
        os.remove(filename)  # delete current generate store if it exists
        fp = open(filename, "wb")
        fp.close()


msglenU = 130
bMsglenU = bytearray(msglenU.to_bytes(2, byteorder="big"))
msglenA = 432
bMsglenA = bytearray(msglenA.to_bytes(2, byteorder="big"))
msglenN = 149
bMsglenN = bytearray(msglenN.to_bytes(2, byteorder="big"))

def writeProcess(writeList, gossipSaveFile, l):
    """
    open file, write a single channel paired with 2 updates to the gossip_store.    use a lock to stop race conditions with writing to file.
    :param: ba: serialized channel annoucement
    :param: bu1: serialized channel update
    :param: bu2: serialized channel update
    """
    l.acquire(block=True)
    for g in writeList:
        ba = g[0]
        bu1 = g[1][0]
        bu2 = g[1][1]
        bn1 = g[2][0]
        bn2 = g[2][1]

        if ba != None:
            writeChannelAnnouncement(ba, gossipSaveFile)
        if bu1 != None:
            writeChannelUpdate(bu1, gossipSaveFile)
        if bu2 != None:
            writeChannelUpdate(bu2, gossipSaveFile)
        if bn1 != None:
            writeNodeAnnouncement(bn1, gossipSaveFile)
        if bn2 != None:
            writeNodeAnnouncement(bn2, gossipSaveFile)

    l.release()
    return

def writeChannelAnnouncement(ba, fp):
    """
    write channel announcement
    :param a: announcement serialized
    :param fp: file pointer
    :return: serialized gossip msg
    """
    with open(fp, "ab") as fp:
        fp.write(bMsglenA)
        fp.write(ba)

def writeChannelUpdate(bu, fp):
    """
    write channel update
    :param u: update serialized
    :param fp: file pointer
    :return: serialized gossip msg
    """
    with open(fp, "ab") as fp:
        fp.write(bMsglenU)
        fp.write(bu)


WIRE_GOSSIP_STORE_CHANNEL_ANNOUNCEMENT = bytearray().fromhex("1000")
def writeNodeAnnouncement(bn, fp):
    """
    write channel update
    :param u: update serialized
    :param fp: file pointer
    :return: serialized gossip msg
    """
    with open(fp, "ab") as fp:
        fp.write(bMsglenN)
        fp.write(bn)


#classes

class ChannelUpdate():
    """
    Channel update class
    """
    def __init__(self):
        self.HTLCMaxMSat = bytearray()  #since is it optional it starts out as empty
    def setSig(self, sig):
        self.sig = sig
    def setscid(self, scid):
        self.scid = scid
    def setTimestamp(self,t):
        self.timestamp = t
    def setmFlags(self,f):
        self.mFlags = f
    def setcFlags(self, f):
        self.cFlags = f
    def setcltv(self, cltv):
        self.cltv = cltv
    def setHTLCMSat(self, msat):
        self.HTLCMSat = msat
    def setFeeBaseMSat(self, msat):
        self.feeBaseMSat = msat
    def setFeePropMill(self, fee):
        self.feePropMill = fee
    def setHTLCMaxMSat(self, msat):    #optional
        self.HTLCMaxMSat = msat

    def serialize(self, full):
        if not full:
            return chainHash + self.scid + self.timestamp + self.mFlags + \
                   self.cFlags + self.cltv + self.HTLCMSat + self.feeBaseMSat + \
                   self.feePropMill + self.HTLCMaxMSat
        else:
            return updateType + self.sig + chainHash + self.scid + self.timestamp + self.mFlags + \
                   self.cFlags + self.cltv + self.HTLCMSat + self.feeBaseMSat + \
                   self.feePropMill + self.HTLCMaxMSat

    def hashPartial(self):
        # we take the double sha
        p = self.serialize(False)
        h = hashlib.sha256(p).digest()
        hh = hashlib.sha256(h).digest()
        return hh

class ChannelAnnouncement():
    """
    Channel Announcement class
    """
    def setNodeSig1(self, sig):
        self.sig1 = sig
    def setNodeSig2(self, sig):
        self.sig2 = sig
    def setBitcoinSig1(self, sig):
        self.bitcoinSig1 = sig
    def setBitcoinSig2(self, sig):
        self.bitcoinSig2 = sig
    def setFeatureLen(self, lenth):
        self.featureLen = lenth
    def setFeatures(self, f):
        self.features = f
    def setscid(self, scid):
        self.scid = scid
    def setNodeid1(self, id1):
        self.id1 = id1
    def setNodeid2(self, id2):
        self.id2 = id2
    def setBitcoinKey1(self, bitcoinKey1):
        self.bitcoinKey1 = bitcoinKey1
    def setBitcoinKey2(self, bitcoinKey2):
        self.bitcoinKey2 = bitcoinKey2

    def serialize(self, full):
        if not full:
            a = self.featureLen + self.features + chainHash + self.scid + self.id1 + self.id2 + self.bitcoinKey1 + self.bitcoinKey2
        else:
            a = channelType + self.sig1 + self.sig2 + self.bitcoinSig1 + self.bitcoinSig2 + self.featureLen + \
                self.features + chainHash + self.scid + self.id1 + self.id2 + self.bitcoinKey1 + self.bitcoinKey2
        return a


    def hashPartial(self):
        """
        hash partial announcement
        :return: hash digest in python bytes type
        """
        a = self.serialize(False)
        h = hashlib.sha256(a).digest()
        hh = hashlib.sha256(h).digest()
        return hh

    def printAnnouncement(self, full):
        """
        printAnnouncement information
        :param: if full annoucement or partial announcement
        """
        if not full:
            print("len:", self.featureLen.hex())
            print("features", self.features.hex())
            print("chain hash",chainHash.hex())
            print("scid", self.scid.hex())
            print("id1:", self.id1.hex())
            print("id2:", self.id2.hex())
            print("bitcoinKey1", self.bitcoinKey1.hex())
            print("bitcoinKey2", self.bitcoinKey2.hex())
        else:
            print("sig 1", self.sig1.hex())
            print("sig 2", self.sig2.hex())
            print("bitcoinSig1", self.bitcoinSig1.hex())
            print("bitcoinSig2", self.bitcoinSig2.hex())
            print("len:", self.featureLen.hex())
            print("features", self.features.hex())
            print("chain hash",chainHash.hex())
            print("scid", self.scid.hex())
            print("id1:", self.id1.hex())
            print("id2:", self.id2.hex())
            print("bitcoinKey1", self.bitcoinKey1.hex())
            print("bitcoinKey2", self.bitcoinKey2.hex())




class NodeAnnouncment:

    def __init__(self):
        zero = 0
        self.setFLen(bytearray(zero.to_bytes(2, "big")))   #starts as 0 features. Functions have to set actual features manually
        self.setFeatures(bytearray())

    def setNodeSig(self, sig):
        self.sig = sig
    def setFLen(self, flen):
        self.flen = flen
    def setFeatures(self, features):
        self.features = features
    def setTimestamp(self, timestamp):
        self.timestamp = timestamp
    def setNodeid(self, id1):
        self.id = id1
    def setRGBColor(self, color):
        self.color = color
    def setAlias(self, alias):
        self.alias = alias
    def setAddrLen(self, addrLen):
        self.addrLen = addrLen
    def setAddresses(self, addresses):
        self.addresses = addresses

    def addressListToBytes(self, addresses):
        #TODO may not need
        if len(addresses) == 0:
            return bytearray()
        else:
            addrs = bytearray()
            for a in addresses:
                addrs += a  

    def hashPartial(self):
        """
        hash partial announcement
        :return: hash digest in python bytes type
        """
        a = self.serialize(False)
        h = hashlib.sha256(a).digest()
        hh = hashlib.sha256(h).digest()
        return hh

    def serialize(self, full):
        if not full:
            n = self.flen + self.features + self.timestamp + self.id + self.color + self.alias + self.addrLen + self.addresses
        else:
            n = nodeType + self.sig + self.flen + self.features + self.timestamp + self.id + self.color + self.alias + self.addrLen + self.addresses
        return n


