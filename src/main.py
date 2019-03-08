import buildNetwork
import gossip
import argparse
import importlib.util

def main():
    args = parse() 
    if args.config != None:
        spec = importlib.util.spec_from_file_location("config", args.config)
        config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config)
    else:
        import config
    overrideConfig(args, config)
    if args.build:
        buildNetwork.main(config.channelNum, config.maxChannelsPerNode, config.analysisListChannelsFile, config.nodeSaveFile, config.channelSaveFile, config.randSeed)
    elif args.gossip:
        gossip.main(config.randSeed, config.gossipSaveFile, nodeSaveFile=config.nodeSaveFile, channelSaveFile=config.channelSaveFile)
    else:
        network, gossipSequence = buildNetwork.main(config.channelNum, config.maxChannelsPerNode, config.analysisListChannelsFile, config.nodeSaveFile, config.channelSaveFile, config.randSeed)
        gossip.main(config.randSeed, config.gossipSaveFile, network=network, gossipSequence=gossipSequence)

    
def parse():
    parse = argparse.ArgumentParser()
    parse.add_argument("--build", action="store_const", const=True)
    parse.add_argument("--gossip", action="store_const", const=True)   #program
    parse.add_argument("--config", type=str)
    parse.add_argument("--name", type=str, required=False)
    parse.add_argument("--channelNum", type=int)
    parse.add_argument("--maxChannelsPerNode", type=int)
    parse.add_argument("--randSeed", type=int)
    parse.add_argument("--analysisFile", type=str)
    parse.add_argument("--channelSaveFile", type=str)
    parse.add_argument("--nodeSaveFile", type=str)
    parse.add_argument("--gossipSaveFile", type=str)
    parse.add_argument("--lightningDataDir", type=str)
    args = parse.parse_args()
    return args


def overrideConfig(args, config):
    """
    using the args provided on cmdline, override those parts of the config
    """
    if args.name != None:
        config.name = args.name
    if args.channelNum != None:
        config.channelNum = args.channelNum
    if args.maxChannelsPerNode != None:
        config.maxChannelsPerNode = args.maxChannelsPerNode
    if args.randSeed != None:
        config.randSeed = args.randSeed
    if args.analysisFile != None:
        config.analysisFile = args.analysisFile
    if args.channelSaveFile != None:
        config.channelSaveFile = args.channelSaveFile
    if args.nodeSaveFile != None:
        config.nodeSaveFile = args.nodeSaveFile
    if args.gossipSaveFile != None:
        config.gossipSaveFile = args.gossipSaveFile
    if args.lightningDataDir != None:
        config.lightningDataDir = args.lightningDataDir
    

main()



