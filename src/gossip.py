import os
import pickle
from config import *
from common.networkClasses import *
from random import randint
import common.utility as utility
import common.wif as wif
from bitcoin.wallet import CBitcoinSecret, P2PKHBitcoinAddress
from bitcoin import SelectParams
import hashlib
from bitcoin.signmessage import BitcoinMessage, VerifyMessage, SignMessage
import base64
import sys
import time

chainHash = bytearray.fromhex('06226e46111a0b59caaf126043eb5bbf28c34f3a5e332a1fc7b2b73cf188910f')
channelType = bytearray().fromhex("0100") #256
updateType = bytearray().fromhex("0102") #258
featureLen = bytearray().fromhex("0000")
features = bytearray()
scid = bytearray([0, 0, 10, 0, 0, 2, 0, 1])   # for now we are placing it in the 10th block, 2nd transactions, 1st output
satoshis = 11111

#update fields
timestamp = 1550513768     # timestamp is from time.time()
timestamp = bytearray(timestamp.to_bytes(4, byteorder="big"))
cltvDelta = 10
cltvDelta = bytearray(cltvDelta.to_bytes(2, byteorder="big"))
htlcMSat = 10000
htlcMSat = bytearray(htlcMSat.to_bytes(8, byteorder="big"))
feeBaseMSat = 1000
feeBaseMSat = bytearray(feeBaseMSat.to_bytes(4, byteorder="big"))
feePropMill = 1000
feePropMill = bytearray(feePropMill.to_bytes(4, byteorder="big"))

CHANNEL_ANNOUNCEMENT = "channel announcement"
CHANNEL_UPDATE = "channel update"


def mvp():
    utility.setRandSeed(0)
    SelectParams("regtest")
    network = loadNetwork(networkSaveFile)
    ch = network.channels[0]
    node1 = ch.node1
    node2 = ch.node2
    makeSinglePrivKey(node1)
    compPubKey(node1)
    makeSinglePrivKey(node2)
    compPubKey(node2)

    ## make another priv key. We will eventually add this to the node object ##
    bitcoinPriv1 = generateNewSecretKey().hex()
    wifBitcoinPriv1 = wif.privToWif(bitcoinPriv1)
    cBitcoinPrivObj1 = CBitcoinSecret(wifBitcoinPriv1)
    cBitcoinPrivObj1._cec_key.set_compressed(True)
    bitcoinPub1 = cBitcoinPrivObj1._cec_key.get_pubkey()
    bitcoinPriv2 = generateNewSecretKey().hex()
    wifBitcoinPriv2 = wif.privToWif(bitcoinPriv2)
    cBitcoinPrivObj2 = CBitcoinSecret(wifBitcoinPriv2)
    cBitcoinPrivObj2._cec_key.set_compressed(True)
    bitcoinPub2 = cBitcoinPrivObj2._cec_key.get_pubkey()
    ## // ##

    nodeid1 = bytearray(compPubKey(node1))
    nodeid2 = bytearray(compPubKey(node2))
    bitcoinKey1 = bytearray(bitcoinPub1)
    bitcoinKey2 = bytearray(bitcoinPub2)

    a = ChannelAnnouncement()
    a.setFeatureLen(featureLen)
    a.setFeatures(features)
    a.setscid(scid)
    a.setNodeid1(nodeid1)
    a.setNodeid2(nodeid2)
    a.setBitcoinKey1(bitcoinKey1)
    a.setBitcoinKey2(bitcoinKey2)

    h = a.hashPartial()
    s = sign(node1.cPrivObj, h)
    nodesig1 = bytearray(sign(node1.cPrivObj, h))
    nodesig2 = bytearray(sign(node2.cPrivObj, h))
    bitcoinSig1 = bytearray(sign(cBitcoinPrivObj1, h))
    bitcoinSig2 = bytearray(sign(cBitcoinPrivObj2, h))

    a.setNodeSig1(nodesig1)
    a.setNodeSig2(nodesig2)
    a.setBitcoinSig1(bitcoinSig1)
    a.setBitcoinSig2(bitcoinSig2)

    finalA = a.serialize(full=True)

    #channel updates
    update1 = ChannelUpdate()
    update1.setscid(scid)
    update1.setTimestamp(timestamp)
    mFlags = bytearray().fromhex("00")   #most sig bit is 0 because direction is from node 1->2. least sig bit is 0 because this is node 1's update
    update1.setmFlags(mFlags)
    cFlags = bytearray().fromhex("00")   #least sig bit this is node 1's update
    update1.setcFlags(cFlags)
    update1.setcltv(cltvDelta)
    update1.sethtlcMSat(htlcMSat)
    update1.setFeeBaseMSat(feeBaseMSat)
    update1.setFeePropMill(feePropMill)

    #update for node 1
    s1 = sign(node1.cPrivObj, update1.hashPartial())
    update1.setSig(s1)
    bUpdate1 = update1.serialize(full=True)

    update2 = update1
    mFlags = bytearray().fromhex("01")  # most sig bit is 0 because direction is from node 1->2. Least sig bit is 1 because this is 2's update
    update2.setmFlags(mFlags)
    cFlags = bytearray().fromhex("01")  # least sig bit is 1 because this is 2's update
    update2.setcFlags(cFlags)
    s2 = sign(node2.cPrivObj, update2.hashPartial())
    update2.setSig(s2)
    bupdate2 = update2.serialize(full=True)
    return finalA, bUpdate1, bupdate2

