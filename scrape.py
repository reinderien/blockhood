#!/usr/bin/env python3

import lzma, numpy as np, pickle, re
from functools import reduce
from itertools import count
from os.path import isfile
from requests import get
from scipy.optimize import linprog


FN = 'blocks.pickle.xz'


class DiscontinuedError(Exception):
    pass


class StubError(Exception):
    pass


class PagedOutError(Exception):
    pass


class Block:
    re_prop = re.compile(r'\| (\w+) *= *(.*)$', re.M)
    re_cat = re.compile(r'\[\[Category:(?!Blocks)([^\]]+)\]\]')

    def __init__(self, data):
        self.title = data['title']
        revs = data.get('revisions')
        if not revs:
            raise PagedOutError(self.title + ' not in this page')

        content = data['revisions'][0]['*']
        if 'Discontinued' in content:
            raise DiscontinuedError(self.title + ' is discontinued')
        if 'Infobox' not in content:
            raise StubError(self.title + ' is an incomplete stub')

        self.category = self.re_cat.search(content).group(1)

        props = {m.group(1): m.group(2) for m in self.re_prop.finditer(content)}
        self.desc = props.get('desc')

        self.res_in, self.res_in_opt, self.res_out = {}, {}, {}

        for i in count(1):
            in_name = props.get('input%d' % i, '').strip()
            if in_name:
                is_opt = props.get('opt%d' % i) == 'yes'
                upd = self.res_in_opt if is_opt else self.res_in
                upd[in_name] = float(props.get('in_qty%d' % i) or '0')
            out_name = props.get('output%d' % i, '').strip()
            if out_name:
                self.res_out[out_name] = float(props.get('out_qty%d' % i) or '0')
            if not (in_name or out_name):
                break

    def __str__(self):
        return self.category + '.' + self.title

    def __lt__(self, other):
        return str(self) < str(other)

    @property
    def resource_names(self):
        return set(k for d in (self.res_in, self.res_in_opt, self.res_out)
                   for k in d.keys())


def iter_blocks():
    params = {'action': 'query',
              'generator': 'categorymembers',
              'gcmtitle': 'Category:Blocks',
              'gcmtype': 'page',
              'gcmlimit': 250,
              'prop': 'revisions',
              'rvprop': 'content',
              'format': 'json'}
    while True:
        resp = get('https://blockhood.gamepedia.com/api.php', params=params).json()

        n_complete, n_paged, n_discontinued, n_stub = 0, 0, 0, 0

        for block_data in resp['query']['pages'].values():
            try:
                yield Block(block_data)
                n_complete += 1
            except PagedOutError:
                n_paged += 1
            except DiscontinuedError:
                n_discontinued += 1
            except StubError as e:
                n_stub += 1
                print(str(e))

        print('Processed %d complete, %d paged, %d discontinued, %d stubs' %
              (n_complete, n_paged, n_discontinued, n_stub))

        if 'batchcomplete' in resp:
            break
        params.update(resp['continue'])


def save(blocks):
    print('Total complete: %d' % len(blocks))

    with lzma.open(FN, 'wb') as lz:
        pickle.dump(blocks, lz)


def load():
    with lzma.open(FN, 'rb') as lz:
        blocks = pickle.load(lz)

    print('%d blocks loaded' % len(blocks))
    return blocks


def analyse(blocks):
    """
    193 blocks, 53 resources

    Name dims     meaning
    c    1,193    coefficients to minimize c*x
    x    193,1    independent variable - block counts - comes in return var
    Aub  53,193   upper-bound coefficients for A*x <= b
    bub  53,1     upper bound for A*x <= b, all 0
    bounds (min,max) defaults to [0, inf]                - omit this

    Block counts must not be negative:
      implied by default value of `bounds`

    Should generate as few non-air resources as possible, and as much fresh air as possible:
      needs to affect c.
      maybe form c from a sum through the resource axis of all blocks, with air negative.
      Include the effects of optional inputs here.

    No resource rates may be negative, unless the negative only impacts optional inputs:
      for each resource, calculate the net rate without considering optional inputs.
      Use Aub and bub for this.
    """

    resource_names = sorted(reduce(set.union, (b.resource_names for b in blocks)))
    resource_indices = {n: i for i, n in enumerate(resource_names)}

    nr = len(resource_names)
    nb = len(blocks)

    rates_no_opt = np.empty((nr, 0))          # Resource rates without optional inputs
    rates_opt = np.empty((nr, 0))             # Optional rates

    def iter_res(col, attr, mu):
        for resource, qty in getattr(block, attr).items():
            col[resource_indices[resource]] += mu*qty

    for b, block in enumerate(blocks):
        nocol = [0]*nr                      # Column of mandatory rates for this block
        opcol = list(nocol)                 # Column of optional rates for this block
        iter_res(nocol, 'res_in', -1)
        iter_res(nocol, 'res_out', 1)
        iter_res(opcol, 'res_in_opt', -1)
        np.append(rates_no_opt, nocol)
        np.append(rates_opt, opcol)

        # todo

    return None


def decompile(blocks, fn):
    print('Loading assets...')

    # Todo - reintroduce
    # asstools = ctypes.cdll.LoadLibrary('AssetsToolsAPI_2.2beta3/bin64/AssetsTools.dll')

    with open(fn, 'rb') as f:
        # We have a lot of memory, so just load it (67MB)
        assets = f.read()

    print('Finding blocks...')

    interesting_strings = tuple(s.encode('ascii') for s in (
                                'allways',
                                'alwaysProducing',
                                'blocksProducing',
                                'directNeighbors',
                                'neighborDecay',
                                'neighborExist',
                                'neighborProducing',
                                'neighborProducingMultiple',
                                'oneAdjacentNeighbor',
                                'threeSquareNeighbors'))

    occurrences = []
    for ins in interesting_strings:
        i = 0
        while True:
            i = assets.find(ins, i)
            if i == -1:
                break
            occurrences.append(i)
            i += 1
    occurrences = sorted(occurrences)

    # pitches = [occurrences[i+1] - occurrences[i]
    #            for i in range(len(occurrences)-1)]
    # pitches are on the order of 12-32 within group, 2000-4000 out of group
    thresh = 200

    block_locations = []
    prev_o = 0
    for o in occurrences:
        if o - prev_o > thresh:
            block_locations.append(o)
        prev_o = o

    print('Finding block correspondence...')

    '''
    # Before the first interesting string occurrence, there are three nulls at least.
    # This is probably because field length precedes the field, and is in little-endian integer format.
    # However, this fails for some corner cases.
    
    print('Verifying block metadata...')

    for o in occurrences:
        start = o
        while True:
            while True:
                packed = assets[start-4:start]
                text_len = unpack('I', packed)[0]
                if text_len != 1:
                    break
                print('Warning, skipping')
                start += 4
            if text_len == 0:
                break
            field = assets[start:start+text_len]
            assert(text_len == len(field))
            assert(field in interesting_strings)

            # 32-bit alignment
            aligned_len = text_len & ~3
            if aligned_len < text_len:
                aligned_len += 4

            for b in assets[start+text_len:start+aligned_len]:
                assert(b == 0)

            start += aligned_len + 4  # next size
    '''

    return occurrences


def main():
    if isfile(FN):
        blocks = load()
    else:
        blocks = sorted(iter_blocks())
        save(blocks)

    # analyse(blocks)
    decompile(blocks, 'sharedassets2.assets')


main()
