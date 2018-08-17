#!/usr/bin/env python3

from analyse import analyse
from unity_asset_dir import search_asset_file
from unity_unpack import unpack_blocks


def main():
    block_db = 21228
    resource_db = 21231
    dbs = search_asset_file(r'D:\Program Files\SteamLibrary\steamapps\common'
                            r'\Blockhood\BLOCKHOOD v0_40_08_Data\sharedassets2.assets',
                            (block_db, resource_db))
    blocks, resources = unpack_blocks()
    analyse(blocks, resources)
    return


main()
