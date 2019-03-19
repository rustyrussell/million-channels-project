import buildNetwork
import gossip
import argparse
import importlib.util
from common import graph, utility
from os import path, mkdir

def main():
    args = parse() 
    if args.config != None:
        spec = importlib.util.spec_from_file_location("config", args.config)
        config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config)
    else:
        import config

    config = overrideConfig(args, config)
    dir = config.saveDir + config.name + "/"
    if not path.exists(dir):
        mkdir(dir)
    if args.build_only:
        network, targetNetwork, gossipSequence = buildNetwork.buildNetwork(config)
    elif args.gossip_only:
        network = gossip.main(config)
    else:
        network, targetNetwork, gossipSequence = buildNetwork.buildNetwork(config)
        network = gossip.main(config, network=network, gossipSequence=gossipSequence)

    if args.tests: #TODO move tests to new function
        for n in network.fullConnNodes:
            if n.maxChannels < n.channelCount:
                print("too many channels", n.nodeid)
            if not n.isInNetwork():
                print("not in network", n.nodeid)
    if args.draw:
        graph.igraphDraw(network.igraph)

    if args.analyze:
        print("power log: c*((x+b)^-a)")
        print("target network power law:", targetNetwork.analysis.channelDistPowLawParams[0])
        network.analysis.channelDistPowLaw()
        print("new network power law:", network.analysis.channelDistPowLawParams[0])


def parse():
    parse = argparse.ArgumentParser()
    parse.add_argument("--build_only", action="store_const", const=True)
    parse.add_argument("--gossip_only", action="store_const", const=True)
    parse.add_argument("--draw", action="store_const", const=True)
    parse.add_argument("--tests", action="store_const", const=True)
    parse.add_argument("--analyze", action="store_const", const=True)
    parse.add_argument("--config", type=str)
    parse.add_argument("--name", type=str, required=False)
    parse.add_argument("--channels", type=int)
    parse.add_argument("-p", type=int)
    parse.add_argument("--maxChannels", type=int)
    parse.add_argument("--maxFunding", type=int)
    parse.add_argument("--defaultValue", type=int)
    parse.add_argument("--randSeed", type=int)
    parse.add_argument("--saveDir", type=str, required=False)
    parse.add_argument("--listchannelsFile", type=str)
    parse.add_argument("--listnodesFile", type=str)
    parse.add_argument("--channelFile", type=str)
    parse.add_argument("--scidSatoshisFile", type=str)
    parse.add_argument("--nodeFile", type=str)
    parse.add_argument("--gossipFile", type=str)
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
        config.nodeFile, config.channelFile, config.gossipFile, config.scidSatoshisFile = utility.getSaveFiles(config.saveDir, config.name)
    if args.channels != None:
        config.channelNum = args.channels
    if args.p != None:
        config.processNum = args.p
    if args.maxChannels != None:
        config.maxChannels = args.maxChannels
    if args.maxFunding != None:
        config.maxFunding = args.maxFunding
    if args.randSeed != None:
        config.randSeed = args.randSeed
    if args.listchannelsFile != None:
        config.listchannelsFile = args.listchannelsFile
    if args.channelFile != None:
        config.channelFile = args.channelFile
    if args.scidSatoshisFile != None:
        config.scidSatoshisFile = args.scidSatoshisFile
    if args.nodeFile != None:
        config.nodeFile = args.nodeFile
    if args.gossipFile != None:
        config.gossipFile = args.gossipFile
    if args.lightningDataDir != None:
        config.lightningDataDir = args.lightningDataDir

    
    return config

main()



