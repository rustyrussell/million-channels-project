from btcpy.structs import crypto as pycrypto
from btcpy.structs.transaction import SegWitTransaction, Sequence, TxOut, Locktime, TxIn, MutableTransaction, P2wpkhV0Script
from btcpy.structs.sig import P2pkhSolver, ScriptSig, P2wpkhV0Solver, MultisigScript, P2wshV0Script
from bitcoin.rpc import Proxy, InWarmupError
import os
import shutil
from common import wif, crypto
import subprocess
import time
from multiprocessing import Pool


def buildChain(config, network):
    chanBlocks = blocksCoinbaseSpends(config, network.channels)
    blocksToMine = getNumBlocksToMine(chanBlocks)
    objRpcB, objPrivMiner, strAddrMiner, strBlockHashes = init(config, blocksToMine)
    cbTxs = getCoinbaseTxids(objRpcB)
    lstSpendBlocks, lstChansOutBlocks = parallelCbSpends(config, chanBlocks, cbTxs, objPrivMiner)
    #spend coinbase transactions that are in spendBlocks
    xlstSpendBlocks = txBlocksToHash(lstSpendBlocks)
    coinbaseHashes, objRpcB = sendRawTxs(config, objRpcB, xlstSpendBlocks, strAddrMiner)
    #fund contracts
    dictIdToPub = crypto.parallelBtcpyPubKeys(config.processNum, network.getNodes())
    xlstFundingBlocks, txidToChan = parallelFundingTxs(config, lstSpendBlocks, lstChansOutBlocks, dictIdToPub, objPrivMiner)
    fundingHashes, objRpcB = sendRawTxs(config, objRpcB, xlstFundingBlocks, strAddrMiner)
    setRealScids(config, objRpcB, txidToChan, fundingHashes)
    killBitcoind()


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
    txPerBlock = config.maxTxPerBlock
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


def blocksFundingTxs(maxFundingTxPerBlock, lstFundingTxs):
    lstFundingBlocks = []

    i = 0
    if i + maxFundingTxPerBlock >= len(lstFundingTxs):
        m = len(lstFundingTxs)
    else:
        m = i + maxFundingTxPerBlock
    while i < len(lstFundingTxs):
        lstFundingBlocks += [lstFundingTxs[i:m]]
        prevM = m
        if i + maxFundingTxPerBlock >= len(lstFundingTxs):
            m = len(lstFundingTxs)
        else:
            m = i + maxFundingTxPerBlock
        i = prevM

    return lstFundingBlocks


def setRealScids(config, objRpcB, txidToChan, blockHashes):
    for hash in blockHashes:
        txids, objRpcB = bitcoinCli(config, objRpcB, "getblock", hash)
        txids = txids["tx"]
        for i in range(1, len(txids)):
            txid = txids[i]
            scidtxi = i
            chan = txidToChan[txid]
            chan.scid.tx = scidtxi


#onchain tx creation functions

def parallelCbSpends(config, lstBlocks, lstCbTxs, objPrivMiner):
    processNum = config.processNum
    txidi = 0
    bundles = [[] for i in range(0, processNum)]
    p = 0
    for i in range(0, len(lstBlocks)):
        block = lstBlocks[i]
        for j in range(0, len(block)):
            bundles[p] += [(lstBlocks[i][j], lstCbTxs[txidi], i)]
            txidi += 1
            if p + 1 == processNum:
                p = 0
            else:
                p += 1


    for b in range(0, len(bundles)):
        bundle = bundles[b]
        bundles[b] = (config.fee, config.coinbaseReward, objPrivMiner, len(lstBlocks), bundle)

    p = Pool(processes=processNum)
    lstlstSpendBlocks = p.map(onChainCbTxs, bundles)
    p.close()
    lstSpendBlocks = [[] for i in range(0, len(lstBlocks))]
    lstChansOutBlocks = [[] for i in range(0, len(lstBlocks))]
    for lst in lstlstSpendBlocks:
        if lst != []:
            for i in range(0, len(lstBlocks)):
                lstSpendBlocks[i] += lst[0][i]
                lstChansOutBlocks[i] += lst[1][i]

    return lstSpendBlocks, lstChansOutBlocks



def onChainCbTxs(args):
    fee = args[0]
    reward = args[1]
    objPrivMiner = args[2]
    iBlocks = args[3]
    bundle = args[4]
    cbSolver = P2pkhSolver(objPrivMiner)
    lstSpendBlocks = [[] for i in range(0, iBlocks)]
    lstChansOutBlocks = [[] for i in range(0, iBlocks)]
    bPubMiner = objPrivMiner.pub(compressed=True)

    for i in range(0, len(bundle)):
        outputs = bundle[i][0]
        xTx = bundle[i][1]
        bi = bundle[i][2]
        objTx = SegWitTransaction.unhexlify(xTx)
        cbSpend = spendCb(fee, reward, objTx, outputs, cbSolver, bPubMiner)
        lstSpendBlocks[bi] += [cbSpend]
        lstChansOutBlocks[bi] += [outputs]

    return lstSpendBlocks, lstChansOutBlocks



def spendCb(fee, reward, objTx, outputs, cbSolver, bPubMiner):
    outs = []
    totVal = 0
    script = P2wpkhV0Script(bPubMiner)
    for o in outputs:
        v = int(o.value)
        v += fee
        totVal += v
        outs += [TxOut(value=v,
                       n=0,
                       script_pubkey=script)]

    change = reward - totVal - fee
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


