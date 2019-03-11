# million-channels-project
The goal of this project is to create a large test network (>1M channels) with an accurate topology extrapolated from the current topology. 
This network will be used for testing routing algorithms and channel syncing.

### Instructions on how to run without regenerating the network:

1. A sample of the gossip produced can be found in data/1M/1M.gossip. 
   This file is split into smaller files. To combine files run:
       `cd data/1M/gossip/`
       `xz -d xa*`
       `cat xa* > ../1M.gossip`

2. rename 1M.gossip to gossip_store and copy it into .lightning directory that you are working in. 

3. You MUST use this fork of c-lightning: https://github.com/nettijoe96/lightning 
    Compile with:
    `./configure --enable-MCP`

4. Run clightning, point it to the right .lightning directory, and watch it load gossip. 
    `./lightning-cli listchannels` should return ~1M channels  

### Generating network or gossip from scratch

1. main.py can create the network and/or the gossip messages. 
   Running main.py with --build_only only builds and saves the network. 
   Running main.py with --gossip_only only generates gossip. 
   Running without either --build_only or --gossip_only does both.

2. building the network consists of analyzing a provided network and scaling it up. 
   Therefore, you need your own network data and set analysisListChannelsFile 
   You can use data provided in data/channels_1-18-18.json.zx (make sure you unzip)
   To get your own network data to feed into main.py for building the network, run:
   `./lightning-cli listchannels` on a highly connected node. 
   You can use scrapeConnectedNodes.py to help make your node highly connected

3. To run without building network, you can use the .nodes files and .channels files 
   provided in /data as the nodeSaveFile and channelSaveFile located in config.py 
   or as cmdline args (ex. --nodeSaveFile /path/to/file). 
       For 1M network, do the following:
       `cd data/1M/nodes/`
       `xz -d xa*`
       `cat xa* > ../1M.nodes`
       `cd data/1M/channels/`
       `xz -d xa*`
       `cat xa* > ../1M.channels`
    
3. scrapeConnectedNodes.py: Connects to nodes in lightning network that are scraped from node files


