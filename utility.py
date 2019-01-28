
import bisect
import json
import networkClasses

# helper functions

def loadJson(fp):
    """
    helper function to load json
    :param fp: file object
    :return: json object
    """
    return json.load(fp)


def search(a, x):
    """
    The search helper function. Searches for a element in a list of objects. Objects MUST have __eq__
    :param a: list
    :param x: element
    :return: -1 for false, the element index for true
    """
    i = bisect.bisect_left(a, x)
    if i != len(a) and a[i].__eq__(x):
        return i
    return -1

def jsonToObject(jn):
    """
    Loads json that is from running the listchannels rpccommand and saving the output.
    Uses binary search and sorted lists for faster loading
    :param jn: json object
    :return: a sorted list of nodes, a sorted list of channels
    """
    channelsJson = jn["channels"]
    channels = []
    nodes = []
    for i in range(0, len(channelsJson)):
        #print("channel " + str(i))
        currChannel = channelsJson[i]
        nodeid1 = channelsJson[i]["source"]
        nodeid2 = channelsJson[i]["destination"]
        channelObj = networkClasses.Channel(None, None, currChannel)

        nodeObj1 = networkClasses.Node(nodeid1)
        nodeObj2 = networkClasses.Node(nodeid2)

        node1Exists = search(nodes, nodeObj1)
        if node1Exists != -1:
            nodeObj1 = nodes[node1Exists]
        else:
            bisect.insort_left(nodes, nodeObj1)

        node2Exists = search(nodes, nodeObj2)
        if node2Exists != -1:
            nodeObj2 = nodes[node2Exists]
        else:
            bisect.insort_left(nodes, nodeObj2)

        pair = False
        if node1Exists != -1 and node2Exists != -1:
            node1Channels = nodeObj1.channels
            channelExists = search(node1Channels, channelObj)
            if channelExists != -1:
                pair = True

        if pair == False:
            channelObj.setParty1(nodeObj1)
            channelObj.setParty2(nodeObj2)
            nodeObj1.addChannel(channelObj)
            nodeObj2.addChannel(channelObj)
            bisect.insort_left(channels, channelObj)

    return nodes, channels