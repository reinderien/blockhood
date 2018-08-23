#!/usr/bin/env python3

from analyse import Analyse
from unity_asset_dir import get_dbs
from unity_unpack import unpack_dbs


def hashable_res(block):
    # The inner tuples must contain everything the optimizer cares about
    res = sorted((m, rk, rv)
                 for m in ('inputs', 'optionalInputs', 'outputs')
                 for rk, rv in block[m].items())
    with_conns = (tuple(res), *(block['connectUpper' + d] for d in ('Forward', 'Back', 'Left', 'Right')))
    return with_conns


def trim(blocks):
    old_len = len(blocks)
    while True:
        try:
            i = next(i for i, b in enumerate(blocks)
                     if b['category'] == 'WILD_TILES' or b['toolTipHeader'] == 'CANAL BRIDGE')
        except StopIteration:
            break
        del blocks[i]
    len_after_un = len(blocks)

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

    print('Trimmed blocks: %d unavailable, %d equivalent.' % (old_len - len_after_un,
                                                              len_after_un - len(blocks)))


def export_blocks(blocks):
    from csv import DictWriter

    keys = tuple(blocks[0].keys())
    with open('blocks.csv', 'w', encoding='utf-8', newline='') as f:
        w = DictWriter(f, keys)
        w.writeheader()

        for b in blocks:
            w.writerow(b)


def main():
    block_db, resource_db = get_dbs(r'D:\Program Files\SteamLibrary')
    blocks, resources = unpack_dbs(block_db['data'], resource_db['data'])

    # export_blocks(blocks)

    trim(blocks)
    print()

    Analyse(blocks, resources).analyse()


main()
