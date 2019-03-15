from analysis import powerLawReg
from igraph import Graph
from common import utility
from analysis import fundingReg

#classes

class Node:
    """
    Node class
    """
    def __init__(self, nodeid, inNetwork=False, maxChannels=None):
        self.setHasKeys(False)
        self.value = 0
        self.channelCount = 0
        self.addrList = []
        self.nodeid = nodeid
        self.maxChannels = maxChannels
        self.channels = []
        self.inNetwork = inNetwork
        self.setAnnounce(False)
        self.addrType = None
        self.value = 0

    def setHasKeys(self, b):
        """
        if true, all keys are generated and saved. Otherwise, False
        :param: b: true
        """
        self.hasKeys = b

    def setNodeCPrivObj(self, cPrivObj):
        self.nodeCPrivObj = cPrivObj

    def setBitcoinCPrivObj(self, cPrivObj):
        self.bitcoinCPrivObj = cPrivObj

    def setNodeCompPub(self, compPub):
        self.nodeCompPub = compPub

    def setBitcoinCompPub(self, compPub):
        self.bitcoinCompPub = compPub

    def addValue(self, value):
        self.value += value

    def addChannel(self, channel):
        self.channelCount += 1

    def setMaxChannels(self,num):
        self.maxChannels = num

    def removeChannel(self, channel):
        self.channelCount -= 1

    def isInNetwork(self):
        return self.inNetwork

    def setAnnounce(self, b):
        self.announce = b

    def setAddrType(self, addrType): #None means no address
        self.addrType = addrType

    def setInNetwork(self, inNetwork):
        self.inNetwork = inNetwork

    def isFull(self):
        return self.channelCount >= self.maxChannels

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
    def __init__(self, node1, node2, value=None, scid=None, json=None):
        self.node1 = node1
        self.node2 = node2
        self.json = json
        self.scid = scid
        self.value = value #NOTE: value is None when it is not set yet
        self.setN1ToWrite(False)
        self.setN2ToWrite(False)
        if json != None:
            self.channelid = json["short_channel_id"]
            self.value = json["satoshis"]
        else:
            self.channelid = str(self.node1.nodeid) + str(self.node2.nodeid)

    def setNode1(self, node1):
        self.node1 = node1

    def setNode2(self, node2):
        self.node2 = node2

    def setScid(self, scid):
        self.scid = scid

    def setN1ToWrite(self, n1Write):
        self.n1Write = n1Write

    def setN2ToWrite(self, n2Write):
        self.n2Write = n2Write

    def __lt__(self, otherChannel):
        return self.channelid < otherChannel.channelid

    def __gt__(self, otherChannel):
        return self.channelid > otherChannel.channelid

    def __eq__(self, otherChannel):
        return self.channelid == otherChannel.channelid


class Chan:
    """
    Light-weight channel object that is pickled 
    """
    def __init__(self, channel):
        self.node1id = channel.node1.nodeid
        self.node2id = channel.node2.nodeid
        self.scid = channel.scid


class Network:
    """
    Network class contains nodes and analysis on the network.
    """

    def __init__(self, fullConnNodes, channels=None):
        """
        Create a network where the nodes do not have the channels passed in
        :param fullConnNodes:
        :param channels:
        """
        self.fullConnNodes = fullConnNodes
        self.nodeNumber = len(fullConnNodes)
        self.analysis = Analysis(self)
        if channels is not None:
            self.channels = channels
        else:
            self.channels = []
        self.makeiGraph()

    def addChannels(self, channels):
        self.channels += channels

    def makeiGraph(self):
        if self.fullConnNodes != None:
            self.fullConnNodes.sort(key=utility.sortByNodeId)
            g = Graph(directed=False)
            g.add_vertices(len(self.fullConnNodes))
            es = []
            for ch in self.channels:
                es += [(ch.node1.nodeid, ch.node2.nodeid)]
            if es != []:
                g.add_edges(es)
            self.igraph = g

    def getConnNodes(self):
        return self.fullConnNodes

    def getNodeNum(self):
        return len(self.getNodes())

    def getNodes(self):
        return self.fullConnNodes

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
        self.channels += [channel]

        return channel

    def removeChannel(self, channel):
        """
           deletes channel
           :param channel: channel
           """
        node1 = channel.node1
        node2 = channel.node2
        node1.removeChannel(channel)
        node2.removeChannel(channel)

class IncompleteNetwork(Network):     # inherits Network class
    """
    Incomplete network that inherits Network. This is used when the network is being built. 
    """
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

    def getConnNodes(self):
        """
        returns connected nodes
        overides getConnNodes in Network class
        :return: connected nodes 
        """
        return self.fullConnNodes + self.partConnNodes

    def getNodeNum(self):
        return len(self.getNodes())

    def getNodes(self):
        return self.fullConnNodes + self.partConnNodes + self.disconnNodes


class Analysis:
    """
    Analysis on the network are the power law and cluster experiments
    """
    def __init__(self, network):
        self.network = network

    def analyze(self):
        params, covariance, x, yProb = powerLawReg.powerLawExperiment(self.network.getConnNodes(), graph=False, completeNetwork=True)   #only fully connected nodes get analyzed
        self.powerLaw = (params, covariance, x, yProb)
        params2, covariance2 = fundingReg.fundingRegExperiment(self.network.getNodes(), self.network.channels)
        self.fundingReg = (params2, covariance2)

    def betweenness(self):
        """
        calculate average betweenness of all verticies in graph
        """
        igraph = self.network.igraph
        bs = igraph.betweenness()
        s = sum(bs)
        avg = s/len(bs)
        return avg



