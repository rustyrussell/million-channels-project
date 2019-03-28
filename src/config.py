# can be changed by user: directories MUST end in backslash. Use full path not ~/
build = False
gossip = False
chain = False
name = "1M"  # ex. "network_2-7-18"  <-- remember that all symbols must be able to be used in filenames and directories
channelNum = 1000000
maxChannels =  1000  # "default"  will base it off of a directly scaled snapshot of the network, but it will lead to very few nodes
maxFunding = "default" #pow(2,24)   
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
historicalData = "../data/historical_data.csv"
lightningDataDir = "/your/path/here"
bitcoinSrcDir = "/your/path/here"
bitcoinBaseDataDir = "/your/path/here"
bitcoinConfPath = "/your/path/here"
bitcoinDataDir = bitcoinBaseDataDir + name + "/"

# cannot be changed by user:
lightningrpc = lightningDataDir + "lightning-rpc"
coinbaseReward = 5000000000    #50 bitcoins
maxOutputsPerTx = 100
confirmations = 6
maxTxPerBlock = 1000 # 1000 transactions in a block plus coinbase (which is at index 0)
iCoinbasePriv = 100000000
bCoinbasePriv = bytearray(iCoinbasePriv.to_bytes(32, "big"))
