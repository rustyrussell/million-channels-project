import buildNetwork
import gossip
import argparse
import importlib.util
from common import graph, utility

def main():
    args = parse() 
    if args.config != None:
        spec = importlib.util.spec_from_file_location("config", args.config)
        config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config)
    else:
        import config

    config = overrideConfig(args, config)
    if args.build_only:
        network, targetNetwork, gossipSequence = buildNetwork.main(config)
    elif args.gossip_only:
        network = gossip.main(config)
    else:
        network, targetNetwork, gossipSequence = buildNetwork.main(config)
        network = gossip.main(config, network=network, gossipSequence=gossipSequence)

    if args.tests: #TODO move to new function
        for n in network.fullConnNodes:
            if n.maxChannels < n.channelCount:
                print("too many channels", n.nodeid)
            if not n.isInNetwork():
                print("not in network", n.nodeid)
    if args.draw:
        graph.igraphDraw(network.igraph)

    if args.analyze:
        print("power log: c*((x+b)^-a)")
        print("target network power log:", targetNetwork.analysis.powerLaw[0])
        network.analysis.analyze()
        
        print("new network power log:", network.analysis.powerLaw[0])
        print("new network betweenness:", network.analysis.betweenness())


def parse():
    parse = argparse.ArgumentParser()
    parse.add_argument("--build_only", action="store_const", const=True)
    parse.add_argument("--gossip_only", action="store_const", const=True)
    parse.add_argument("--draw", action="store_const", const=True)
    parse.add_argument("--gossip_store", action="store_const", const=True)
    parse.add_argument("--tests", action="store_const", const=True)
    parse.add_argument("--analyze", action="store_const", const=True)
    parse.add_argument("--config", type=str)
    parse.add_argument("--name", type=str, required=False)
    parse.add_argument("--channelNum", type=int)
    parse.add_argument("--maxChannelsPerNode", type=int)
    parse.add_argument("--defaultValue", type=int)
    parse.add_argument("--randSeed", type=int)
    parse.add_argument("--saveDir", type=str, required=False)
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
    if args.saveDir != None:
        config.saveDir = args.saveDir
    if args.name != None:
        config.name = args.name
        config.nodeSaveFile, config.channelSaveFile, config.gossipSaveFile = utility.getSaveFiles(config.saveDir, config.name)
    if args.channelNum != None:
        config.channelNum = args.channelNum
    if args.maxChannelsPerNode != None:
        config.maxChannelsPerNode = args.maxChannelsPerNode
    if args.gossip_store != None:
        config.gossip_store = args.gossip_store
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

    
    return config

main()



