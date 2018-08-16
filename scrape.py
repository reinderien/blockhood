#!/usr/bin/env python3

import fieldtypes, lzma, numpy as np, pickle, re, struct
from functools import reduce
from io import SEEK_SET
from itertools import count
from os.path import isfile
from pprint import pprint
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

        self.category = self.re_cat.search(content)[1]

        props = {m[1]: m[2] for m in self.re_prop.finditer(content)}
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


class AssetDecoder:
    def __init__(self, db_fn, source_fn, first_offset):
        self.f = open(db_fn, 'rb')
        self.f.seek(first_offset, SEEK_SET)
        self.items = []

        with open(source_fn, encoding='utf-8') as f:
            src = f.read()
        self.mbrs = list(fieldtypes.get_members(src))

    def decode(self):
        for list_index in count():
            item = {}
            for field in self.mbrs:
                file_off = self.f.tell()
                try:
                    val = field.field_type.read(self.f)
                except EOFError:
                    return
                item[field.field_name] = val
            self.items.append(item)


def align4(i):
    needs_pad = i & 3
    if needs_pad:
        i += 4 - needs_pad
    return i


def find_str(data, end):
    nrun = 0
    last_i = None
    for i in range(end - 1, end - 500, -1):
        if ord(' ') <= data[i] <= ord('z'):
            nrun += 1
            if nrun >= 10:
                break
        else:
            nrun = 0
            last_i = i
    else:
        return

    last_i = align4(last_i)
    return find_by_int(data, last_i)


def find_by_int(data, end):
    for i in range(end - 8, end - 500, -4):
        clen = struct.unpack('I', data[i:i+4])[0]
        if 0 < clen < 500:
            break
    else:
        return None
    start_i = i+4

    if not(0 <= end-start_i - clen < 4):
        newend = start_i + align4(clen)
        print('Warning: actual len %d, expected %d, using %d' % (clen, end - start_i, newend - start_i))
        end = newend

    content = data[start_i:start_i+clen].decode('utf-8')
    return start_i - 4, end, content


def decompile():
    print('Loading assets...')

    rad = AssetDecoder('resourceDB.dat', 'ResourceItem.cs', 292)
    rad.decode()

    with open('blockDB.dat', 'rb') as f:
        data = f.read()

    agent_starts = []
    i = 0
    agent_needle = 'oneAdjacentNeighbor'.encode('utf-8')
    first = True
    while True:
        i = data.find(agent_needle, i)
        if i == -1:
            break

        agent_list_start = i - 8
        lens = struct.unpack_from('II', data, agent_list_start)
        if lens[1] != len(agent_needle) or lens[0] < 1 or lens[0] > 20:
            print('Warning: weird lengths', lens)
        else:
            if first:
                first = False
            else:
                # Find a run of printable characters before the agent list
                descstart, descend, descstr = find_str(data, i-9)
                namestart, nameend, namestr = find_by_int(data, descstart)

                print('{namestr:25} '
                      '{namestart:6} {nameend:6} '
                      '{descstart:6} {descend:6} '
                      '{agent_list_start:6}'
                      .format(**locals()))

        i += len(agent_needle)

    return


def main():
    if isfile(FN):
        blocks = load()
    else:
        blocks = sorted(iter_blocks())
        save(blocks)

    # analyse(blocks)
    decompile()


main()
