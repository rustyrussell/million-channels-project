import os

"""
TODO: MANY OF THESE FEILDS SHOULD EVENTUALLY BE CONFIGURABLE ON STARTUP
"""

###buildNetwork.py###
#can be changed by user:    ##MUST END IN BACKSLASH
networkName = "1M"  # ex "network_2-7-18"  <-- remember that all symbols must be able to be used in filenames and directories
finalNumChannels = 2000000
randSeed = 2
channelFileName = "../data/channels_1-18-18.json"
channelSaveFile = "../data/" + networkName + ".channels"
nodeSaveFile = "../data/" + networkName + ".nodes"
gossipSaveFile = "../data/" + networkName + ".gossip"
maxChannelsPerNode = 100000
baseDataDir = ""
experimentName = ""   # ex "experTwo" , "7" , etc
currExperimentDir = ""
lightningDir =  ""


#cannot be changed by user:
lightningExpBaseDir = baseDataDir + currExperimentDir + experimentName
lightningCliDir = lightningDir + "cli/"



def checkBuildNetworkFields():
    if networkName == "":
        print("Fill networkName in config.py with network name for saving network in files and directories")
        return False
    return True

def checkGossipFields():
    if lightningDir == "":
        print("Fill lightningdDir in config.py with the path to c-lightning directory. Example: /home/myUser/c-lightning/")
        return False
    return True

def checkPowerLawFields():
    return True

def checkScrapeConnectedNodesFields():
    if lightningDir == "":
        print("Fill lightningdDir in config.py with the path to c-lightning directory. Example: /home/myUser/c-lightning/")
        return False
    return True

