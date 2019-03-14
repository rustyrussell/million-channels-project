from random import randint
import common.wif as wif
from bitcoin.wallet import CBitcoinSecret, P2PKHBitcoinAddress


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

def getAddr(pub):
    addrObj = P2PKHBitcoinAddress.from_pubkey(pub)
    addr = addrObj.hex()
    #TODO: add prefix https://en.bitcoin.it/wiki/List_of_address_prefixes
    return addr

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


