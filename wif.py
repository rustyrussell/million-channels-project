'''
https://github.com/crcarlo/btcwif/blob/master/btcwif.py

Title: btcwif
Version: 0.1
Author: Carlo Cervellin
Website: carlo.cervellin.eu


Note: 80 is replaced with ef because of testnet/regtest private keys are different encoding than mainnet private keys

'''

import hashlib

# base58 alphabet
alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def sha256(arg) :
	''' Return a sha256 hash of a hex string '''
	byte_array = bytearray.fromhex(arg)
	m = hashlib.sha256()
	m.update(byte_array)
	return m.hexdigest()

def b58encode(hex_string) :
	''' Return a base58 encoded string from hex string '''
	num = int(hex_string, 16)
	encode = ""
	base_count = len(alphabet)
	while (num > 0) :
		num, res = divmod(num,base_count)
		encode = alphabet[res] + encode
	return encode

def b58decode(v):
	''' Decode a Base58 encoded string as an integer and return a hex string '''
	if not isinstance(v, str):
		v = v.decode('ascii')
	decimal = 0
	for char in v:
		decimal = decimal * 58 + alphabet.index(char)
	return hex(decimal)[2:] # (remove "0x" prefix)

def privToWif(priv, verbose=False) :
	''' Produce a WIF from a private key in the form of an hex string '''
	# 1 - Take a private key
	_priv = priv.lower() # just for aesthetics
	if verbose : print("Private key: "+_priv)
	# 2 - Add a 0x80 byte in front of it
	priv_add_x80 = "EF" + _priv   #TODO: this is 80 with mainnet addresses, and 239 with regtest
	if verbose : print("Private with x80 at beginning: "+priv_add_x80)
	# 3 - Perform SHA-256 hash on the extended key
	first_sha256 = sha256(priv_add_x80)
	if verbose : print("sha256: " + first_sha256.upper())
	# 4 - Perform SHA-256 hash on result of SHA-256 hash
	seconf_sha256 = sha256(first_sha256)
	if verbose : print("sha256: " + seconf_sha256.upper())
	# 5 - Take the first 4 bytes of the second SHA-256 hash, this is the checksum
	first_4_bytes = seconf_sha256[0:8]
	if verbose : print("First 4 bytes: " + first_4_bytes)
	# 6 - Add the 4 checksum bytes from point 5 at the end of the extended key from point 2
	resulting_hex = priv_add_x80 + first_4_bytes
	if verbose : print("Resulting WIF in HEX: " + resulting_hex)
	# 7 - Convert the result from a byte string into a base58 string using Base58Check encoding. This is the Wallet Import Format
	result_wif = b58encode(resulting_hex)
	if verbose : print("Resulting WIF: " + result_wif)
	return result_wif

def wifToPriv(wif, verbose=False) :
	''' Produce the private ECDSA key in the form of a hex string from a WIF string '''
	if not wifChecksum(wif, verbose) : raise Exception('The WIF is not correct (does not pass checksum)')
	# 1 - Take a Wallet Import Format string
	if verbose : print("WIF: " + wif)
	# 2 - Convert it to a byte string using Base58Check encoding
	byte_str = b58decode(wif)
	if verbose : print("WIF base58 decoded: " + byte_str)
	# 3 - Drop the last 4 checksum bytes from the byte string
	byte_str_drop_last_4bytes = byte_str[0:-8]
	if verbose : print("Decoded WIF drop last 4 bytes: " + byte_str_drop_last_4bytes)
	# 4 - Drop the first byte
	byte_str_drop_first_byte = byte_str_drop_last_4bytes[2:]
	if verbose : print("ECDSA private key: " + byte_str_drop_first_byte)
	return byte_str_drop_first_byte

def wifChecksum(wif, verbose=False) :
	''' Returns True if the WIF is positive to the checksum, False otherwise '''
	# 1 - Take the Wallet Import Format string
	if verbose : print("WIF: " + wif)
	# 2 - Convert it to a byte string using Base58Check encoding
	byte_str = b58decode(wif)
	if verbose : print("WIF base58 decoded: " + byte_str)
	# 3 - Drop the last 4 checksum bytes from the byte string
	byte_str_drop_last_4bytes = byte_str[0:-8]
	if verbose : print("Decoded WIF drop last 4 bytes: " + byte_str_drop_last_4bytes)
	# 3 - Perform SHA-256 hash on the shortened string
	sha_256_1 = sha256(byte_str_drop_last_4bytes)
	if verbose : print("SHA256 1: " + sha_256_1)
	# 4 - Perform SHA-256 hash on result of SHA-256 hash
	sha_256_2 = sha256(sha_256_1)
	if verbose : print("SHA256 2: " + sha_256_2)
	# 5 - Take the first 4 bytes of the second SHA-256 hash, this is the checksum
	first_4_bytes = sha_256_2[0:8]
	if verbose : print("First 4 bytes: " + first_4_bytes)
	# 6 - Make sure it is the same, as the last 4 bytes from point 2
	last_4_bytes_WIF = byte_str[-8:]
	if verbose : print("Last 4 bytes of WIF: " + last_4_bytes_WIF)
	bytes_check = False
	if first_4_bytes == last_4_bytes_WIF : bytes_check = True
	if verbose : print("4 bytes check: " + str(bytes_check))
	# 7 - If they are, and the byte string from point 2 starts with 0x80 (0xef for testnet addresses), then there is no error.
	check_sum = False
	if bytes_check and byte_str[0:2] == "ef" : check_sum = True
	if verbose : print("Checksum: " + str(check_sum))
	return check_sum
