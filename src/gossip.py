from config import *
from random import randint
from common import utility, networkClasses
import common.wif as wif
from bitcoin.wallet import CBitcoinSecret, P2PKHBitcoinAddress
from bitcoin import SelectParams
import hashlib
import time
from copy import deepcopy, copy
from multiprocessing import Process, Lock, Pool


chainHash = bytearray.fromhex('06226e46111a0b59caaf126043eb5bbf28c34f3a5e332a1fc7b2b73cf188910f')
channelType = bytearray().fromhex("0100") #256
updateType = bytearray().fromhex("0102") #258
featureLen = bytearray().fromhex("0000")
features = bytearray()
initialscid = bytearray().fromhex("0000010000010001")  #block height 1, tx 1, output 1
scidOutput = bytearray().fromhex("0001") #output 1
satoshis = 10000000 # 1 btc
bSatoshis = bytearray(satoshis.to_bytes(8, byteorder="big"))
WIRE_GOSSIP_STORE_CHANNEL_ANNOUNCEMENT = bytearray().fromhex("1000")
msglenA = 432
bMsglenA = bytearray(msglenA.to_bytes(2, byteorder="big"))  # big endian because this is how gossip store loads it
fulllenA = len(WIRE_GOSSIP_STORE_CHANNEL_ANNOUNCEMENT) + len(bMsglenA) + msglenA + len(bSatoshis)  # remember, we don't have checksum and we don't count gossipVersion
bMsglenAFull = bytearray(fulllenA.to_bytes(4, byteorder="big"))
halfWriteA = bMsglenAFull + WIRE_GOSSIP_STORE_CHANNEL_ANNOUNCEMENT + bMsglenA

#update fields
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
#update
WIRE_GOSSIP_STORE_CHANNEL_UPDATE = bytearray().fromhex("1001")
msglenU = 130
bMsglenU = bytearray(msglenU.to_bytes(2, byteorder="big"))  # big endian because this is how gossip store loads it
fulllenU = len(WIRE_GOSSIP_STORE_CHANNEL_UPDATE) + len(bMsglenU) + msglenU  # remember, we don't have checksum and we don't count gossipVersion
bMsglenUFull = bytearray(fulllenU.to_bytes(4, byteorder="big"))
halfWriteU = bMsglenUFull + WIRE_GOSSIP_STORE_CHANNEL_UPDATE + bMsglenU


GOSSIP_CHANNEL_ANNOUNCEMENT = "announcement"
GOSSIP_CHANNEL_UPDATE = "update"

def call(node):
    node =  makeKeyParall(node)
    return node

def main():
    utility.setRandSeed(randSeed)
    SelectParams("regtest")
    t0 = time.time()
    network = utility.loadNetwork(nodeSaveFile, channelSaveFile)
    print(len(network.channels))
    t1 = time.time()
    print("loading network complete", t1-t0)
    t2 = time.time()
    # with Pool(5) as p:
    #     n = p.map(call, network.getNodes())
    #     print("stop")
    # makeAllPrivPubKeys(network.getNodes())
    t3 = time.time()
    print("key creation complete", t3-t2)
    t4 = time.time()
    initGossip_store(gossipSaveFile)
    generateAllGossip(network)
    t5 = time.time()
    print("generating/writing gossip complete", t5-t4)

    print("program complete", t5-t0)


def generateAllGossip(network):
    channels = network.channels
    writeList = []

    #initial writing process
    # wp = Process(target=writeGossipParall, args=(writeList, len(channels), filename))
    # wp.start()

    #run genGossip with Pool.map
    with Pool(5) as p:
        p.map(genGossip, channels)

    # wp.join()

