#!/usr/bin/env python3

from analyse import analyse
from unity_asset_dir import search_asset_file
from unity_unpack import unpack_blocks


def hashable_res(block):
    res = sorted((m, rk, rv)
                 for m in ('inputs', 'opt_inputs', 'outputs')
                 for rk, rv in getattr(block, m).items())
    return tuple(res)


def trim(blocks):
    unavailable = {'TRAILER', "BLOCK'HOME", 'BLOKCORP HQ', 'TREEHOUSE', 'CANAL BRIDGE'}
    for u in unavailable:
        i = next(i for i, b in enumerate(blocks) if b.name == u)
        del blocks[i]

    blocks_hashable = sorted((hashable_res(b), ib) for ib, b in enumerate(blocks))
    to_remove = set()
    i = 0
    while i < len(blocks_hashable)-1:
        res, ib = blocks_hashable[i]
        for j in range(i+1, len(blocks_hashable)):
            next_res, next_ib = blocks_hashable[j]
            if res == next_res:
                to_remove.add(next_ib)
            else:
                break
        i = j

    for ib in sorted(to_remove, reverse=True):
        del blocks[ib]

    print('Trimmed blocks: %d unavailable, %d equivalent.' % (len(unavailable), len(to_remove)))


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
    trim(blocks)
    print()

    analyse(blocks, resources)


main()
