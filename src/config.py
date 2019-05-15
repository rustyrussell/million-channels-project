# can be changed by user: directories MUST end in backslash. Use full path not ~/
build = False
gossip = False
chain = False
writeNodes = True
gossipStore = False
name = "1M"  # ex. "network_2-7-18"  <-- remember that all symbols must be able to be used in filenames and directories
channelNum = 1000000
maxChannels =  10000  # "default"  will base it off of a directly scaled snapshot of the network, but it will lead to very few nodes
maxFunding = 100000000 #"default" will base it off scaled max capacity node 
fee = 50000
randSeed = 2
addrTypes = "all"
processNum = 4
saveDir = "../data/"
listchannelsFile = saveDir + "channels_1-14-19.json"
listnodesFile = saveDir + "nodes_1-14-19.json"
bitcoinSrcDir = "/your/full/path/"
bitcoinBaseDataDir = "/your/full/path/"
bitcoinConfPath = "/your/full/path/"


#if the user doesn't change below, it will save in million-channels-project/data/name/...
nodesFile = saveDir + name + "/" + name + ".nodes"
channelsFile = saveDir + name + "/" + name + ".channels"
gossipFile = saveDir + name + "/" + name + ".gossip"
scidSatoshisFile = saveDir + name + "/" + "scidSatoshis" + ".csv"
bitcoinDataDir = bitcoinBaseDataDir + name + "/" 
