from common import crypto
import sys
from bitcoin import SelectParams


def main():
    argv = sys.argv
    source = int(argv[1])
    dest = int(argv[2])
    printPubKeys(source, dest)


def printPubKeys(source, dest):
    SelectParams("regtest")
    sourcePub = crypto.compPubKey(crypto.makeSinglePrivKeyNodeId(source))
    destPub = crypto.compPubKey(crypto.makeSinglePrivKeyNodeId(dest))
    print("source pub key", bytearray(sourcePub).hex())
    print("dest pub key", bytearray(destPub).hex())

main()
