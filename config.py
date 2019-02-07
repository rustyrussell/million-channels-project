"""
TODO: MANY OF THESE FEILDS SHOULD EVENTUALLY BE CONFIGURABLE ON STARTUP
"""


baseDataDir = "/home/jnetti/.lightning/"
currExperimentDir = "experiments/1/"   # TODO add to config and cmd args in the future. Include a check to make sure that the experiment does not already exist

#buildNetwork
noiseProb = .2    #on average, 1 out of every 5 nodes should be random
randGenNoiseTrials = 10  # the first 10 nodes will use randint the rest will be swapped at an interval of 1 out of every 10
finalNumChannels = 1000 #1000000    # right now it is constant at 1,000,000. #TODO make this variable when the program gets more advanced
randSeed = 1                  #TODO make this variable when the program gets more advanced
channelFileName = "data/channels_1-18-18.json"
networkSaveFile = "data/network.data"
backtracksPerCheckpoint = 1
candidateNumber = 3
channelsPerRound = 5
attempts = candidateNumber**channelsPerRound


#power law reg
maxChannelsPerNode = 100000


#gossip
lightningdDir = "/home/jnetti/lightning/c-lightning/lightningd/"
bitcoinSrcDir = "/home/jnetti/bitcoin/bitcoin/src/"
bitcoinCliPath = bitcoinSrcDir + "bitcoin-cli"