# million-channels-project
Use this project to create a large test lightning network (~1M channels) with an accurate topology extrapolated from the current topology. 

This network can be used to test routing algorithms and optimize lightning implementations.

### Instructions on how to run without regenerating the network:

1. [Download](https://github.com/rustyrussell/million-channels-project-data) 1M gossip and regtest chain.

2. To set up the bitcoin regtest blockchain, do:

```
rm -rf ~/.bitcoin/regtest && mkdir ~/.bitcoin/regtest
tar xfa million-channels-project-data/v0.1/bitcoin/regtest_blocks.tar.xz
mv blocks ~/.bitcoin/regtest
```

3. For [c-lightning](https://github.com/ElementsProject/lightning), create a `gossip_store` (about 780MB) using the gossip files:

```
cd lightning
./configure --enable-developer && make
# This will take about 30 seconds
devtools/create-gossipstore -i <(xzcat ../million-channels-project-data/v0.1/gossip/1M.gossip.xz) -o ~/.lightning/gossip_store --csv <(xzcat ../million-channels-project-data/v0.1/gossip/scidSatoshis.csv.xz)
```

4. Run clightning, point it to the right .lightning directory, and watch it load gossip. 
    `./lightning-cli listchannels` <-- should return ~1M channels  

### Generating network or gossip from scratch

1. main.py can create the network, regtest chain, or the gossip messages. 
    Running main.py with --build  builds and saves the network. Add --analyze for pretty graphs and --draw for network graph.
    
    Running main.py with --chain generates the chain.
    
    Running main.py with --gossip generates gossip (Note: running gossip without chain will lead to incorrect scids).
    
    for example: 

    generating 1M channel network: 

   `python3 main.py --build --chain --gossip --name 1M --channels 1000000 --maxChannels 10000`
    generating 100K channels network: 

   `python3 main.py --build --chain --gossip --name 100K --channels 100000 --maxChannels 1000`

2. building the network consists of analyzing a provided network and scaling it up. 
   Therefore, you need your own network data and set analysisListChannelsFile 
   You can use data provided in data/channels_1-18-18.json.zx (make sure you unzip).
   To get your own network data to feed into main.py for building the network, run:
   `./lightning-cli listchannels` on a highly connected node. 
   You can use scrapeConnectedNodes.py to help make your node highly connected

3. To run without building network, you can use the .nodes files and .channels files 
   provided in /data as the nodeSaveFile and channelSaveFile located in config.py 
   or as cmdline args (ex. --nodeSaveFile /path/to/file). 

    


