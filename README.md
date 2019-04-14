# million-channels-project
The goal of this project is to create a large test network (>1M channels) with an accurate topology extrapolated from the current topology. 
This network will be used for testing routing algorithms and channel syncing.

### Instructions on how to run without regenerating the network:

1. Download 1M gossip and regtest chain: https://drive.google.com/drive/folders/10uda9L7EtwctCAoU9EzH3PnKMs7tx7Fd?usp=sharing 

2. A sample of the gossip produced can be found in data/1M/1M.gossip. 
   This file is split into smaller files. To combine files run:

       `tar xfJ data.tar.xz`

       `mv bitcoin ~\.bitcoin\1M` 

3. Clone this fork and switch to guilt/store-load-optimize branch

       `git clone https://github.com/rustyrussell/lightning.git`
       
       `cd lightning`
       
       `git checkout guilt/store-load-optimize`
       
       `./configure --enable-developer && make`

       `cd devtools`
       
       `./create-gossipstore --verbose 100000 -i /path/to/gossip -o ~/path/to/.lightning-datadir`

4. Set fields in config.py that are currently set to /your/path/here (or pass in cmdline args to set them)

5. Run clightning, point it to the right .lightning directory, and watch it load gossip. 
    `./lightning-cli listchannels` <-- should return ~1M channels  

### Generating network or gossip from scratch

1. main.py can create the network, regtest chain, or the gossip messages. 
   Running main.py with --build  builds and saves the network. 
   Running main.py with --chain generates the chain.
   Running main.py with --gossip generates gossip (Note: running gossip without chain will lead to incorrect scids).

2. building the network consists of analyzing a provided network and scaling it up. 
   Therefore, you need your own network data and set analysisListChannelsFile 
   You can use data provided in data/channels_1-18-18.json.zx (make sure you unzip).
   To get your own network data to feed into main.py for building the network, run:
   `./lightning-cli listchannels` on a highly connected node. 
   You can use scrapeConnectedNodes.py to help make your node highly connected

3. To run without building network, you can use the .nodes files and .channels files 
   provided in /data as the nodeSaveFile and channelSaveFile located in config.py 
   or as cmdline args (ex. --nodeSaveFile /path/to/file). 

    