def sign(key, h):
    sig, i = key.sign_compact(h)
    return sig

def makeAllPrivPubKeys(network):
    nodes = network.fullConnNodes + network.partConnNodes
    for node in nodes:
        makeSinglePrivKey(node)
        compPubKey(node)

def makeSinglePrivKey(node):
    randbits = generateNewSecretKey()
    node.priv = randbits
    wifPriv = wif.privToWif(randbits.hex())
    cPrivObj = CBitcoinSecret(wifPriv)
    node.setCPrivKeyObj(cPrivObj)

def compPubKey(node):
    cPrivObj = node.cPrivObj
    cPrivObj._cec_key.set_compressed(True)
    pubbits = cPrivObj._cec_key.get_pubkey()
    node.setCompPubKey(pubbits)
    return pubbits





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

    def serialize(self, full):
        if not full:
            a = self.featureLen + self.features + chainHash + self.scid + \
                self.id1 + self.id2 + self.bitcoinKey1 + self.bitcoinKey2
        else:
            a = channelType + self.sig1 + self.sig2 + self.bitcoinSig1 + \
                self.bitcoinSig2 + self.featureLen + self.features + chainHash + self.scid + \
                self.id1 + self.id2 + self.bitcoinKey1 + self.bitcoinKey2
        return a

    def hashPartial(self):
        """
        hash partial announcement
        :return: hash digest in python bytes type
        """
        a = self.serialize(False)
        h = hashlib.sha256(a).digest()
        hh = hashlib.sha256(h).digest()
        print("hash", hh.hex())
        self.printAnnoucement(False)
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


def generateNewSecretKey():
    """
    using default python randomness because secret keys don't have to be secure--this is a test suite.

    :return: CECKey priv key , CPubKey
    """

    size = 32
    randBytes = [randint(0,255) for i in range(0, size)]
    randbits = b''
    randbits = bytes(randBytes)
    return randbits


## gossip store functions


def writeToGossip_store(writeList, filename):
    fp = open(filename, "wb")
    initGossip_store(fp)
    for entry in writeList:
        a = entry[0]
        t = entry[1]
        if t == CHANNEL_ANNOUNCEMENT:
            writeChannelAnnouncement(a, fp)
        elif t == CHANNEL_UPDATE:
            writeChannelUpdate(a, fp)


def initGossip_store(fp):
    gossipVersion = bytearray().fromhex("03")
    fp.write(gossipVersion)