def parallelFundingTxs(config, lstSpendBlocks, lstChanOutBlocks, dictIdToPub, objPrivMiner):
    processNum = config.processNum

    bundles = [[] for i in range(0, processNum)]

    p = 0
    for i in range(0, len(lstSpendBlocks)):
        block = lstSpendBlocks[i]
        for j in range(0, len(block)):
            bundles[p] += [(lstSpendBlocks[i][j], lstChanOutBlocks[i][j])]
            if p + 1 == processNum:
                p = 0
            else:
                p += 1

    for i in range(0, len(bundles)):
        bundle = bundles[i]
        bundles[i] = (dictIdToPub, objPrivMiner, bundle)

    p = Pool(processes=processNum)
    r = p.map(onChainFundingTxs, bundles)
    p.close()
    lstFundingTxs = []
    dictTxIdChan = {}
    for lst in r:
        if lst != []:
            lstFundingTxs += lst[0]
            for tup in lst[1]:
                dictTxIdChan[tup[0]] = tup[1]
    lstFundingBlocks = blocksFundingTxs(config.maxTxPerBlock, lstFundingTxs)

    return lstFundingBlocks, dictTxIdChan


def onChainFundingTxs(args):
    dictIdToPub = args[0]
    objPrivMiner = args[1]
    bundle = args[2]
    lstFundingTxs= []
    tupTxidChan = []
    for i in range(0, len(bundle)):
        spend = bundle[i][0]
        chans = bundle[i][1]
        for k in range(0, len(chans)):
            chan = chans[k]
            txoi = k
            txout = spend.outs[txoi]
            txid = spend.txid
            bPubN1 = dictIdToPub[str(chan.node1.nodeid)]
            bPubN2 = dictIdToPub[str(chan.node2.nodeid)]
            fundingTx = spendToFunding(chan, txid, txout, txoi, objPrivMiner, bPubN1, bPubN2)
            lstFundingTxs += [fundingTx.hexlify()]
            tupTxidChan += [(fundingTx.txid, chan)]


    return lstFundingTxs, tupTxidChan


def spendToFunding(chan, txid, txout, txoi, objPrivMiner, bPubN1, bPubN2):

    if bPubN1.compressed < bPubN2.compressed:   #lexicographical ordering
        multisig_script = MultisigScript(2, bPubN1, bPubN2, 2)
    else:
        multisig_script = MultisigScript(2, bPubN2, bPubN1, 2)

    v = int(chan.value)
    p2wsh_multisig = P2wshV0Script(multisig_script)
    # print("scid:", chan.scid.tx, "multisig:", p2wsh_multisig.hexlify())
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
    strBlockHashes, objRpcB = bitcoinCli(config, objRpcB, "generatetoaddress", blocksToMine, strAddrMiner)

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


def mineNBlocks(config, objRpcB, strAddrMiner, blocksToMine):
    while True:
        try:
            strBlockHashes = objRpcB.call("generatetoaddress", blocksToMine, strAddrMiner)
            break
        except BrokenPipeError:
            objRpcB = Proxy(btc_conf_file=config.bitcoinDataDir + config.bitcoinConf)

    return strBlockHashes


def bitcoinCli(config, objRpcB, cmd, *args):
    while True:
        try:
            r = objRpcB.call(cmd, *args)
            break
        except BrokenPipeError:
            objRpcB = Proxy(btc_conf_file=config.bitcoinDataDir + config.bitcoinConf)

    return r, objRpcB


def getCoinbaseTxids(objRpcB):
    unspentTxs = objRpcB.call("listunspent")
    txs = []
    for tx in unspentTxs:
        txid = tx["txid"]
        r = objRpcB.call("gettransaction", txid)
        xtx = r["hex"]
        txs += [xtx]
    return txs


def txBlocksToHash(lstSpendBlocks):
    xlstSpendBlocks = [[] for i in range(0, len(lstSpendBlocks))]
    for i in range(0, len(lstSpendBlocks)):
        block = lstSpendBlocks[i]
        for j in range(0, len(block)):
            xlstSpendBlocks[i] += [lstSpendBlocks[i][j].hexlify()]

    return xlstSpendBlocks


def sendRawTxs(config, objRpcB, xTxBlocks, strAddrMiner):
    """
    sends raw transactions and creates blocks. All txs will have at least 6 confirmations.
    :param objRpcB:
    :param spendBlocks: lists of "blocks" that are lists of transactions. Txs in each "block" is assumed to fit in a single bitcoin block
    :param strAddrMiner: miner address
    :return: hashes of non-empty blocks (so all blocks except last 5 confirmations)
    """
    blockHashes = []
    for i in range(0, len(xTxBlocks)):
        block = xTxBlocks[i]
        for j in range(0, len(block)):
            xtx = block[j]
            txid, objRpcB = bitcoinCli(config, objRpcB, "sendrawtransaction", xtx)
        r, objRpcB = bitcoinCli(config, objRpcB, "generatetoaddress", 1, strAddrMiner)
        blockHashes += r
    r, objRpcB = bitcoinCli(config, objRpcB, "generatetoaddress", 5, strAddrMiner)  # get 6 confirmations on last group of transactions
    return blockHashes, objRpcB

