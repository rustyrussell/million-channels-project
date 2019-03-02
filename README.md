# million-channels-project
The goal of this project is to create a large test network (>1M channels) with an accurate topology extrapolated from the current topology. 
This network will be used for testing routing algorithms and channel syncing.

### Instructions on how to run without regenerating the network:

    1. A sample of the gossip produced can be found in data/1M/1M.gossip. 
        This file is split into smaller files. To combine files run:
        `cd data/1M/gossip/
        cat xa* > ../1M.gossip`

    2. rename 1M.gossip to gossip_store and copy it into .lightning directory that you are working in. 

    3. You MUST use this fork of c-lightning: https://github.com/nettijoe96/lightning 
        Compile with:
        `./configure --enable-MCP`

    4. Run clightning, point it to the right .lightning directory, and watch it load gossip. 
        `./lightning-cli listchannels` should return ~1M channels  

The project has several seperate programs can be used to create a new network:

1. buildNetwork.py: Applies a scaling factor to make a similar network on regtest
    1. To get your own node data to feed into buildNetwork, run:
     `./lightning-cli listchannels` on a highly connected node. You can use scrapeConnectedNodes.py to help make your node highly connected

2. gossip.py: Generates all the gossip generated by that network.
    1. To run this without running buildNetwork, you can use the .nodes files and .channels files as the nodeSaveFile and channelSaveFile located in config.py. 

3. scrapeConnectedNodes.py: Connects to nodes in lightning network that are scraped from node files


