import buildNetwork
import gossip
import chain
import argparse
import importlib.util
from bitcoin import SelectParams
from common import graph, utility
from os import path, mkdir
import time


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

    if not config.chain and not config.gossip and not config.build and not args.tests and not args.analyze:
        raise ValueError(
            "Use --build, --chain, --gossip, --analyze, --tests in cmd line to specify what actions to perform, (or set them to True in the config.py)")

    init(config)

    if args.analyze or config.build:
        if args.analyze:
            graph = True
        else:
            graph = False
        targetNetwork = buildNetwork.initTargetNetwork(config, graph)
    if config.build:
        t0 = time.time()
        network, targetNetwork, gossipSequence = buildNetwork.buildNetwork(config, targetNetwork)
        t1 = time.time()
        print("build network complete in", t1-t0)
        network.printNetworkStats()
        if args.analyze:
            print("power log: c*((x+b)^-a)")
            print("target network channel prob. dist. power law:", targetNetwork.analysis.channelDistPowLawParams[0])
            print("target network node capacity prob. dist. power law:", targetNetwork.analysis.nodeCapacityInNetPowLawParams[0])
            print("target network channel capacity in node", targetNetwork.analysis.channelCapacityInNodeParams[1][0])
            print("target network linear params:", targetNetwork.analysis.channelCapacityInNodeParams[0][0])
            network.analysis.analyze(True)
            print("new network power law:", network.analysis.channelDistPowLawParams[0])
            print("new network node capacity prob. dist. power law:", network.analysis.nodeCapacityInNetPowLawParams[0])
            print("new network channel capacity in node", network.analysis.channelCapacityInNodeParams[1][0])
            print("new network linear params:", network.analysis.channelCapacityInNodeParams[0][0])
    else:
        network, gossipSequence = utility.loadNetwork(config.nodesFile, config.channelsFile)
    if args.draw:
        graph.igraphDraw(network.igraph)
    if config.chain:
        t0 = time.time()
        try: 
            network = chain.buildChain(config, network)
        finally:
            chain.killBitcoind()
        t1 = time.time()
        print("build chain complete in", t1-t0)

    if config.chain or config.build:
        utility.writeNetwork(network, gossipSequence, config.nodesFile, config.channelsFile)
    if config.gossip:
        t0 = time.time()
        network = gossip.gossip(config, network, gossipSequence)
        t1 = time.time()
        print("gossip complete in", t1-t0)

    if args.tests: #TODO move tests to new function
        channelSum = 0
        maxChannelSum = 0
        for n in network.getNodes():
            if n.maxChannels < n.channelCount:
                print("too many channels", n.nodeid)
            if not n.isInNetwork():
                print("not in network", n.nodeid)
            channelSum += n.channelCount
            maxChannelSum += n.maxChannels
            if config.build:
                for c in n.channels:
                    if c.value is None:
                        print("in node:", "scid", c.scid, "of node1", c.node1, "node2", c.node2, "has None value")
        if channelSum != len(network.channels):
            print("# of channels in list:", len(network.channels), "# of channels in nodes", channelSum//2)
        for c in network.channels:
            if c.value is None:
                print("in channel list: scid", c.scid, "of node1", c.node1, "node2", c.node2, "has None value")
        print("# of max channels", maxChannelSum//2)

def parse():
    parse = argparse.ArgumentParser()
    parse.add_argument("--build", action="store_const", const=True)
    parse.add_argument("--gossip", action="store_const", const=True)
    parse.add_argument("--chain", action="store_const", const=True)
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
    parse.add_argument("--bitcoindPath", type=str)
    parse.add_argument("--bitcoinDataDir", type=str)

    args = parse.parse_args()
    return args


def overrideConfig(args, config):
    """
    using the args provided on cmdline, override those parts of the config
    """
    if args.build:
        config.build = True
    if args.gossip:
        config.gossip = True
    if args.chain:
        config.chain = True
    if args.saveDir != None:
        config.saveDir = args.saveDir
    if args.name != None:
        config.name = args.name
        config.nodesFile, config.channelsFile, config.gossipFile, config.scidSatoshisFile, config.bitcoinDataDir = utility.getSaveFiles(config.saveDir, config.bitcoinBaseDataDir, config.name)
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
    if args.bitcoindPath != None:
        config.bitcoindPath = args.bitcoindPath
    if args.bitcoinDataDir != None:
        config.bitcoinDataDir = args.bitcoinDataDir

    return config


def init(config):
    SelectParams("regtest")
    utility.setRandSeed(config.randSeed)


main()



