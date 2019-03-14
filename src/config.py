###buildNetwork.py###
# can be changed by user: directories MUST end in backslash
name = "1M"  # ex. "network_2-7-18"  <-- remember that all symbols must be able to be used in filenames and directories
channelNum = 1000000
maxChannelsPerNode = 100000
defaultValue = 10000
randSeed = 2
saveDir = "../data/"
processNum = 4
analysisFile = saveDir + "channels_1-18-18.json"
channelSaveFile = saveDir + name + "/" + name + ".channels"
nodeSaveFile = saveDir + name + "/" + name + ".nodes"
gossipSaveFile = saveDir + name + "/" + name + ".gossip"
lightningDataDir = ""
historicalData = "../data/historical_data.csv"

# cannot be changed by user:
lightningrpc = lightningDataDir + "lightning-rpc"


