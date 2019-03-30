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
    for c in network.channels:
        c.scid.tx = 0
        c.scid.height = 0
    lstChanBlocks = blocksCoinbaseSpends(config, network.channels)
    blocksToMine = getNumBlocksToMine(lstChanBlocks)
    objRpcB, objPrivMiner, strAddrMiner, strBlockHashes = init(config, blocksToMine)
    objRpcB, cbTxs = getCoinbaseTxids(config, objRpcB)
    chanIdToChan = {}
    for chan in network.channels:
        chanIdToChan[chan.channelid] = chan
    lstSpendBlocks, lstChansOutBlocks = parallelCbSpends(config, lstChanBlocks, cbTxs, objPrivMiner)
    #spend coinbase transactions that are in spendBlocks
    xlstSpendBlocks = txBlocksToHex(lstSpendBlocks)
    coinbaseHashes, objRpcB = sendRawTxs(config, objRpcB, xlstSpendBlocks, strAddrMiner)
    #fund contracts
    dictIdToPub = crypto.parallelBtcpyPubKeys(config.processNum, network.getNodes())
    xlstFundingBlocks, txidToChan = parallelFundingTxs(config, lstSpendBlocks, lstChansOutBlocks, dictIdToPub, chanIdToChan, objPrivMiner)
    fundingHashes, objRpcB = sendRawTxs(config, objRpcB, xlstFundingBlocks, strAddrMiner)
    setRealScids(config, objRpcB, txidToChan, fundingHashes)
    killBitcoind()
    return network


