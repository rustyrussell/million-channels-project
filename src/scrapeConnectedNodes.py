"""
this program scrapes and tries to connect to nodes from 1ml.com json or
from the output of lightning-cli listnodes command (one snapshot of each is provided in data folder).

c-lightning and a bitcoin server (bitcoind or spruned) must be running in order to run this program
the directory of c-lightning in os.chdir in function connect() will probably have to be changed to be able to find your cli
"""

import json
import os
import subprocess
import sys
from config import *

#classes

class JsonType:
    """
    Json types
    """
    def __init__(self, type_string):
        self.type = type_string

    def isCLightningType(self):
        return self.type == "clightning"

    def is1MLType(self):
        return self.type == "1ML"


#functions

def main():
    """
    Takes in 2 cmd args: filename and jtype. File must be stored in data directory. jType is either clightning or 1ML
    :return:
    """
    jType = sys.argv[1]
    filename = sys.argv[2]
    jType = JsonType(jType)
    connect(filename, jType)


def connect(filename, jType):
    """
    tries to connect to the nodes that are in the json format of the output of the c-lightning cli listnodes command
    :return: None
    """
    fp = open("../data/" + filename)
    nodeList = []
    if jType.isCLightningType():
        nodeList = scrapeNodesFromJsonCLightning(fp)

    elif jType.is1MLType():
        nodeList = scrapeNodesFromJson1ML(fp)
    os.chdir(lightningCliDir)
    for node in nodeList:
        try:
            subprocess.run(["./lightning-cli", "--lightning-dir="+lightningDataDir, "connect", node])
        except:  # TODO: horrible except statement because I don't know how to except specifically timeouts on the lightning-cli side
            pass


def scrapeNodesFromJson1ML(fp):
    """
    scrape from listnodes json
    :param fp: file
    :return: nodeList
    """
    jsonObj = json.load(fp)
    nodeList = []
    for i in range(0, len(jsonObj)):
        nodeString = jsonObj[i]['pub_key'] + "@" + jsonObj[i]['addresses'][0]['addr']
        nodeList += [nodeString]

    return nodeList 

def scrapeNodesFromJsonCLightning(fp):
    """
    scrape from 1ml json
    :param fp: file
    :return: Nodelist
    """
    jsonObj = json.load(fp)
    nodeList = []
    for i in range(0, len(jsonObj["nodes"])):
        try:
            nodeString = jsonObj["nodes"][i]['nodeid'] + "@" + jsonObj["nodes"][i]['addresses'][0]['address'] + ":" + str(jsonObj["nodes"][i]["addresses"][0]["port"])
            nodeList += [nodeString]
        except IndexError:
            pass
        except KeyError:
            pass

    return nodeList 


assert(checkScrapeConnectedNodesFields() == True)
if __name__ == "__main__":
    main()


