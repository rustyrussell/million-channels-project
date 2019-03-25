from btcpy.structs import crypto as pycrypto
from btcpy.structs.transaction import SegWitTransaction, Sequence, TxOut, Locktime, TxIn, MutableTransaction, P2wpkhV0Script
from btcpy.structs.sig import P2pkhSolver, ScriptSig, P2wpkhV0Solver, MultisigScript, P2wshV0Script
from bitcoin.rpc import Proxy, InWarmupError
import os
import shutil
from common import wif
import subprocess
import time



def buildChain(config, network):
    chanBlocks = blocksCoinbaseSpends(config, network.channels)
    blocksToMine = getNumBlocksToMine(chanBlocks)
    objRpcB, objPrivMiner, strAddrMiner, strBlockHashes = init(config, blocksToMine)
    cbTxs = getCoinbaseTxids(objRpcB)
    spendBlocks, txs = onChainCbTxs(config, chanBlocks, cbTxs, objPrivMiner)
    #spend coinbase transactions that are in spendBlocks
    sendRawTxs(objRpcB, spendBlocks, strAddrMiner)
    #fund contracts
    fundingBlocks, txidToChan = onChainFundingTxs(config, txs, network.channels, objPrivMiner)
    blockHashes = sendRawTxs(objRpcB, fundingBlocks, strAddrMiner)
    setRealScids(objRpcB, txidToChan, blockHashes)
    killBitcoind()


def setRealScids(objRpcB, txidToChan, blockHashes):
    for hash in blockHashes:
        txids = objRpcB.call("getblock", hash)["tx"]
        for i in range(1, len(txids)):
            txid = txids[i]
            scidtxi = i
            chan = txidToChan[txid]
            chan.scid.tx = scidtxi


def blocksCoinbaseSpends(config, channels):
    """
    calculates coinbase outputs
    :param config:
    :param channels:
    :return:
    """
    coinbaseTxs = []
    currOutputs = []
    currOutputsValue = config.fee
    txPerBlock = 100
    blocks = []
    for i in range(0, len(channels)):
        chan = channels[i]
        value = chan.value
        if (currOutputsValue + value + config.fee) < config.coinbaseReward and len(currOutputs) < config.maxOutputsPerTx:
            currOutputs += [chan]
            currOutputsValue += value + config.fee
        else:
            coinbaseTxs += [currOutputs]
            currOutputs = [chan]
            currOutputsValue = config.fee

        if len(coinbaseTxs) == txPerBlock:
            blocks += [coinbaseTxs]
            currOutputs = []
            coinbaseTxs = []

    if currOutputs != []:
        coinbaseTxs += [currOutputs]
    if coinbaseTxs != []:
        blocks += [coinbaseTxs]

    return blocks



def getNumBlocksToMine(chanBlocks):
    cbs = 0
    for block in chanBlocks:
        cbs += len(block)
    blocksToMine = cbs + 100
    return blocksToMine


def onChainCbTxs(config, chanBlocks, cbTxs, objMinerPriv):
    txidi = 0
    cbSolver = P2pkhSolver(objMinerPriv)
    txs = []
    spendBlocks = [[] for i in range(0, len(chanBlocks))]
    bPubMiner = objMinerPriv.pub(compressed=True)
    for i in range(0, len(chanBlocks)):
        chanBlock = chanBlocks[i]
        for j in range(0, len(chanBlock)):
            xTx = cbTxs[txidi]
            objTx = SegWitTransaction.unhexlify(xTx)
            outputs = chanBlock[j]
            cbSpend = spendCb(config, objTx, outputs, cbSolver, bPubMiner)
            txs += [cbSpend]
            spendBlocks[i] += [cbSpend]
            txidi += 1

    return spendBlocks, txs



