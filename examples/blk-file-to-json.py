
import sys
import json
from blockchain_parser.blockchain import *

"""
execute as:
cd ~/dev/python-bitcoin-blockchain-parser/examples &&
 python blk-file-to-json.py \
 ~/Library/Application\ Support/Bitcoin/test/blk00000.dat \
~/dev/python-bitcoin-blockchain-parser/blk0000.json
"""
blk_file = sys.argv[1]
output_json_file = sys.argv[2]

with open(output_json_file, "w") as file:
    transaction_counter = 0
    for raw_block in get_blocks(blk_file):
        block = Block(raw_block)

        for transaction in block.transactions:
            json_transaction = {}
            json_transaction["block_id"] = block.hash
            json_transaction["previous_block"] = block.header.previous_block_hash
            json_transaction["merkle_root"] = block.header.merkle_root
            json_transaction["nonce"] =block.header.nonce
            json_transaction["num_transactions"] = block.n_transactions
            json_transaction["timestamp"] = block.header.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            json_transaction["transaction_id"] = transaction.txid

            inputs = []
            for input in transaction.inputs:
                json_input = {}
                json_input["script"] = input.script.value
                json_input["transaction_hash"] = input.transaction_hash
                json_input["transaction_index"] = input.transaction_index
                inputs.append(json_input)
            json_transaction["inputs"] = inputs

            outputs = []
            for output in transaction.outputs:
                json_output = {}
                json_output["script"] = output.script.value
                json_output["output_satoshis"] = output.value
                json_output["btc"] = output.value / 100000000

                addresses = []
                for address in output.addresses:
                    addresses.append(address.address)
                json_output["addresses"] = addresses

                outputs.append(json_output)
            json_transaction["outputs"] = outputs

            json.dump(json_transaction, file)
            file.write(os.linesep)

            transaction_counter = transaction_counter + 1
            if (transaction_counter % 10000) == 0:
                print("Transactions processed:", transaction_counter)
