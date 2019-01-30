import bisect
import powerLawReg

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
        else:
            self.channelList = channels
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
        p1 = channel.party1
        p2 = channel.party2
        if p1 != self:
            if p1 not in self.neighbors:
                self.neighbors += [p1]
        else:
            if p2 not in self.neighbors:
                self.neighbors += [p2]

    def setMaxChannels(self,num):
        self.maxChannels = num

    def removeChannel(self, channel):
        self.channelCount -= 1
        self.channels.remove(channel)
        self.value -= channel.value

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
    def __init__(self, party1, party2, json=None):
        self.party1 = party1
        self.party2 = party2
        self.json = json
        if json != None:
            self.channelid = json["short_channel_id"]
            self.value = json["satoshis"]
        else:
            self.value = 1
            self.channelid = str(self.party1.nodeid) + str(self.party2.nodeid)

    def setParty1(self, party1):
        self.party1 = party1

    def setParty2(self, party2):
        self.party2 = party2

    def __lt__(self, otherChannel):
        return self.channelid < otherChannel.channelid

    def __gt__(self, otherChannel):
        return self.channelid > otherChannel.channelid

    def __eq__(self, otherChannel):
        return self.channelid == otherChannel.channelid


class ChannelGenParams:
    """
    The parameters that help create an accurate network
    """
    def __init__(self):
        pass


class NetworkAnalysis:
    def __init__(self, nodes):
        self.nodes = nodes

    def analyze(self):
        params, covariance, x, yProb = powerLawReg.powerLawExperiment(self.nodes, graph=False, completeNetwork=True)
        self.powerLaw = (params, covariance, x, yProb)

