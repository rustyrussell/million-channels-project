from config import *
from random import randint
from common import utility, networkClasses
import common.wif as wif
from bitcoin.wallet import CBitcoinSecret, P2PKHBitcoinAddress
from bitcoin import SelectParams
import hashlib
import time
from copy import deepcopy, copy
from multiprocessing import Process, Lock, Pool, pool, get_context


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


def main():
    """
    creates and writes all gossip from the files nodeSaveFile and channelSaveFile defined in config 
    Writes this information to gossipSaveFile
    Each channel has 1 channel annoucement and 2 channel updates. Keys and scids are determined determinisically based on node id.
    """
    utility.setRandSeed(randSeed)
    SelectParams("regtest")
    t0 = time.time()
    network, gossipSequence = utility.loadNetwork(nodeSaveFile, channelSaveFile)
    print(len(network.channels))
    t1 = time.time()
    print("loading network complete", t1-t0)
    initGossip_store(gossipSaveFile)
    t2 = time.time()
    generateAllGossip(network, gossipSequence)
    t3 = time.time()
    print("generating/writing gossip complete", t3-t2)

    print("program complete", t3-t0)


def generateAllGossip(network, rawGossipSequence):
    """
    generates and writes all gossip. 
    First use the gossipSequence generated in buildNetwork.py and stored in channelStoreFile to seperate channels into lists of channels 
    Second, based on thread count, create lists of channel allococaters called tindex which helps with load balancing. A sequence of channels is called a bundle. 
    Bundles will be assigned to each process.
    Last, we make a group of processes running genGossip
    """
    channels = network.channels

    network.fullConnNodes.sort(key=utility.sortByNodeId, reverse=False)
    nodes = network.fullConnNodes

    gossipSequence = []
    for bound in rawGossipSequence:
        i = bound[0]
        bound = bound[1]
        gossipSequence += [(nodes[i], channels[bound[0]:bound[1]])]

    threadNum = 25
 
    #if threadNum is 5, we allocate seq1 to t1, seq2 to t2 ... seq5 to t5. 
    #Then we set t2 as first, so seq6 to t2, seq7 to t3, seq10 to t1
    #This is a greedy way to get fairly equal load balancing.  
    tindex = [[] for i in range(0, threadNum)]
    for i in range(0, threadNum):
        tindex[0] += [i]
    for i in range(1, threadNum):
        tindex[i] = [tindex[i - 1][-1]] + tindex[i - 1][0:-1]

    bundles = [[] for i in range(0, threadNum)]

    i = 0
    j = 0
    for b in range(0, len(gossipSequence)):
        gs = gossipSequence[b]
        ti = tindex[i][j]
        bundles[ti] += [gs]
        if j == threadNum-1:
            i += 1
        j += 1
        i = i % threadNum
        j = j % threadNum

    pList = []
    for i in range(0, threadNum):
        p = Process(target=genGossip, args=(bundles[i],)) 
        p.start()
        pList += [p]
    for i in range(0, threadNum):
        pList[i].join()
      
    
    #run genGossip with Pool.map
    #with MyPool(threadNum) as p:
    #    p.map(genGossip, bundles)


l = Lock()

def genGossip(bundles):
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
            makeKeyOnDemand(genNode)
          
        for channel in channels:
            scid = getScid(channel)

            node1 = channel.node1
            node2 = channel.node2
            if node1 == genNode:
                otherNode = node2
            else:
                otherNode = node1

            if not otherNode.hasKeys:
                makeKeyOnDemand(otherNode)

            a = createChannelAnnouncement(channel, scid)
            u1, u2 = createChannelUpdates(channel, a, btimestamp, scid)

            ba = a.serialize(full=True)
            bu1 = u1.serialize(full=True)
            bu2 = u2.serialize(full=True)
  
            writeList += [(ba, bu1, bu2)]

            # TODO: write every x number of channels
            if w == 100:
                p = Process(target=writeParallel, args=(writeList,))
                pList += [p]
                p.start()
                writeList = []
                w = 0
            w += 1
        print("done with bundle", genNode.nodeid, "channel count:", genNode.channelCount)
    p = Process(target=writeParallel, args=(writeList,))
    pList += [p]
    p.start()
    writeList = []
    print("done with thread")
    for p in pList:
        p.join()
    print("done with thread and writing")
