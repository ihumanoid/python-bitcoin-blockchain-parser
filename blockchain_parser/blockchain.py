# Copyright (C) 2015-2016 The bitcoin-blockchain-parser developers
#
# This file is part of bitcoin-blockchain-parser.
#
# It is subject to the license terms in the LICENSE file found in the top-level
# directory of this distribution.
#
# No part of bitcoin-blockchain-parser, including this file, may be copied,
# modified, propagated, or distributed except according to the terms contained
# in the LICENSE file.

import os
import mmap
import struct
import pickle
import stat

from .block import Block
from .index import DBBlockIndex
from .utils import format_hash


# Constant separating blocks in the .blk files
BITCOIN_CONSTANT = b"\xf9\xbe\xb4\xd9"


def get_files(path):
    """
    Given the path to the .bitcoin directory, returns the sorted list of .blk
    files contained in that directory
    """
    if not stat.S_ISDIR(os.stat(path)[stat.ST_MODE]):
        return [path]
    files = os.listdir(path)
    files = [f for f in files if f.startswith("blk") and f.endswith(".dat")]
    files = map(lambda x: os.path.join(path, x), files)
    return sorted(files)


def get_blocks(blockfile):
    """
    Given the name of a .blk file, for every block contained in the file,
    yields its raw hexadecimal value
    """
    with open(blockfile, "rb") as f:
        if os.name == 'nt':
            size = os.path.getsize(f.name)
            raw_data = mmap.mmap(f.fileno(), size, access=mmap.ACCESS_READ)
        else:
            # Unix-only call, will not work on Windows, see python doc.
            raw_data = mmap.mmap(f.fileno(), 0, prot=mmap.PROT_READ)
        length = len(raw_data)
        offset = 0
        block_count = 0
        while offset < (length - 4):
            if raw_data[offset:offset+4] == BITCOIN_CONSTANT:
                offset += 4
                size = struct.unpack("<I", raw_data[offset:offset+4])[0]
                offset += 4 + size
                block_count += 1
                yield raw_data[offset-size:offset]
            else:
                offset += 1
        raw_data.close()


def get_block(blockfile, offset):
    """Extracts a single block from the blockfile at the given offset"""
    with open(blockfile, "rb") as f:
        f.seek(offset - 4)  # Size is present 4 bytes before the db offset
        size, = struct.unpack("<I", f.read(4))
        return f.read(size)


class Blockchain(object):
    """Represent the blockchain contained in the series of .blk files
    maintained by bitcoind.
    """

    def __init__(self, path):
        self.path = path
        self.blockIndexes = None
        self.indexPath = None

    def get_unordered_blocks(self):
        """Yields the blocks contained in the .blk files as is,
        without ordering them according to height.
        """
        for blk_file in get_files(self.path):
            for raw_block in get_blocks(blk_file):
                yield Block(raw_block)

    def _index_confirmed(self, chain_indexes, num_confirmations=6):
        """Check if the first block index in "chain_indexes" has at least
        "num_confirmation" (6) blocks built on top of it.
        If it doesn't it is not confirmed and is an orphan.
        """

        # chains holds a 2D list of sequential block hash chains
        # as soon as there an element of length num_confirmations,
        # we can make a decision about whether or not the block in question
        # is confirmed by checking if it's hash is in that list
        chains = []
        # this is the block in question
        first_block = None

        # loop through all future blocks
        for i, index in enumerate(chain_indexes):
            # if this block doesn't have data don't confirm it
            if index.file == -1 or index.data_pos == -1:
                return False

            # parse the block
            blkFile = os.path.join(self.path, "blk%05d.dat" % index.file)
            block = Block(get_block(blkFile, index.data_pos))

            if i == 0:
                first_block = block

            chains.append([block.hash])

            for chain in chains:
                # if this block can be appended to an existing block in one
                # of the chains, do it
                if chain[-1] == block.header.previous_block_hash:
                    chain.append(block.hash)

                # if we've found a chain length == num_dependencies (usually 6)
                # we are ready to make a decesion on whether or not the block
                # belongs to a fork or the main chain
                if len(chain) == num_confirmations:
                    if first_block.hash in chain:
                        return True
                    else:
                        return False