## gossip store functions
def writeGossipParall(writeList, numChannels, filename):
    """
    writes gossip announcements and updates to gossip_store file.
    :param writeList: a list of tuples: [(serialized_data, GOSSIP_CHANNEL_ANNOUNCEMENT|GOSSIP_CHANNEL_UPDATE)]
    :param filename: filename of gossip_store
    """
    fp = open(filename, "ab")

    i = 0
    while len(writeList) != numChannels:
        lenWriteList = len(writeList)
        if lenWriteList == (i+1) or lenWriteList == 0:
            print("writelist in write:", writeList)
            continue
        else:
            a = writeList[i][0]
            u1 = writeList[i][1]
            u2 = writeList[i][2]

            writeChannelAnnouncement(a, fp)
            writeChannelUpdate(u1, fp)
            writeChannelUpdate(u2, fp)
            i += 1

    fp.close()

l = Lock()

def genGossip(channel):
    scid = getScid(channel)

    node1CPrivObj, node1Pub, bitcoin1CPrivObj, bitcoin1Pub = makeKeyOnDemand(channel.node1.nodeid)
    node2CPrivObj, node2Pub, bitcoin2CPrivObj, bitcoin2Pub = makeKeyOnDemand(channel.node2.nodeid)

    a = createChannelAnnouncement(channel, scid, node1CPrivObj, node1Pub, bitcoin1CPrivObj, bitcoin1Pub, node2CPrivObj, node2Pub, bitcoin2CPrivObj, bitcoin2Pub)
    u1, u2 = createChannelUpdates(channel, a, btimestamp, scid, node1CPrivObj, node1Pub, node2CPrivObj, node2Pub)

    # TODO if I ever check for spaces, I need to find the bytes that are causing it, check for them here and then redo the ca and u1,u2 if that is the case
    ba = a.serialize(full=True)
    bu1 = u1.serialize(full=True)
    bu2 = u2.serialize(full=True)
    # writeList = [(ba, GOSSIP_CHANNEL_ANNOUNCEMENT), (bu1, GOSSIP_CHANNEL_UPDATE), (bu2, GOSSIP_CHANNEL_UPDATE)]
    # writeList += [[(ba, GOSSIP_CHANNEL_ANNOUNCEMENT), (bu1, GOSSIP_CHANNEL_UPDATE), (bu2, GOSSIP_CHANNEL_UPDATE)]]
    # we write now so that we aren't holding a million CAs in memory
    # if w % 100 == 0:
    #     writeGossip(writeList, filename)
    #     writeList = []

    l.acquire(block=True)
    fp = open(gossipSaveFile, "ab")
    writeChannelAnnouncement(ba, fp)
    writeChannelUpdate(bu1, fp)
    writeChannelUpdate(bu2, fp)
    fp.close()
    l.release()



def generateAllGossipOld(network, filename):
    """
    Generate and write announcements and updates for all channels to gossip_store file
    :param network: network object
    """
    channels = network.channels
    timestamp = initialTimestamp
    scid = initialscid
    writeList = []
    w = 0
    i = 0
    j = 1
    for ch in channels:
        if i == 1000:
            print(str(1000*j), "gossip created")
            j += 1
            i = 0

        timestamp += 1
        btimestamp = bytearray(timestamp.to_bytes(4, byteorder="big"))
        a = createChannelAnnouncement(ch,scid)
        u1, u2 = createChannelUpdates(ch, a, btimestamp, scid)
        #TODO if I ever check for spaces, I need to find the bytes that are causing it, check for them here and then redo the ca and u1,u2 if that is the case
        ba = a.serialize(full=True)
        bu1 = u1.serialize(full=True)
        bu2 = u2.serialize(full=True)
        writeList = [(ba, GOSSIP_CHANNEL_ANNOUNCEMENT), (bu1, GOSSIP_CHANNEL_UPDATE), (bu2, GOSSIP_CHANNEL_UPDATE)]
        # writeList += [(ba, GOSSIP_CHANNEL_ANNOUNCEMENT), (bu1, GOSSIP_CHANNEL_UPDATE), (bu2, GOSSIP_CHANNEL_UPDATE)]
        # we write now so that we aren't holding a million CAs in memory
        # if w % 100 == 0:
        #     writeGossip(writeList, filename)
        #     writeList = []
        writeToGossip_store(writeList, filename)
        scid = getNextScid(scid)
        i += 1
        w += 1
    # if writeList != []:
    #     writeGossip(writeList, filename)