def spendCb(config, objTx, outputs, cbSolver, bPubMiner):
    outs = []
    totVal = 0
    script = P2wpkhV0Script(bPubMiner)
    for o in outputs:
        v = int(o.value)
        v += config.fee
        totVal += v
        outs += [TxOut(value=v,
                       n=0,
                       script_pubkey=script)]

    change = config.coinbaseReward - totVal - config.fee
    outsWithChange = outs + [TxOut(value=change, n=0, script_pubkey=objTx.outs[0].script_pubkey)]
    unsignedSegwit = MutableTransaction(version=1,
                                        ins=[TxIn(txid=objTx.txid,
                                                  txout=0,
                                                  script_sig=ScriptSig.empty(),
                                                  sequence=Sequence.max())],
                                        outs=outsWithChange,
                                        locktime=Locktime(0)
                                        )
    segwitTx = unsignedSegwit.spend([objTx.outs[0]], [cbSolver])
    return segwitTx



def onChainFundingTxs(config, txs, channels, objPrivMiner):
    fundingBlocks = []
    txidToChan = {}
    txi = 0
    txoi = 0
    j = 1
    block = []
    for i in range(0, len(channels)):
        chan = channels[i]
        txout = txs[txi].outs[txoi]
        txid = txs[txi].txid
        fundingTx = spendToFunding(chan, txid, txout, txoi, objPrivMiner)
        block += [fundingTx]
        txidToChan[fundingTx.txid] = chan
        print("scid:", chan.scid.tx, chan.scid.height, "txid:", fundingTx.txid, "fundingtx", fundingTx.hexlify())
        if j == config.maxFundingTxPerBlock:
            fundingBlocks += [block]
            block = []
        else:
            j += 1

        if txoi + 2 == len(txs[txi].outs):
            txoi = 0
            txi += 1
        else:
            txoi += 1

    if block != []:
        fundingBlocks += [block]

    return fundingBlocks, txidToChan


def spendToFunding(chan, txid, txout, txoi, objPrivMiner):
    node1 = chan.node1
    node2 = chan.node2
    n1Id = node1.nodeid
    n2Id = node2.nodeid
    iPrivN1 = n1Id + 1
    iPrivN2 = n2Id + 1
    bPrivN1 = iPrivN1.to_bytes(32, "big")
    bPrivN2 = iPrivN2.to_bytes(32, "big")
    objPrivN1 = pycrypto.PrivateKey(bPrivN1)
    objPrivN2 = pycrypto.PrivateKey(bPrivN2)
    objPubN1 = objPrivN1.pub(compressed=True)
    objPubN2 = objPrivN2.pub(compressed=True)
    if objPubN1.compressed < objPubN2.compressed:   #lexicographical ordering
        multisig_script = MultisigScript(2, objPubN1, objPubN2, 2)
    else:
        multisig_script = MultisigScript(2, objPubN2, objPubN1, 2)

    v = int(chan.value)
    p2wsh_multisig = P2wshV0Script(multisig_script)
    print("scid:", chan.scid.tx, chan.scid.height, "multisig:", p2wsh_multisig.hexlify())
    unsignedP2wsh = MutableTransaction(version=0,
                                       ins=[TxIn(txid=txid,
                                                 txout=txoi,
                                                 script_sig=ScriptSig.empty(),
                                                 sequence=Sequence.max())],
                                       outs=[TxOut(value=v,
                                                   n=0,
                                                   script_pubkey=p2wsh_multisig)],
                                       locktime=Locktime(0)
                                       )
    segwitSolver = P2wpkhV0Solver(privk=objPrivMiner)
    fundingTx = unsignedP2wsh.spend([txout], [segwitSolver])
    return fundingTx




#init functions

