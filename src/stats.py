from common import utility
from config import *

network, gs = utility.loadNetwork(nodeSaveFile, channelSaveFile)
print(len(network.channels))
print(len(network.getNodes()))


