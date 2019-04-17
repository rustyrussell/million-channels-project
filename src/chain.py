from btcpy.structs import crypto as pycrypto
from btcpy.structs.transaction import SegWitTransaction, Sequence, TxOut, Locktime, TxIn, MutableTransaction
from btcpy.structs.sig import P2pkhSolver, ScriptSig, MultisigScript, P2wshV0Script
from bitcoin.rpc import Proxy, InWarmupError
import os
import shutil
from common import wif, crypto, utility
import subprocess
import time
from multiprocessing import Pool


def buildChain(config, network):
    scaleCapacities(config, network.channels, network.getNodes())
    for n in network.getNodes():
        n.channels = []
    for c in network.channels:
        c.scid.tx = 0
        c.scid.height = 0
        c.output = 0
    lstChanBlocks = blocksCoinbaseSpends(config, network.channels)
    blocksToMine = getNumBlocksToMine(lstChanBlocks)
    objRpcB, objPrivMiner, strAddrMiner, hashesCb = init(config, blocksToMine)
    objRpcB, lstCbTxs = getCoinbaseTxids(config, objRpcB, hashesCb)
    chanIdToChan = {}
    for chan in network.channels:
        chanIdToChan[chan.channelid] = chan
    dictIdToPub = crypto.parallelBtcpyPubKeys(config.processNum, network.getNodes())
    lstSpendBlocks, dictTxidToChans = parallelCbSpends(config, lstChanBlocks, lstCbTxs, dictIdToPub, objPrivMiner)
    #spend coinbase transactions that are in spendBlocks
    xlstSpendBlocks = txBlocksToHex(lstSpendBlocks)
    spendHashes, objRpcB = sendRawTxs(config, objRpcB, xlstSpendBlocks, strAddrMiner)
    objRpcB = setRealScids(config, objRpcB, dictTxidToChans, chanIdToChan, spendHashes)
    killBitcoind()
    return network


def scaleCapacities(config, channels, nodes):
    """
    scale capacities according to the units in config.capacities.
    :param config: config
    :param channels: channels objs
    """
    div = utility.getScaleDiv(config.scalingUnits)
    for c in channels:
        c.value = utility.scaleSatoshis(c.value, div)
    for n in nodes:
        n.value = utility.scaleSatoshis(n.value, div)


def blocksCoinbaseSpends(config, channels):
    """
    calculates coinbase outputs
    :param config: config
    :param channels: list of channels
    :return: channels put into blocks of coinbase spend outputs
    """
    coinbaseTxs = []
    currOutputs = []
    currOutputsValue = 0
    txPerBlock = config.maxTxPerBlock
    blocks = []
    coinbaseReward = config.coinbaseReward    #50 bitcoins
    copyChannels = channels.copy()
    copyChannels.sort(key=utility.sortByChanValue, reverse=True) #sorting in reverse because larger coinbase reward can comes first
    icbs = 1
    for i in range(0, len(copyChannels)):
        chan = copyChannels[i]
        value = chan.value
        if (currOutputsValue + value + config.fee) < coinbaseReward and len(currOutputs) < config.maxOutputsPerTx:
            currOutputs += [chan]
            currOutputsValue += value
        else:
            coinbaseTxs += [(currOutputs, coinbaseReward)]
            icbs += 1
            if icbs == config.halvingInterval:
                coinbaseReward = int(coinbaseReward / 2)
                icbs = 0
            currOutputs = [chan]
            currOutputsValue = chan.value

        if len(coinbaseTxs) == txPerBlock:
            blocks += [coinbaseTxs]
            coinbaseTxs = []

    if currOutputs != []:
        coinbaseTxs += [(currOutputs, coinbaseReward)]
    if coinbaseTxs != []:
        blocks += [coinbaseTxs]

    return blocks

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


#onchain tx creation functions

def parallelCbSpends(config, lstChanBlocks, lstCbTxs, dictIdToPub, objPrivMiner):
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
            #print(txidi, ":", SegWitTransaction.unhexlify(lstCbTxs[txidi]).outs[0].value, lstChanBlocks[i][j][1])
            txidi += 1
            if p + 1 == processNum:
                p = 0
            else:
                p += 1

    for b in range(0, len(bundles)):
        bundle = bundles[b]
        bundles[b] = (config.fee, objPrivMiner, dictIdToPub, len(lstChanBlocks), bundle)

    p = Pool(processes=processNum)
    lstlstSpendBlocks = p.map(onChainCbTxs, bundles)
    p.close()
    lstSpendBlocks = [[] for i in range(0, len(lstChanBlocks))]
    dictTxidChans = {}
    for lst in lstlstSpendBlocks:
        if lst != []:
            for i in range(0, len(lstChanBlocks)):
                lstSpendBlocks[i] += lst[0][i]
            for tup in lst[1]:
                dictTxidChans[tup[0]] = tup[1]

    return lstSpendBlocks, dictTxidChans