def init(config, blocksToMine):
    """
    clears any old regtest blocks
    creates rpc
    starts bitcoind
    :param config:
    :param network:
    :return:
    """
    clearBitcoinChain(config)
    startBitcoind(config)
    objRpcB = Proxy(btc_conf_file=config.bitcoinDataDir + config.bitcoinConf)
    waitForBitcoind(objRpcB)
    objPrivMiner = pycrypto.PrivateKey(config.bCoinbasePriv)
    pubMiner = objPrivMiner.pub(compressed=True)
    xPubMiner = str(pubMiner)
    strAddrMiner = str(pubMiner.to_address(mainnet=False))
    addPrivToBitcoind(objRpcB, config.iCoinbasePriv, xPubMiner, strAddrMiner)
    strBlockHashes = mineNBlocks(objRpcB, strAddrMiner, blocksToMine)

    return objRpcB, objPrivMiner, strAddrMiner, strBlockHashes


def clearBitcoinChain(config):
    """
    Delete the blocks dir and chainstate dir
    :return:
    """
    if os.path.exists(config.bitcoinDataDir + "blocks"):
        shutil.rmtree(config.bitcoinDataDir + "blocks")
    if os.path.exists(config.bitcoinDataDir + "chainstate"):
        shutil.rmtree(config.bitcoinDataDir + "chainstate")
    if os.path.exists(config.bitcoinDataDir + "indexes"):
        shutil.rmtree(config.bitcoinDataDir + "indexes")
    if os.path.exists(config.bitcoinDataDir + "wallet.dat"):
        os.remove(config.bitcoinDataDir + "wallet.dat")



#calling bitcoind
def startBitcoind(config):
    currPath = os.getcwd()
    os.chdir(config.bitcoinSrcDir)
    e = subprocess.run(["./bitcoind", "--daemon", "--conf=" + config.bitcoinConf, "--txindex"])
    if e.returncode == 1:
        raise ConnectionRefusedError("Bitcoind is already running. pkill bitcoind before running.")
    os.chdir(currPath)


def waitForBitcoind(objRpcB):
    # TODO Fix this sleep because it is very hacky
    time.sleep(4)
    while True:
        try:
            objRpcB.call("getrpcinfo")
            return objRpcB
        except InWarmupError:
            time.sleep(.5)



def addPrivToBitcoind(objRpcB, iPriv, xPubMiner, strAddrMiner):
    xPriv = iPriv.to_bytes(32, "big").hex()
    wifPriv = wif.privToWif(xPriv)
    objRpcB.call("importprivkey", wifPriv)
    objRpcB.call("importpubkey", xPubMiner)
    objRpcB.call("importaddress", strAddrMiner)


def killBitcoind():
    subprocess.run(["pkill", "bitcoind"])


def mineNBlocks(objRpcB, strAddrMiner, blocksToMine):
    strBlockHashes = objRpcB.call("generatetoaddress", blocksToMine, strAddrMiner)
    return strBlockHashes


def getCoinbaseTxids(objRpcB):
    unspentTxs = objRpcB.call("listunspent")
    txs = []
    for tx in unspentTxs:
        txid = tx["txid"]
        r = objRpcB.call("gettransaction", txid)
        xtx = r["hex"]
        txs += [xtx]
    return txs



def sendRawTxs(objRpcB, spendBlocks, strAddrMiner):
    """
    sends raw transactions and creates blocks. All txs will have at least 6 confirmations.
    :param objRpcB:
    :param spendBlocks: lists of "blocks" that are lists of transactions. Txs in each "block" is assumed to fit in a single bitcoin block
    :param strAddrMiner: miner address
    :return: hashes of non-empty blocks (so all blocks except last 5 confirmations)
    """
    blockHashes = []
    for i in range(0, len(spendBlocks)):
        block = spendBlocks[i]
        for j in range(0, len(block)):
            tx = block[j]
            xtx = tx.hexlify()
            txid = objRpcB.call("sendrawtransaction", xtx, False)
        blockHashes += mineNBlocks(objRpcB, strAddrMiner, 1)
    mineNBlocks(objRpcB, strAddrMiner, 5)  # get 6 confirmations on last group of transactions
    return blockHashes


