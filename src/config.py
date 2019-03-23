###buildNetwork.py###
# can be changed by user: directories MUST end in backslash
build = False
gossip = False
chain = False
name = "1M"  # ex. "network_2-7-18"  <-- remember that all symbols must be able to be used in filenames and directories
channelNum = 1000000
maxChannels =  1000  # "default"  will base it off of the snapshot of the network, but may lead to very few nodes
maxFunding = "default" #pow(2,24)   #limit to number of sats in a channel
defaultValue = 10000
fee = 1000
randSeed = 2
saveDir = "../data/"
processNum = 4
listchannelsFile = saveDir + "channels_1-18-18.json"
listnodesFile = saveDir + "nodes_1-18-18.json"
channelSaveFile = saveDir + name + "/" + name + ".channels"
scidSatoshisFile = saveDir + name + "/" + "scidSatoshis" + ".csv"
nodesFile = saveDir + name + "/" + name + ".nodes"
gossipFile = saveDir + name + "/" + name + ".gossip"
lightningDataDir = ""
historicalData = "../data/historical_data.csv"
bitcoinSrcDir = "/your/path/here"
bitcoinDataDir = "/your/path/here"
bitcoinConf = "regtest.conf"

# cannot be changed by user:
lightningrpc = lightningDataDir + "lightning-rpc"
coinbaseReward = 5000000000
maxOutputsPerTx = 10
confirmations = 6
maxFundingTxPerBlock = 1001 # 1000 transactions in a block plus coinbase (which is at index 0)
iCoinbasePriv = 100000000
bCoinbasePriv = bytearray(iCoinbasePriv.to_bytes(32, "big"))
