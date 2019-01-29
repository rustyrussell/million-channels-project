import bisect

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
        else:
            self.channelList = channels
            for channel in channels:
                self.value += channel.value
            self.channelCount = len(channels)
        self.nodeid = nodeid
        self.maxChannels = maxChannels

    def addChannel(self, channel):
        bisect.insort_left(self.channels, channel)
        self.value += channel.value
        self.channelCount += 1

    def setMaxChannels(self,num):
        self.maxChannels = num

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
    def __init__(self, party1, party2, json):
        self.party1 = party1
        self.party2 = party2
        self.json = json
        self.channelid = json["short_channel_id"]
        self.value = json["satoshis"]

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


