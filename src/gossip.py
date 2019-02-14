import os
import pickle
from config import *
from common.networkClasses import *
from random import randint
import common.wif as wif
from bitcoin.wallet import CBitcoinSecret, P2PKHBitcoinAddress
from bitcoin import SelectParams
import hashlib
from bitcoin.signmessage import BitcoinMessage, VerifyMessage, SignMessage
import base64
import sys

chainHash = bytearray.fromhex('06226e46111a0b59caaf126043eb5bbf28c34f3a5e332a1fc7b2b73cf188910f')
announcementType = bytearray().fromhex("0100")
featureLen = bytearray().fromhex("0000")
features = bytearray()
scid = bytearray([0, 0, 10, 0, 0, 2, 0, 1])   # for now we are placing it in the 10th block, 2nd transactions, 1st output

def mvp():
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
    nodesig1 = bytearray(sign(node1.cPrivObj, h))
    nodesig2 = bytearray(sign(node2.cPrivObj, h))
    bitcoinSig1 = bytearray(sign(cBitcoinPrivObj1, h))
    bitcoinSig2 = bytearray(sign(cBitcoinPrivObj2, h))

    a.setNodeSig1(nodesig1)
    a.setNodeSig2(nodesig2)
    a.setBitcoinSig1(bitcoinSig1)
    a.setBitcoinSig2(bitcoinSig2)

    finalA = a.serialize(full=True)
    print(finalA.hex())
    print()

_bchr = chr
_bord = ord
if sys.version > '3':
    long = int
    _bchr = lambda x: bytes([x])
    _bord = lambda x: x

def sign(key, h):
    sig, i = key.sign_compact(h)
    meta = 27 + i
    if key.is_compressed:
        meta += 4
    return base64.b64encode(_bchr(meta) + sig)

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
            a = announcementType + self.featureLen + self.features + chainHash + self.scid + \
                self.id1 + self.id2 + self.bitcoinKey1 + self.bitcoinKey2
        else:
            a = announcementType + self.sig1 + self.sig2 + self.bitcoinSig1 + \
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
        return h





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



def loadNetwork(networkFilename):
    fp = open(networkFilename, "rb")
    network = pickle.load(fp)
    return network



#from tests in c-lightning
# with open(os.path.join("/home/jnetti/.lightning/experiments/testNodes/1", 'gossip_store'), 'wb') as f:
#     f.write(bytearray.fromhex("03"  # GOSSIP_VERSION
#                               "000001bc"  # len
#                               "521ef598"  # csum
#                               "1000"  # WIRE_GOSSIP_STORE_CHANNEL_ANNOUNCEMENT
#                               "01b00100bb8d7b6998cca3c2b3ce12a6bd73a8872c808bb48de2a30c5ad9cdf835905d1e27505755087e675fb517bbac6beb227629b694ea68f49d357458327138978ebfd7adfde1c69d0d2f497154256f6d5567a5cf2317c589e0046c0cc2b3e986cf9b6d3b44742bd57bce32d72cd1180a7f657795976130b20508b239976d3d4cdc4d0d6e6fbb9ab6471f664a662972e406f519eab8bce87a8c0365646df5acbc04c91540b4c7c518cec680a4a6af14dae1aca0fd5525220f7f0e96fcd2adef3c803ac9427fe71034b55a50536638820ef21903d09ccddd38396675b598587fa886ca711415c813fc6d69f46552b9a0a539c18f265debd0e2e286980a118ba349c216000043497fd7f826957108f4a30fd9cec3aeba79972084e90ead01ea33090000000013a63c0000b50001021bf3de4e84e3d52f9a3e36fbdcd2c4e8dbf203b9ce4fc07c2f03be6c21d0c67503f113414ebdc6c1fb0f33c99cd5a1d09dd79e7fdf2468cf1fe1af6674361695d203801fd8ab98032f11cc9e4916dd940417082727077609d5c7f8cc6e9a3ad25dd102517164b97ab46cee3826160841a36c46a2b7b9c74da37bdc070ed41ba172033a0000000001000000"))
#


def main():
    network = loadNetwork(buildNetwork.networkSaveFile)
    makeAllPrivPubKeys(network) # TODO: eventually there should be a check for cmd arg to see where privkeys were already calculated



mvp()