def onChainCbTxs(args):
    """
    create on chain coinbase txs for a set of blocks (provided in the bundle arg)
    :param args: tuple of args
    :return: list of blocks with transactions that are coinbase spends, list of blocks with chans of the coinbase spent outs that matches lstSpendBlocks
    """
    fee = args[0]
    objPrivMiner = args[1]
    dictIdToPub = args[2]
    iBlocks = args[3]
    bundle = args[4]
    cbSolver = P2pkhSolver(objPrivMiner)
    lstSpendBlocks = [[] for i in range(0, iBlocks)]
    lstTupTxidChans = []
    rewards = []
    for i in range(0, len(bundle)):
        outputs = bundle[i][0][0]
        reward = bundle[i][0][1]
        xTx = bundle[i][1]
        bi = bundle[i][2]
        objTx = SegWitTransaction.unhexlify(xTx)
        cbSpend, tupTxidChans = spendCb(fee, reward, objTx, outputs, cbSolver, dictIdToPub)
        lstTupTxidChans += [tupTxidChans]
        lstSpendBlocks[bi] += [cbSpend]
        rewards += [reward]

    return lstSpendBlocks, lstTupTxidChans, rewards



def spendCb(fee, reward, objTx, outputs, cbSolver, dictIdToPub):
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
    chanIds = []
    for o in outputs:
        v = int(o.value)
        bPubN1 = dictIdToPub[str(o.node1.nodeid)]
        bPubN2 = dictIdToPub[str(o.node2.nodeid)]
        if bPubN1.compressed < bPubN2.compressed:  # lexicographical ordering
            multisig_script = MultisigScript(2, bPubN1, bPubN2, 2)
        else:
            multisig_script = MultisigScript(2, bPubN2, bPubN1, 2)
        p2wsh_multisig = P2wshV0Script(multisig_script)
        totVal += v
        outs += [TxOut(value=v,
                       n=0,
                       script_pubkey=p2wsh_multisig)]
        chanIds += [o.channelid]

    change = reward - totVal - fee
    outsWithChange = outs + [TxOut(value=change, n=0, script_pubkey=objTx.outs[0].script_pubkey)]
    unsignedCb = MutableTransaction(version=1,
                                        ins=[TxIn(txid=objTx.txid,
                                                  txout=0,
                                                  script_sig=ScriptSig.empty(),
                                                  sequence=Sequence.max())],
                                        outs=outsWithChange,
                                        locktime=Locktime(0)
                                        )
    cbTx = unsignedCb.spend([objTx.outs[0]], [cbSolver])
    return cbTx, (cbTx.txid, chanIds)



def setRealScids(config, objRpcB, txidToChan, chanidToChan, blockHashes):
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
            lstChanid = txidToChan[txid]
            for j in range(0, len(lstChanid)):
                chanid = lstChanid[j]
                chan = chanidToChan[chanid]
                chan.scid.tx = scidtxi
                chan.scid.height = height
                chan.scid.output = j

    return objRpcB


#init functions

def getNumBlocksToMine(chanBlocks):
    """
    get number blocks to mine to fund the channels including extra 100 to spend the blocks
    :param chanBlocks: the outputs of coinbase txs put in blocks
    :return: int
    """
    cbs = 0
    for block in chanBlocks:
        cbs += len(block)
    blocksToMine = cbs + 100
    return blocksToMine


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
    hundredBlockRounds = blocksToMine // 100
    remainder = blocksToMine % 100
    strBlockHashes = []
    for i in range(0, hundredBlockRounds):
        hashes, objRpcB = bitcoinCli(config, objRpcB, "generatetoaddress", 100, strAddrMiner)
        strBlockHashes += hashes
    if remainder != 0:
        hashes, objRpcB = bitcoinCli(config, objRpcB, "generatetoaddress", remainder, strAddrMiner)
        strBlockHashes += hashes

    return objRpcB, objPrivMiner, strAddrMiner, strBlockHashes[:-100]


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


def getCoinbaseTxids(config, objRpcB, hashesCb):
    """
    get txids of coinbase txs that are spendable
    :param config: config
    :param objRpcB: proxy object
    :return: lastest proxy object, str txids of spendable coinbases
    """
    xtxs = []
    for hashCb in hashesCb:
        r, objRpcB = bitcoinCli(config, objRpcB, "getblock", hashCb, 2)
        xtx = r["tx"][0]["hex"]
        xtxs += [xtx]

    return objRpcB, xtxs


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