def blocksCoinbaseSpends(config, channels):
    """
    calculates coinbase outputs
    :param config: config
    :param channels: list of channels
    :return: channels put into blocks of coinbase spend outputs
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
            currOutputsValue = chan.value + config.fee

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
    """
    get number blocks to mine to fund the channels including extra 100 to spend the blocks
    :param chanBlocks: the outputs of coinbase txs put in blocks
    :return: int
    """
    cbs = 0
    for block in chanBlocks:
        cbs += len(block) + 100
    blocksToMine = cbs
    return blocksToMine


def blocksFundingTxs(maxTxPerBlock, lstFundingTxs):
    """
    separate the funding transactions into blocks with config.maxTxPerBlock amount
    :param maxTxPerBlock: maxTxPerBlock
    :param lstFundingTxs: list of funding txs
    :return: list of funding blocks
    """
    lstFundingBlocks = []

    i = 0
    if i + maxTxPerBlock >= len(lstFundingTxs):
        m = len(lstFundingTxs)
    else:
        m = i + maxTxPerBlock
    while i < len(lstFundingTxs):
        lstFundingBlocks += [lstFundingTxs[i:m]]
        i = m
        if i + maxTxPerBlock >= len(lstFundingTxs):
            m = len(lstFundingTxs)
        else:
            m = m + maxTxPerBlock

    return lstFundingBlocks


def setRealScids(config, objRpcB, txidToChan, blockHashes):
    """
    the transactions that are send via sendrawtransaction are not added to a block in the same order as they are sent, 
    This function queries bitcoinCli for the block and gets the correct scid
    :param config: config
    :param objRpcB: proxy obj
    :param txidToChan: dict mapping txid to chans
    :param blockHashes: block hashes
    """
    for hash in blockHashes:
        r, objRpcB = bitcoinCli(config, objRpcB, "getblock", hash)
        txids = r["tx"]
        height = r["height"]
        for i in range(1, len(txids)):
            txid = txids[i]
            scidtxi = i
            chan = txidToChan[txid]
            chan.scid.tx = scidtxi
            chan.scid.height = height

#onchain tx creation functions

def parallelCbSpends(config, lstChanBlocks, lstCbTxs, objPrivMiner):
    """
    Create coinbase spends with config.threadNum processes
    :param config: config
    :param lstChanBlocks: list of blocks where the txs are chans that spend coinbase
    :param lstCbTxs: list of coinbase txs in hex
    :param objPrivMiner: miner priv
    :return: list of blocks with transactions that are coinbase spends, list of blocks with chans of the coinbase spent outs that matches lstSpendBlocks
    """
    processNum = config.processNum
    txidi = 0
    bundles = [[] for i in range(0, processNum)]
    p = 0
    for i in range(0, len(lstChanBlocks)):
        block = lstChanBlocks[i]
        for j in range(0, len(block)):
            bundles[p] += [(lstChanBlocks[i][j], lstCbTxs[txidi], i)]
            txidi += 1
            if p + 1 == processNum:
                p = 0
            else:
                p += 1

    for b in range(0, len(bundles)):
        bundle = bundles[b]
        bundles[b] = (config.fee, config.coinbaseReward, objPrivMiner, len(lstChanBlocks), bundle)

    p = Pool(processes=processNum)
    lstlstSpendBlocks = p.map(onChainCbTxs, bundles)
    p.close()
    lstSpendBlocks = [[] for i in range(0, len(lstChanBlocks))]
    lstChansOutBlocks = [[] for i in range(0, len(lstChanBlocks))]
    for lst in lstlstSpendBlocks:
        if lst != []:
            for i in range(0, len(lstChanBlocks)):
                lstSpendBlocks[i] += lst[0][i]
                lstChansOutBlocks[i] += lst[1][i]  #TODO change use chanIdToChan to set the correct chan objects rather than copies

    return lstSpendBlocks, lstChansOutBlocks



def onChainCbTxs(args):
    """
    create on chain coinbase txs for a set of blocks (provided in the bundle arg)
    :param args: tuple of args
    :return: list of blocks with transactions that are coinbase spends, list of blocks with chans of the coinbase spent outs that matches lstSpendBlocks
    """
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
    """
    create a single coinbase spend
    :param fee: fee
    :param reward: block reward in sat
    :param objTx: coinbase tx
    :param outputs: lst of channels (copies from originals)
    :param cbSolver: solver
    :param bPubMiner: pub of the miner
    :return: tx that spends coinbase
    """
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


def parallelFundingTxs(config, lstSpendBlocks, lstChanOutBlocks, dictIdToPub, chanIdToChan, objPrivMiner):
    """
    create funding txs that spend the txs that spend the coinbases
    :param config: config
    :param lstSpendBlocks: list of blocks with transactions that are coinbase spends
    :param lstChanOutBlocks: list of blocks with chans of the coinbase spent outs that matches lstSpendBlocks
    :param dictIdToPub: dict of nodeid to public key
    :param chanIdToChan: channelid to chan
    :param objPrivMiner: priv key of miner
    :return: list of blocks that cointain hex txs, mapping from tx to chan
    """
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
                dictTxIdChan[tup[0]] = chanIdToChan[tup[1]]
    lstFundingBlocks = blocksFundingTxs(config.maxTxPerBlock, lstFundingTxs)

    return lstFundingBlocks, dictTxIdChan


def onChainFundingTxs(args):
    """
    creates tx that funds lightning
    :param args: args
    :return: list of funding txs for outputs of a single spend of coinbase, tuple of (txid, channelid) that is used to make a dictionary in parallelFundingTxs
    """
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
            txin = spend.outs[txoi]
            txid = spend.txid
            bPubN1 = dictIdToPub[str(chan.node1.nodeid)]
            bPubN2 = dictIdToPub[str(chan.node2.nodeid)]
            fundingTx = spendToFunding(chan, txid, txin, txoi, objPrivMiner, bPubN1, bPubN2)
            lstFundingTxs += [fundingTx.hexlify()]
            tupTxidChan += [(fundingTx.txid, chan.channelid)]


    return lstFundingTxs, tupTxidChan


def spendToFunding(chan, txid, txin, txoi, objPrivMiner, bPubN1, bPubN2):
    """
    create a single lightning funding transaction
    :param chan: channel copy
    :param txid: txid
    :param txin: output we are spending
    :param txoi: input index
    :param objPrivMiner: priv key
    :param bPubN1: pub key of n1
    :param bPubN2: pub key of n2
    :return: lightning funding tx
    """

    if bPubN1.compressed < bPubN2.compressed:   #lexicographical ordering
        multisig_script = MultisigScript(2, bPubN1, bPubN2, 2)
    else:
        multisig_script = MultisigScript(2, bPubN2, bPubN1, 2)

    v = int(chan.value)
    p2wsh_multisig = P2wshV0Script(multisig_script)
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
    fundingTx = unsignedP2wsh.spend([txin], [segwitSolver])

    xmulti = p2wsh_multisig.hexlify()
    #print("chan:", chan.channelid, "txid", fundingTx.txid, "multisig:", p2wsh_multisig.hexlify())   #for debugging
    return fundingTx


#init functions

def init(config, blocksToMine):
    """
    clears any old regtest blocks
    creates rpc
    starts bitcoind
    :param config:
    :param network:
    :return: proxy obj, miner priv, miner addr, block hashes of coinbases that can be spent
    """
    clearBitcoinChain(config)
    startBitcoind(config)
    objRpcB = Proxy(btc_conf_file=config.bitcoinConfPath)
    objRpcB = waitForBitcoind(config, objRpcB)
    objPrivMiner = pycrypto.PrivateKey(config.bCoinbasePriv)
    pubMiner = objPrivMiner.pub(compressed=True)
    xPubMiner = str(pubMiner)
    strAddrMiner = str(pubMiner.to_address(mainnet=False))
    objRpcB = addPrivToBitcoind(config, objRpcB, config.iCoinbasePriv, xPubMiner, strAddrMiner)
    hundredBlockRounds = blocksToMine // 1000
    remainder = blocksToMine % 1000
    strBlockHashes = []
    for i in range(0, hundredBlockRounds):
        hashes, objRpcB = bitcoinCli(config, objRpcB, "generatetoaddress", 1000, strAddrMiner)
        strBlockHashes += hashes
    if remainder != 0:
        hashes, objRpcB = bitcoinCli(config, objRpcB, "generatetoaddress", remainder, strAddrMiner)
        strBlockHashes += hashes

    return objRpcB, objPrivMiner, strAddrMiner, strBlockHashes


def clearBitcoinChain(config):
    """
    Delete the data dir and makes new one
    """
    if os.path.exists(config.bitcoinDataDir):
        shutil.rmtree(config.bitcoinDataDir)
    os.makedirs(config.bitcoinDataDir, exist_ok=True)


#starting bitcoind
def startBitcoind(config):
    """
    start bitcoind using subprocess. Sets bitcoin conf location and data directory according to config or cmd args
    :param config: config
    """
    currPath = os.getcwd()
    os.chdir(config.bitcoinSrcDir)
    e = subprocess.run(["./bitcoind", "--daemon", "--conf=" + config.bitcoinConfPath, "--datadir=" + config.bitcoinDataDir, "--txindex"])
    if e.returncode == 1:
        raise ConnectionRefusedError("Bitcoind is already running. pkill bitcoind before running.")
    os.chdir(currPath)


def waitForBitcoind(config, objRpcB):
    """
    wait until bitcoind has initialized before continuing
    :param config: config
    :param objRpcB: proxy object
    :return: latest proxy object
    """
    # TODO Fix this sleep because it is very hacky
    time.sleep(4)
    while True:
        try:
            r, objRpcB = bitcoinCli(config, objRpcB, "getrpcinfo")
            return objRpcB
        except InWarmupError:
            time.sleep(.5)


def addPrivToBitcoind(config, objRpcB, iPriv, xPubMiner, strAddrMiner):
    """
    add private key, public key and address to bitcoind so that listunspent shows spendable coinbase txs
    :param config: config
    :param objRpcB: proxy object
    :param iPriv: int private key of miner
    :param xPubMiner: hex pubkey of miner
    :param strAddrMiner: str base58 addr of miner
    :return: latest proxy object
    """
    xPriv = iPriv.to_bytes(32, "big").hex()
    wifPriv = wif.privToWif(xPriv)
    r, objRpcB = bitcoinCli(config, objRpcB, "importprivkey", wifPriv)
    r, objRpcB = bitcoinCli(config, objRpcB, "importpubkey", xPubMiner)
    r, objRpcB = bitcoinCli(config, objRpcB, "importaddress", strAddrMiner)
    return objRpcB


def killBitcoind():
    """
    pkills bitcoind
    """
    subprocess.run(["pkill", "bitcoind"])


def bitcoinCli(config, objRpcB, cmd, *args):
    """
    runs a bitcoin client command using the proxy object. If connection is broken, we create a new object and try again.
    Every call to bitcoinCli should use this wrapper
    :param config: config
    :param objRpcB: proxy object
    :param cmd: str of command to call
    :param args: arguments to pass into command
    :return: result of bitcoin-cli call, latest proxy object
    """
    while True:
        try:
            r = objRpcB.call(cmd, *args)
            break
        except BrokenPipeError:
            objRpcB = Proxy(btc_conf_file=config.bitcoinConfPath)

    return r, objRpcB


def getCoinbaseTxids(config, objRpcB):
    """
    get txids of coinbase txs that are spendable
    :param config: config
    :param objRpcB: proxy object
    :return: lastest proxy object, str txids of spendable coinbases
    """
    unspentTxs, objRpcB = bitcoinCli(config, objRpcB, "listunspent")
    txs = []
    for tx in unspentTxs:
        txid = tx["txid"]
        r, objRpcB = bitcoinCli(config, objRpcB, "gettransaction", txid)
        xtx = r["hex"]
        txs += [xtx]
    return objRpcB, txs


def txBlocksToHex(lstSpendBlocks):
    """
    turns txs to hexs because transactions cannot be sent as input into multiprocessing
    :param lstSpendBlocks:
    :return: list of blocks with transactions that are coinbase spends
    """
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

