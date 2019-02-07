import bisect
import powerLawReg
from igraph import Graph
import utility

#classes

class Node:
    """
    Node class
    """
    def __init__(self, nodeid, channels=None, maxChannels=None):
        if channels == None:
            self.channels = []
            self.value = 0
            self.channelCount = 0
            self.neighbors = []
            self.neighborsDict = dict()
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

    def addChannel(self, channel):
        bisect.insort_left(self.channels, channel)
        self.value += channel.value
        self.channelCount += 1
        p1 = channel.node1
        p2 = channel.node2
        if p1.nodeid == self.nodeid:
            if p1.nodeid not in self.neighborsDict:
                self.neighbors += [p2]
                self.neighborsDict[p2.nodeid] = 1
            else:
                self.neighborsDict[p2.nodeid] += 1
        else:
            if p1.nodeid not in self.neighborsDict:
                self.neighbors += [p1]
                self.neighborsDict[p1.nodeid] = 1
            else:
                self.neighborsDict[p1.nodeid] += 1


    def setMaxChannels(self,num):
        self.maxChannels = num

    def removeChannel(self, channel):
        self.channelCount -= 1
        self.channels.remove(channel)
        self.value -= channel.value
        p1 = channel.node1
        p2 = channel.node2
        if p1.nodeid == self.nodeid:
            if p2.nodeid in self.neighborsDict:
                cs = self.neighborsDict[p2.nodeid]
                if cs == 1:
                    self.neighborsDict.pop(p2.nodeid)
                    self.neighbors.remove(p2)
                else:
                    self.neighborsDict[p2.nodeid] -= 1
        else:
            if p1.nodeid in self.neighborsDict:
                cs = self.neighborsDict[p1.nodeid]
                if cs == 1:
                    self.neighborsDict.pop(p1.nodeid)
                    self.neighbors.remove(p1)
                else:
                    self.neighborsDict[p1.nodeid] -= 1




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



class Network:
    """
    Network class contains nodes and analysis on the network.
    """
    def __init__(self, fullConnNodes, analysis):
        self.fullConnNodes = fullConnNodes
        self.channels = []
        self.igraph = self.makeiGraph(fullConnNodes)
        self.nodeNumber = len(fullConnNodes)
        if analysis == True:
            self.analysis = Analysis(self)
        elif analysis == False:
            self.analysis = None
        else:
            self.analysis = analysis

    def addChannels(self,channels):
        self.channels += channels

    def makeiGraph(self, nodes):
        nodes.sort(key=utility.sortByNodeId)
        g = Graph()
        g.add_vertices(len(nodes))
        # for c in self.channels:
        #     g.add_edge(c.node1.nodeid, c.node2.nodeid)
        return g
    def setBaseDataDir(self, dir):
        self.baseDataDir = dir


class IncompleteNetwork(Network):     # inherits Network class
    def __init__(self, fullConnNodes, disconnNodes, partConnNodes=None, unfullNodes=None, igraph=None):
        Network.__init__(self, fullConnNodes, False)
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
                self.igraph = self.makeiGraph(fullConnNodes + disconnNodes + partConnNodes)
            else:
                self.igraph = self.makeiGraph(fullConnNodes + disconnNodes)

    def createNewChannel(self, node1, node2):
        """
        creates channel between node1 and node2. NOTE: this does not check if adding this channel breaks the maximum
        :param node1: node obj
        :param node2: node obj
        :return: channel
        """
        if node1.channelCount == 0:    # if disconnected
            self.disconnNodes.remove(node1)
            if node1.maxChannels == 1:
                self.fullConnNodes += [node1]
                self.unfullNodes.remove(node1)
            else:
                self.partConnNodes += [node1]
        else:
            if node1.channelCount == node1.maxChannels - 1:
                self.fullConnNodes += [node1]
                self.partConnNodes.remove(node1)
                self.unfullNodes.remove(node1)
            else:
                pass    #it stays in partConnNodes
        if node2.channelCount == 0:  # if disconnected
            self.disconnNodes.remove(node2)
            if node2.maxChannels == 1:
                self.fullConnNodes += [node2]
                self.unfullNodes.remove(node2)
            else:
                self.partConnNodes += [node2]
        else:
            if node2.channelCount == node2.maxChannels - 1:
                self.fullConnNodes += [node2]
                self.partConnNodes.remove(node2)
                self.unfullNodes.remove(node2)
            else:
                pass  # it stays in partConnNodes


        channel = Channel(node1, node2)
        node1.addChannel(channel)
        node2.addChannel(channel)
        self.igraph.add_edge(node1.nodeid, node2.nodeid)

        return channel

    def removeChannel(self, channel):
        """
        deletes channel
        :param channel: channel
        :return:
        """
        node1 = channel.node1
        node2 = channel.node2
        if node1.maxChannels == 1:   # if full
            self.fullConnNodes.remove(node1)
            self.disconnNodes += [node1]
            self.unfullNodes += [node1]
        elif node1.isFull():
            self.fullConnNodes.remove(node1)
            self.partConnNodes += [node1]
            self.unfullNodes += [node1]
        elif node1.channelCount == 1: # partial but will be disconnected
            self.partConnNodes.remove(node1)
            self.disconnNodes += [node1]
        if node2.maxChannels == 1:   # if full
            try:
                self.fullConnNodes.remove(node2)
            except:
                print("error")
            self.disconnNodes += [node2]
            self.unfullNodes += [node2]
        elif node2.isFull():
            self.fullConnNodes.remove(node2)
            self.partConnNodes += [node2]
            self.unfullNodes += [node2]
        elif node2.channelCount == 1: # partial but will be disconnected
            self.partConnNodes.remove(node2)
            self.disconnNodes += [node2]
        node1.removeChannel(channel)
        node2.removeChannel(channel)
        self.igraph.delete_edges([(node1.nodeid, node2.nodeid)])


    def pushUnfull(self, node):
        self.unfullNodes.insert(0, node)

    def popUnfull(self):
        n = self.unfullNodes[-1]
        self.unfullNodes = self.unfullNodes[0:-1]
        return n




class Analysis:
    """
    Analysis on the network are the power law and cluster experiments
    """
    def __init__(self, network):
        self.network = network
        network.analysis = self.analyze()

    def analyze(self):
        params, covariance, x, yProb = powerLawReg.powerLawExperiment(self.network.fullConnNodes, graph=False, completeNetwork=True)   #only fully connected nodes get analyzed
        self.powerLaw = (params, covariance, x, yProb)
        # avgCluster, clusterDict, freqx, clustery, params, covariance = powerLawReg.cluster(self.network.fullConnNodes, graph=False, completeNetwork=True, bounds=(0, 1000, 1))
        # self.cluster = (clusterDict, freqx, clustery, params, covariance)


class ChannelGenParams:
    """
    The parameters that help create an accurate network
    """
    def __init__(self, newNetwork, targetNetwork):
        self.targetNetwork = targetNetwork
        self.newNetwork = newNetwork