#keys
def makeAllPrivPubKeys(nodes):
    """
    make private and public keypair for every node in the network
    :param network: network
    """

    i = 0
    j = 1
    for node in nodes:
        if not node.hasKeys:
            if i == 1000:
                print(str(1000 * j), "keys created")
                j += 1
                i = 0
            else:
                i += 1

            nodeCPrivObj = makeSinglePrivKeyNodeId(node.nodeid)  # there can never be a 0 private key in ecdsa
            #nodeCPrivObj = makeSinglePrivKey()
            node.setNodeCPrivObj(nodeCPrivObj)
            nodePub = compPubKey(nodeCPrivObj)
            node.setNodeCompPub(nodePub)
            bitcoinCPrivObj = makeSinglePrivKey()
            bitcoinPub = compPubKey(bitcoinCPrivObj)
            node.setBitcoinCPrivObj(bitcoinCPrivObj)
            node.setBitcoinCompPub(bitcoinPub)
            node.setHasKeys(True)


def makeKeyParall(node):
    """
    Parallelized function
    :param node: node obj
    """
    nodeCPrivObj = makeSinglePrivKeyNodeId(node.nodeid)  # there can never be a 0 private key in ecdsa
    node.setNodeCPrivObj(nodeCPrivObj)
    nodePub = compPubKey(nodeCPrivObj)
    node.setNodeCompPub(nodePub)
    bitcoinCPrivObj = makeSinglePrivKey()
    bitcoinPub = compPubKey(bitcoinCPrivObj)
    node.setBitcoinCPrivObj(bitcoinCPrivObj)
    node.setBitcoinCompPub(bitcoinPub)
    node.setHasKeys(True)
    return nodeCPrivObj


def makeKeyOnDemand(nodeid):
    nodeCPrivObj = makeSinglePrivKeyNodeId(nodeid)  # there can never be a 0 private key in ecdsa
    nodePub = compPubKey(nodeCPrivObj)
    bitcoinCPrivObj = makeSinglePrivKey()
    bitcoinPub = compPubKey(bitcoinCPrivObj)
    return nodeCPrivObj, nodePub, bitcoinCPrivObj, bitcoinPub

def makeSinglePrivKeyNodeId(nodeid):
    key = nodeid + 1
    privBits = key.to_bytes(32, "big")
    wifPriv = wif.privToWif(privBits.hex())
    cPrivObj = CBitcoinSecret(wifPriv)
    return cPrivObj

def makeSinglePrivKey():
    """
    make private key python bitcoin object
    :return: python-bitcoin key object
    """
    randbits = generateNewSecretKey()
    wifPriv = wif.privToWif(randbits.hex())
    cPrivObj = CBitcoinSecret(wifPriv)
    return cPrivObj

def compPubKey(keyObj):
    """
    get public key from python-bitcoin key object
    :param keyObj: python-bitcoin key object
    :return: public bytes
    """
    keyObj._cec_key.set_compressed(True)
    pubbits = keyObj._cec_key.get_pubkey()
    return pubbits

def generateNewSecretKey():
    """
    using default python randomness because secret keys don't have to be secure
    :return: CECKey priv key , CPubKey
    """

    size = 32
    randBytes = [randint(0,255) for i in range(0, size)]
    randbits = bytes(randBytes)
    return randbits


