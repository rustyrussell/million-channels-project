# cannot be changed by user:
coinbaseReward = 5000000000    #50 bitcoins
halvingInterval = 150
maxOutputsPerTx = 1000
scalingUnits = .000001  # units of cap
confirmations = 6
onchainSatoshiMinimum = 100
maxTxPerBlock = 20 # 200 transactions in a block plus coinbase (which is at index 0)
iCoinbasePriv = 100000000   # some private key that is completely insecure. Doesn't matter what it is.
bCoinbasePriv = bytearray(iCoinbasePriv.to_bytes(32, "big"))


