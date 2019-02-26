import bisect
import powerLawReg
from igraph import Graph
from common import utility
import igraph

#classes

class Node:
    """
    Node class
    """
    def __init__(self, nodeid, channels=None, maxChannels=None):
        self.setHasKeys(False)
        if channels == None:
            self.channels = []
            self.value = 0
            self.channelCount = 0
            self.neighbors = []
            self.neighborsDict = dict()
            self.realChannelCount = 0
            self.addrList = []
        else:
            self.channels = channels
            self.neighbors = []
            for channel in channels:
                self.value += channel.value
                p1 = channel.party1
                p2 = channel.party2
                if p1 != self:
                    if p1 not in self.neighbors:
                        self.neighbors += [p1]
                else:
                    if p2 not in self.neighbors:
                        self.neighbors += [p2]
            self.channelCount = len(channels)
        self.nodeid = nodeid
        self.maxChannels = maxChannels

    def setHasKeys(self, b):
        self.hasKeys = b

    def setNodeCPrivObj(self, cPrivObj):
        self.nodeCPrivObj = cPrivObj

    def setBitcoinCPrivObj(self, cPrivObj):
        self.bitcoinCPrivObj = cPrivObj

    def setNodeCompPub(self, compPub):
        self.nodeCompPub = compPub

    def setBitcoinCompPub(self, compPub):
        self.bitcoinCompPub = compPub

    def addChannel(self, channel):
        self.channelCount += 1
        self.value += channel.value

    def setMaxChannels(self,num):
        self.maxChannels = num

    def removeChannel(self, channel):
        self.channelCount -= 1
        self.value -= channel.value

    def addToRealChannelCount(self):
        self.realChannelCount += 1

    def setRPC(self, rpc):
        self.rpc = rpc

    def setId(self, id):
        self.id = id

    def addToAddrList(self, addr):
        self.addrList += [addr]

    def inNetwork(self):
        return len(self.channels) > 0

    def isFull(self):
        return self.channelCount >= self.maxChannels

    def setDataDir(self, dataDir):
        self.dataDir = dataDir

    def setpid(self):
        fp = open(self.dataDir + "lightningd-regtest.pid", "r")
        pid = ""
        for line in fp:
            pid = line
            break
        self.pid = pid

    def setIP(self, ip):
        self.ip = ip

    def __lt__(self, otherNode):
        return self.nodeid < otherNode.nodeid

    def __gt__(self, otherNode):
        return self.nodeid > otherNode.nodeid

    def __eq__(self, otherNode):
        return self.nodeid == otherNode.nodeid



class Channel:
    """
    Channel class
    """
    def __init__(self, node1, node2, json=None):
        self.node1 = node1
        self.node2 = node2
        self.json = json
        if json != None:
            self.channelid = json["short_channel_id"]
            self.value = json["satoshis"]
        else:
            self.value = 1
            self.channelid = str(self.node1.nodeid) + str(self.node2.nodeid)

    def setParty1(self, node1):
        self.node1 = node1

    def setParty2(self, node2):
        self.node2 = node2

    def __lt__(self, otherChannel):
        return self.channelid < otherChannel.channelid

    def __gt__(self, otherChannel):
        return self.channelid > otherChannel.channelid

    def __eq__(self, otherChannel):
        return self.channelid == otherChannel.channelid


class Chan:
    def __init__(self, channel):
        self.node1id = channel.node1.nodeid
        self.node2id = channel.node2.nodeid


class Network:
    """
    Network class contains nodes and analysis on the network.
    """
    def __init__(self, fullConnNodes):
        self.fullConnNodes = fullConnNodes
        self.channels = []
        self.igraph = self.makeiGraph(fullConnNodes)
        self.nodeNumber = len(fullConnNodes)
        self.analysis = Analysis(self)

    def addChannels(self,channels):
        self.channels += channels

    def makeiGraph(self, nodes):
        nodes.sort(key=utility.sortByNodeId)
        g = Graph(directed=False)
        for n in nodes:
            g.add_vertex(str(n.nodeid))
        # for c in self.channels:
        #     g.add_edge(c.node1.nodeid, c.node2.nodeid)
        return g

    def getConnNodes(self):
        return self.fullConnNodes

class IncompleteNetwork(Network):     # inherits Network class
    def __init__(self, fullConnNodes, disconnNodes, partConnNodes=None, unfullNodes=None, igraph=None):
        Network.__init__(self, fullConnNodes)
        self.disconnNodes = disconnNodes
        self.unfullNodes = disconnNodes
        if partConnNodes == None:
            self.partConnNodes = []
            self.nodeNumber = len(fullConnNodes) + len(disconnNodes)
        else:
            self.partConnNodes = partConnNodes
            self.unfullNodes = self.unfullNodes + partConnNodes
            self.nodeNumber = len(fullConnNodes) + len(disconnNodes) + len(partConnNodes)
        if unfullNodes != None:
            self.unfullNodes = unfullNodes

        if igraph != None:
            self.igraph = igraph
        else:
            if partConnNodes != None:
                self.igraph = self.makeiGraph(fullConnNodes + partConnNodes)
            else:
                self.igraph = self.makeiGraph(fullConnNodes)

    def getConnNodes(self):
        return self.fullConnNodes + self.partConnNodes

    def createNewChannel(self, node1, node2):
        """
        creates channel between node1 and node2. NOTE: this does not check if adding this channel breaks the maximum
        :param node1: node obj
        :param node2: node obj
        :return: channel
        """
        channel = Channel(node1, node2)
        node1.addChannel(channel)
        node2.addChannel(channel)

        return channel

    def removeChannel(self, channel):
        """
           deletes channel
           :param channel: channel
           :return:
           """
        node1 = channel.node1
        node2 = channel.node2
        node1.removeChannel(channel)
        node2.removeChannel(channel)


class Analysis:
    """
    Analysis on the network are the power law and cluster experiments
    """
    def __init__(self, network):
        self.network = network

    def analyze(self):
        params, covariance, x, yProb = powerLawReg.powerLawExperiment(self.network.getConnNodes(), graph=False, completeNetwork=True)   #only fully connected nodes get analyzed
        self.powerLaw = (params, covariance, x, yProb)
        # avgCluster, clusterDict, freqx, clustery, params, covariance = powerLawReg.cluster(self.network.fullConnNodes, graph=False, completeNetwork=True, bounds=(0, 1000, 1))
        # self.cluster = (clusterDict, freqx, clustery, params, covariance)

    def betweenness(self):
        igraph = self.network.igraph
        bs = igraph.betweenness()
        s = sum(bs)
        avg = s/len(bs)
        return avg


class ChannelGenParams:
    """
    The parameters that help create an accurate network
    """
    def __init__(self, newNetwork, targetNetwork):
        self.targetNetwork = targetNetwork
        self.newNetwork = newNetwork




