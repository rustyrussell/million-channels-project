import os

###buildNetwork.py###
# can be changed by user: directories MUST end in backslash
networkName = "1M"  # ex. "network_2-7-18"  <-- remember that all symbols must be able to be used in filenames and directories
finalNumChannels = 1000000
randSeed = 2
channelFileName = "../data/channels_1-18-18.json"
channelSaveFile = "../data/" + networkName + "/" + networkName + ".channels"
nodeSaveFile = "../data/" + networkName + "/" + networkName + ".nodes"
gossipSaveFile = "../data/" + networkName + "/" + networkName + ".gossip"
maxChannelsPerNode = 100000
lightningDataDir = "/home/jnetti/.lightning/experiments/testNodes/7/"
lightningSourceDir =  ""


# cannot be changed by user:
lightningrpc = lightningDataDir + "lightning-rpc"
lightningCliDir = lightningSourceDir + "cli/"
channelsToCreate = 2 * finalNumChannels



def checkBuildNetworkFields():
    if networkName == "":
        print("Fill networkName in config.py with network name for saving network in files and directories")
        return False
    return True

def checkGossipFields():
    if networkName == "":
        print("Fill networkName in config.py with network name for saving network in files and directories")
        return False
    return True

def checkPowerLawFields():
    return True

def checkScrapeConnectedNodesFields():
    if lightningSourceDir == "":
        print("Fill lightningdDir in config.py with the path to c-lightning directory. Example: /home/myUser/c-lightning/")
        return False
    return True

