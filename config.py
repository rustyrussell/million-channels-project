"""
TODO: MANY OF THESE FEILDS SHOULD EVENTUALLY BE CONFIGURABLE ON STARTUP
"""

###buildNetwork.py###
#can be changed by user:    ##MUST END IN BACKSLASH
networkName = ""  # ex "network_2-7-18"  <-- remember that all symbols must be able to be used in filenames and directories
finalNumChannels = 1000
randSeed = 1
channelFileName = "data/channels_1-18-18.json"
networkSaveFile = "data/" + networkName
backtracksPerCheckpoint = 1
candidateNumber = 3
channelsPerRound = 5
#cannot be changed by user:
attempts = candidateNumber**channelsPerRound


###power law reg.py###
#can be changed by user:
maxChannelsPerNode = 100000


###gossip.py###
#can be changed by user:    ##MUST END IN BACKSLASH
baseDataDir = ""      # ex "/home/jnetti/.lightning/"
experimentName = ""   # ex "experTwo" , "7" , etc
currExperimentDir = "experiments/"
lightningDir =  ""             # ex "/home/jnetti/lightning/c-lightning/"
bitcoinSrcDir =  ""             # ex "/home/jnetti/bitcoin/bitcoin/src/"
#cannot be changed by user:
lightningdDir = lightningDir + "lightningd/"
lightningCliDir = lightningDir + "cli/"
bitcoinCliPath = bitcoinSrcDir + "bitcoin-cli"




def checkBuildNetworkFields():
    if networkName == "":
        print("Fill networkName in config.py with network name for saving network in files and directories")
        return False
    return True

def checkGossipFields():
    if baseDataDir == "":
        print("Fill baseDataDir in config.py with the path to the lightning base dir (usually /home/<user>/.lightning")
        return False
    elif experimentName == "":
        print("Fill experimentName in config.py with the specific experiment name")
        return False
    elif lightningDir == "":
        print("Fill lightningdDir in config.py with the path to c-lightning directory. Example: /home/myUser/c-lightning/")
        return False
    elif bitcoinSrcDir == "":
        print("Fill bitcoinSrcDir in config.py with the path to bitcoin src directory of a bitcoin core implementation. Example: /home/myUser/bitcoin/src/")
        return False
    return True

def checkPowerLawFields():
    return True

def checkScrapeConnectedNodesFields():
    if lightningDir == "":
        print("Fill lightningdDir in config.py with the path to c-lightning directory. Example: /home/myUser/c-lightning/")
        return False
    return True