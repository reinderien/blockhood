#!/usr/bin/env python3

from analyse import analyse
from unity_asset_dir import search_asset_file
from unity_unpack import unpack_blocks


def main():
    print('Loading game databases...')
    block_db = 21228
    resource_db = 21231
    dbs = search_asset_file(r'D:\Program Files\SteamLibrary\steamapps\common'
                            r'\Blockhood\BLOCKHOOD v0_40_08_Data\sharedassets2.assets',
                            (block_db, resource_db))
    block_db = dbs[block_db]
    resource_db = dbs[resource_db]
    print('Loaded %s %dkiB, %s %dkiB.' % (block_db['name'], block_db['size']/1024,
                                         resource_db['name'], resource_db['size']/1024))
    print()
    assert(block_db['name'] == 'blockDB_current')
    assert(resource_db['name'] == 'resourceDB')

    blocks, resources = unpack_blocks(block_db['data'], resource_db['data'])
    analyse(blocks, resources)


main()
