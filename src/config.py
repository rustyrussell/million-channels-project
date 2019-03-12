###buildNetwork.py###
# can be changed by user: directories MUST end in backslash
name = "1000"  # ex. "network_2-7-18"  <-- remember that all symbols must be able to be used in filenames and directories
channelNum = 1000
maxChannelsPerNode = 100000
defaultValue = 10000
randSeed = 2
analysisListChannelsFile = "../data/channels_1-18-18.json"
channelSaveFile = "../data/" + name + "/" + name + ".channels"
nodeSaveFile = "../data/" + name + "/" + name + ".nodes"
gossipSaveFile = "../data/" + name + "/" + name + ".gossip"
fullGossipStore = False
lightningDataDir = ""
historicalData = "../data/historical_data.csv"

# cannot be changed by user:
lightningrpc = lightningDataDir + "lightning-rpc"


