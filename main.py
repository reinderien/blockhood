#!/usr/bin/env python3

from analyse import analyse
from unity_asset_dir import search_asset_file
from unity_unpack import unpack_blocks


def trim(blocks):
    unavailable = {'TRAILER', "BLOCK'HOME", 'BLOKCORP HQ', 'TREEHOUSE'}
    for u in unavailable:
        i = next(i for i, b in enumerate(blocks) if b.name == u)
        del blocks[i]


def main():
    print('Loading game databases...', end=' ')
    block_db, resource_db = 21228, 21231
    dbs = search_asset_file(r'D:\Program Files\SteamLibrary\steamapps\common'
                            r'\Blockhood\BLOCKHOOD v0_40_08_Data\sharedassets2.assets',
                            (block_db, resource_db))
    block_db, resource_db = dbs[block_db], dbs[resource_db]
    print('Loaded %s %dkiB, %s %dkiB.' % (block_db['name'], block_db['size']/1024,
                                          resource_db['name'], resource_db['size']/1024))
    assert(block_db['name'] == 'blockDB_current')
    assert(resource_db['name'] == 'resourceDB')

    blocks, resources = unpack_blocks(block_db['data'], resource_db['data'])
    print()

    trim(blocks)
    analyse(blocks, resources)


main()