def createChannelAnnouncement(channel, scid, nodeACPrivObj, nodeAPub, bitcoinACPrivObj, bitcoinAPub, nodeBCPrivObj, nodeBPub, bitcoinBCPrivObj, bitcoinBPub):
    """
    create a channel announcement
    :param channel: network classes channel obj
    :return: announcement
    """
    if nodeAPub < nodeBPub:   #in bolt 7, node_id_1 is the pubkey that is "numerically-lesser" of the two
        node1Pub = nodeAPub
        node1CPrivObj = nodeACPrivObj
        node2Pub = nodeBPub
        node2CPrivObj = nodeBCPrivObj
        bitcoin1Pub = bitcoinAPub
        bitcoin1CPrivObj = bitcoinACPrivObj
        bitcoin2Pub = bitcoinBPub
        bitcoin2CPrivObj = bitcoinBCPrivObj
    else:
        node1Pub = nodeBPub
        node1CPrivObj = nodeBCPrivObj
        node2Pub = nodeAPub
        node2CPrivObj = nodeACPrivObj
        bitcoin1Pub = bitcoinBPub
        bitcoin1CPrivObj = bitcoinBCPrivObj
        bitcoin2Pub = bitcoinAPub
        bitcoin2CPrivObj = bitcoinACPrivObj

    a = ChannelAnnouncement()
    a.setFeatureLen(featureLen)
    a.setFeatures(features)
    a.setscid(scid)
    a.setNodeid1(node1Pub)
    a.setNodeid2(node2Pub)
    a.setBitcoinKey1(bitcoin1Pub)
    a.setBitcoinKey2(bitcoin2Pub)
    h = a.hashPartial()
    nodesig1 = bytearray(sign(node1CPrivObj, h))
    nodesig2 = bytearray(sign(node2CPrivObj, h))
    bitcoinSig1 = bytearray(sign(bitcoin1CPrivObj, h))
    bitcoinSig2 = bytearray(sign(bitcoin2CPrivObj, h))
    a.setNodeSig1(nodesig1)
    a.setNodeSig2(nodesig2)
    a.setBitcoinSig1(bitcoinSig1)
    a.setBitcoinSig2(bitcoinSig2)

    return a

def createChannelUpdates(channel, a, timestamp, scid, node1CPrivObj, node1Pub, node2CPrivObj, node2Pub):
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
    u.sethtlcMSat(htlcMSat)
    u.setFeeBaseMSat(feeBaseMSat)
    u.setFeePropMill(feePropMill)

    u1 = createChannelUpdate(channel, node1, node1CPrivObj, node1Pub, deepcopy(u), a)
    u2 = createChannelUpdate(channel, node2, node2CPrivObj, node2Pub, deepcopy(u), a)
    return u1, u2


def createChannelUpdate(channel, node, nodeCPrivObj, nodePub, u, a):
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
    if nodePub == a.id1:
        mFlags = "00"
        cFlags = "0"
    elif nodePub == a.id2:
        mFlags = "80"
        cFlags = "8"
    if node == channel.node1:
        cFlags += "0"
    elif node == channel.node2:
        cFlags += "1"
    u.setmFlags(bytearray().fromhex(mFlags))
    u.setcFlags(bytearray().fromhex(cFlags))
    # update for node 1
    s1 = sign(nodeCPrivObj, u.hashPartial())
    u.setSig(s1)
    return u

def getScid(channel):
    """
    nodeid
    :param nodeid:
    :return:
    """
    nodeid1 = channel.node1.nodeid
    nodeid2 = channel.node2.nodeid
    connids = int(str(nodeid1) + str(nodeid2))
    bconnids = bytearray(connids.to_bytes(6, "big"))
    bscid = bconnids + scidOutput
    return bscid

def getNextScid(scid):
    """
    basic incremeneting method that currently allows 100 lightning txs in a block. This is naive may be changed in the future
    :param scid: scid
    :return: new scid
    """
    bheight = scid[0:3]
    tx = int.from_bytes(bytes(scid[3:6]), "big")
    boutput = scid[6:]

    if tx == 100:
        height = int.from_bytes(bytes(bheight), "big")
        height += 1
        bheight = bytearray(height.to_bytes(3, "big"))
        tx = 1
    else:
        tx += 1

    btx = bytearray(tx.to_bytes(3, "big"))

    return bheight + btx + boutput