def writeChannelAnnouncement(a, fp):
    msglen = getmsglen(a)
    bMsglenA = bytearray(msglen.to_bytes(2, byteorder="big"))  # big endian because this is how gossip store loads it
    WIRE_GOSSIP_STORE_CHANNEL_ANNOUNCEMENT = bytearray().fromhex("1000")
    bSatoshis = bytearray(satoshis.to_bytes(8, byteorder="big"))
    fulllen = len(WIRE_GOSSIP_STORE_CHANNEL_ANNOUNCEMENT) + len(bMsglenA) + len(a) + len(bSatoshis) #remember, we don't have checksum and we don't count gossipVersion
    bMsglenFull = bytearray(fulllen.to_bytes(4, byteorder="big"))
    aToWrite = bMsglenFull + WIRE_GOSSIP_STORE_CHANNEL_ANNOUNCEMENT + bMsglenA + a + bSatoshis
    fp.write(aToWrite)
    return aToWrite

def writeChannelUpdate(a, fp):
    msglen = getmsglen(a)
    bMsglenA = bytearray(msglen.to_bytes(2, byteorder="big"))  # big endian because this is how gossip store loads it
    WIRE_GOSSIP_STORE_CHANNEL_UPDATE = bytearray().fromhex("1001")
    fulllen = len(WIRE_GOSSIP_STORE_CHANNEL_UPDATE) + len(bMsglenA) + len(a) #remember, we don't have checksum and we don't count gossipVersion
    bMsglenFull = bytearray(fulllen.to_bytes(4, byteorder="big"))
    aToWrite = bMsglenFull + WIRE_GOSSIP_STORE_CHANNEL_UPDATE + bMsglenA + a
    fp.write(aToWrite)
    # print("len of u:", len(a))
    # print(len(aToWrite.hex()))
    # print(aToWrite.hex())
    return aToWrite


def getmsglen(a):
    return len(a)


def loadNetwork(networkFilename):
    fp = open(networkFilename, "rb")
    network = pickle.load(fp)
    return network