#cryptography functions

def makeKeyOnDemand(node):
    """
    given a node, check if a key was already created and if not, generate 2 keys    and save the priv/pub keys of those 2 keys in the object
    :param node: node obj 
    """
    if not node.hasKeys:
        nodeid = node.nodeid
        nodeCPrivObj = makeSinglePrivKeyNodeId(nodeid)  # there can never be a 0 private key in ecdsa
        nodePub = compPubKey(nodeCPrivObj)
        #bitcoinCPrivObj = makeSinglePrivKey()
        #bitcoinPub = compPubKey(bitcoinCPrivObj)
        node.setNodeCompPub(nodePub)
        node.setBitcoinCompPub(nodePub) #TODO decide whether to have different keys for bitcoin and node
        node.setNodeCPrivObj(nodeCPrivObj)
        node.setBitcoinCPrivObj(nodeCPrivObj)
        node.setHasKeys(True)
    else:
        raise ValueError("should have keys already generated")


def makeSinglePrivKeyNodeId(nodeid):
    """
    make and return a python bitcoin cprivobj 
    :param nodeid: nodeid int
    :return: CBitcoinSecret obj 
    """
    key = nodeid + 1   # we add 1 because keys cannot be 0
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


def sign(key, h):
    """
    sign hash with key
    :param key: key
    :param h: hash bytes
    :return: signature
    """
    sig, i = key.sign_compact(h)
    return sig



#annoucement creation

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
    nodesig1 = bytearray(sign(node1.nodeCPrivObj, h))
    nodesig2 = bytearray(sign(node2.nodeCPrivObj, h))
    bitcoinSig1 = bytearray(sign(node1.bitcoinCPrivObj, h))
    bitcoinSig2 = bytearray(sign(node2.bitcoinCPrivObj, h))
    a.setNodeSig1(nodesig1)
    a.setNodeSig2(nodesig2)
    a.setBitcoinSig1(bitcoinSig1)
    a.setBitcoinSig2(bitcoinSig2)

    return a

def createChannelUpdates(channel, a, timestamp, scid):
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
    s1 = sign(node.nodeCPrivObj, u.hashPartial())
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

#writing functions

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

def writeParallel(writeList):
    """
    open file, write a single channel paired with 2 updates to the gossip_store.    use a lock to stop race conditions with writing to file.
    :param: ba: serialized channel annoucement
    :param: bu1: serialized channel update
    :param: bu2: serialized channel update
    """
    l.acquire(block=True)
    for g in writeList:
        ba = g[0]
        bu1 = g[1]
        bu2 = g[2]
        writeChannelAnnouncement(ba, gossipSaveFile)
        writeChannelUpdate(bu1, gossipSaveFile)
        writeChannelUpdate(bu2, gossipSaveFile)
    #try:
    #    fp.close()
    #except:
    #    raise IOException("io execpt") 
    l.release()
    return

def writeChannelAnnouncement(a, fp):
    """
    write channel announcement
    :param a: announcement serialized
    :param fp: file pointer
    :return: serialized gossip msg
    """
    with open(fp, "ab") as fp:
        fp.write(halfWriteA)
        fp.write(a)
        fp.write(bSatoshis)

def writeChannelUpdate(u, fp):
    """
    write channel update
    :param u: update serialized
    :param fp: file pointer
    :return: serialized gossip msg
    """
    with open(fp, "ab") as fp:
        fp.write(halfWriteU)
        fp.write(u)

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


#NOTE: these 3 classes I got from stackoverflow: https://stackoverflow.com/a/53180921
class NoDaemonProcess(Process):
    @property
    def daemon(self):
        return False

    @daemon.setter
    def daemon(self, value):
        pass

class NoDaemonContext(type(get_context())):
    Process = NoDaemonProcess

# We sub-class multiprocessing.pool.Pool instead of multiprocessing.Pool
# because the latter is only a wrapper function, not a proper class.
class MyPool(pool.Pool):
    def __init__(self, *args, **kwargs):
        kwargs['context'] = NoDaemonContext()
        super(MyPool, self).__init__(*args, **kwargs)



main()

