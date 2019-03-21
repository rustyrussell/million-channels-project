from btcpy.structs import crypto
from btcpy.structs.transaction import SegWitTransaction, Witness, Transaction, Sequence, TxOut, Locktime, ScriptBuilder, TxIn, MutableTransaction, MutableSegWitTransaction, CoinBaseTxIn, CoinBaseScriptSig, P2wpkhV0Script
from btcpy.structs.sig import P2pkhSolver, P2shScript, P2pkhScript, ScriptSig, P2wpkhV0Solver, MultisigScript, MultisigSolver, P2wshV0Script, P2wshV0Solver
from bitcoin.rpc import Proxy

def buildChain(config, network):
    # init(config, network)

    channels = network.channels
    print(calcNetworkValue(network))

    #sort channels in order of scid


def init(config, network):
    clearBitcoinChain()
    blocksToMine = getNumBlocksToMine()
    brpc = Proxy(btc_conf_file=config.bitcoindPath)
    # mineNBlocks(blocksToMine)

    return brpc



def clearBitcoinChain():
    pass


def calcNetworkValue(network):
    """
    network value
    :param network: network
    :return:
    """
    networkValue = 0
    for c in network.channels:  #TODO ERROR! some channels don't have values. need to fix build network!
        if c.value is None:
            pass
            # print("in channel list: scid", c.scid, "of node1", c.node1.nodeid, "node2", c.node2.nodeid, "has None value")
        networkValue += c.value
    return networkValue


def getNumBlocksToMine():
    default = 100  #first 100 blocks are empty