#ca = "03" + "000001bc" + "1000" + "01b00100bb8d7b6998cca3c2b3ce12a6bd73a8872c808bb48de2a30c5ad9cdf835905d1e27505755087e675fb517bbac6beb227629b694ea68f49d357458327138978ebfd7adfde1c69d0d2f497154256f6d5567a5cf2317c589e0046c0cc2b3e986cf9b6d3b44742bd57bce32d72cd1180a7f657795976130b20508b239976d3d4cdc4d0d6e6fbb9ab6471f664a662972e406f519eab8bce87a8c0365646df5acbc04c91540b4c7c518cec680a4a6af14dae1aca0fd5525220f7f0e96fcd2adef3c803ac9427fe71034b55a50536638820ef21903d09ccddd38396675b598587fa886ca711415c813fc6d69f46552b9a0a539c18f265debd0e2e286980a118ba349c216000043497fd7f826957108f4a30fd9cec3aeba79972084e90ead01ea33090000000013a63c0000b50001021bf3de4e84e3d52f9a3e36fbdcd2c4e8dbf203b9ce4fc07c2f03be6c21d0c67503f113414ebdc6c1fb0f33c99cd5a1d09dd79e7fdf2468cf1fe1af6674361695d203801fd8ab98032f11cc9e4916dd940417082727077609d5c7f8cc6e9a3ad25dd102517164b97ab46cee3826160841a36c46a2b7b9c74da37bdc070ed41ba172033a0000000001000000"
update =  "00000086" + "88c703c8"  +"1001" + "008201021ea7c2eadf8a29eb8690511a519b5656e29aa0a853771c4e38e65c5abf43d907295a915e69e451f4c7a0c3dc13dd943cfbe3ae88c0b96667cd7d58955dbfedcf43497fd7f826957108f4a30fd9cec3aeba79972084e90ead01ea33090000000013a63c0000b500015b8d9b440000009000000000000003e8000003e800000001"
# print(update)
# with open(os.path.join(l1.daemon.lightning_dir, 'gossip_store'), 'wb') as f:
#     f.write(bytearray.fromhex("03"  # GOSSIP_VERSION
#                               "000001bc"  # len
#                               "521ef598"  # csum
#                               "1000"  # WIRE_GOSSIP_STORE_CHANNEL_ANNOUNCEMENT
#                               "01b00100bb8d7b6998cca3c2b3ce12a6bd73a8872c808bb48de2a30c5ad9cdf835905d1e27505755087e675fb517bbac6beb227629b694ea68f49d357458327138978ebfd7adfde1c69d0d2f497154256f6d5567a5cf2317c589e0046c0cc2b3e986cf9b6d3b44742bd57bce32d72cd1180a7f657795976130b20508b239976d3d4cdc4d0d6e6fbb9ab6471f664a662972e406f519eab8bce87a8c0365646df5acbc04c91540b4c7c518cec680a4a6af14dae1aca0fd5525220f7f0e96fcd2adef3c803ac9427fe71034b55a50536638820ef21903d09ccddd38396675b598587fa886ca711415c813fc6d69f46552b9a0a539c18f265debd0e2e286980a118ba349c216000043497fd7f826957108f4a30fd9cec3aeba79972084e90ead01ea33090000000013a63c0000b50001021bf3de4e84e3d52f9a3e36fbdcd2c4e8dbf203b9ce4fc07c2f03be6c21d0c67503f113414ebdc6c1fb0f33c99cd5a1d09dd79e7fdf2468cf1fe1af6674361695d203801fd8ab98032f11cc9e4916dd940417082727077609d5c7f8cc6e9a3ad25dd102517164b97ab46cee3826160841a36c46a2b7b9c74da37bdc070ed41ba172033a0000000001000000"
#                               "00000086"  # len
#                               "88c703c8"  # csum
#                               "1001"  # WIRE_GOSSIP_STORE_CHANNEL_UPDATE
#                               "008201021ea7c2eadf8a29eb8690511a519b5656e29aa0a853771c4e38e65c5abf43d907295a915e69e451f4c7a0c3dc13dd943cfbe3ae88c0b96667cd7d58955dbfedcf43497fd7f826957108f4a30fd9cec3aeba79972084e90ead01ea33090000000013a63c0000b500015b8d9b440000009000000000000003e8000003e800000001"
#                               "00000099"  # len
#                               "12abbbba"  # csum
#                               "1002"  # WIRE_GOSSIP_STORE_NODE_ANNOUNCEMENT
#                               "00950101cf5d870bc7ecabcb7cd16898ef66891e5f0c6c5851bd85b670f03d325bc44d7544d367cd852e18ec03f7f4ff369b06860a3b12b07b29f36fb318ca11348bf8ec00005aab817c03f113414ebdc6c1fb0f33c99cd5a1d09dd79e7fdf2468cf1fe1af6674361695d23974b250757a7a6c6549544300000000000000000000000000000000000000000000000007010566933e2607"))
#



def main():
    network = loadNetwork(networkSaveFile)
    makeAllPrivPubKeys(network) # TODO: eventually there should be a check for cmd arg to see where privkeys were already calculated


myA, update1, update2 = mvp()
h = myA.hex()[516:]
# for i in range(0, len(h), 2):
#     print(h[i]+h[i+1])
print(update1.hex()[220:])
# saved = "01021ea7c2eadf8a29eb8690511a519b5656e29aa0a853771c4e38e65c5abf43d907295a915e69e451f4c7a0c3dc13dd943cfbe3ae88c0b96667cd7d58955dbfedcf43497fd7f826957108f4a30fd9cec3aeba79972084e90ead01ea33090000000013a63c0000b500015b8d9b440000009000000000000003e8000003e800000001"
# print(saved[219:])
# lst = [(myA, CHANNEL_ANNOUNCEMENT), (update1, CHANNEL_UPDATE), (update2, CHANNEL_UPDATE)]
# writeToGossip_store(lst, "gossip_store")
#
#

print("hashTests")
h = hashlib.sha3_256(bytearray().fromhex("00")).digest()
hh = hashlib.sha3_256(h).digest()
print(hh.hex())
h = hashlib.sha256(bytearray().fromhex("00")).digest()
hh = hashlib.sha256(h).digest()
print(hh.hex())
h = hashlib.sha3_256(bytearray().fromhex("00000000")).digest()
hh = hashlib.sha3_256(h).digest()
print(hh.hex())
h = hashlib.sha256(bytearray().fromhex("00000000")).digest()
hh = hashlib.sha256(h).digest()
print(hh.hex())