def sign(key, h):
    """
    sign hash with key
    :param key: key
    :param h: hash bytes
    :return: signature
    """
    sig, i = key.sign_compact(h)
    return sig


## gossip store functions
def writeToGossip_store(writeList, filename):
    """
    writes gossip announcements and updates to gossip_store file.
    :param writeList: a list of tuples: [(serialized_data, GOSSIP_CHANNEL_ANNOUNCEMENT|GOSSIP_CHANNEL_UPDATE)]
    :param filename: filename of gossip_store
    """
    fp = open(filename, "ab")
    for entry in writeList:
        a = entry[0]
        t = entry[1]
        if t == GOSSIP_CHANNEL_ANNOUNCEMENT:
            writeChannelAnnouncement(a, fp)
        elif t == GOSSIP_CHANNEL_UPDATE:
            writeChannelUpdate(a, fp)
    fp.close()

def initGossip_store(filename):
    """
    initialze gosip store by making a new one and writing gossip store version (3)
    :param filename: gossip_store filename
    """
    if os.path.exists(filename):
        os.remove(filename)  # delete current generate store if it exists
    fp = open(filename, "wb")
    gossipVersion = bytearray().fromhex("03")
    fp.write(gossipVersion)
    fp.close()

def writeGossip(writeLst, filename):
    fp = open(filename, "ab")
    gossip = bytearray()
    for e in writeLst:
        if e[1] == GOSSIP_CHANNEL_ANNOUNCEMENT:
            gossip += bMsglenAFull + WIRE_GOSSIP_STORE_CHANNEL_ANNOUNCEMENT + bMsglenA + e[0] + bSatoshis
        elif e[1] == GOSSIP_CHANNEL_UPDATE:
            gossip += bMsglenUFull + WIRE_GOSSIP_STORE_CHANNEL_UPDATE + bMsglenU + e[0]
    fp.write(gossip)

def writeChannelAnnouncement(a, fp):
    """
    write channel announcement
    :param a: announcement serialized
    :param fp: file pointer
    :return: serialized gossip msg
    """
    # aToWrite = bMsglenAFull + WIRE_GOSSIP_STORE_CHANNEL_ANNOUNCEMENT + bMsglenA + a + bSatoshis
    fp.write(halfWriteA)
    fp.write(a)
    fp.write(bSatoshis)
    # fp.write(aToWrite)
    # return aToWrite


def writeChannelUpdate(u, fp):
    """
    write channel update
    :param u: update serialized
    :param fp: file pointer
    :return: serialized gossip msg
    """

    fp.write(halfWriteU)
    fp.write(u)
    # print("len of u:", len(a))
    # print(len(aToWrite.hex()))
    # print(aToWrite.hex())


#classes

class ChannelUpdate():
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
    def sethtlcMSat(self, msat):
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

    # def preserialize(self):
    #     self.preserialize = self.featureLen.extend(chainHash)

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

    def printAnnoucement(self, full):
        if not full:
            print("len:", self.featureLen.hex())
            print("features", self.features.hex())
            print("chain hash",chainHash.hex())
            print("scid", self.scid.hex())
            print("id1:", self.id1.hex())
            print("id2:", self.id2.hex())
            print("bitcoinKey1", self.bitcoinKey1.hex())
            print("bitcoinKey2", self.bitcoinKey2.hex())


main()
#
# SelectParams("regtest")
# n = networkClasses.Node(0)
# makeKeyParall(n)
# import pickle
# fp = open("pickle.txt", "wb")
# pickle.dump(n, fp)

#test functions
def testSigning(num):
    SelectParams("regtest")
    k = makeSinglePrivKeyNodeId(num)
    m = "message"
    h = hashlib.sha256(m.encode()).digest()
    sig = sign(k, h)
    import bitcoin.signmessage as signmessage
    # signmessage.VerifyMessage(sig,m,)
    # r =
    return
