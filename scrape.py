#!/usr/bin/env python3

import fieldtypes, lzma, numpy as np, pickle, re
from collections import namedtuple
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


Member = namedtuple('MemberType', ('field_index', 'access', 'type_name', 'field_name', 'field_type'))


class AssetDecoder:
    def __init__(self, db_fn, source_fn, first_offset):
        self.f = open(db_fn, 'rb')
        self.f.seek(first_offset, SEEK_SET)
        self.items = []

        with open(source_fn, encoding='utf-8') as f:
            src = f.read()

        types = [fieldtypes.Int(), fieldtypes.Float(), fieldtypes.String(), fieldtypes.AssetRef()]

        for tm in re.finditer(r'\s*public enum (\S+)$', src, re.M):
            type_name = tm.group(1)
            start = tm.start(1)
            end = src.index('}', start)
            val_src = src[start:end]
            vals = tuple(m.group(1) for m in
                         re.finditer(r'\s*(\S+),$', val_src, re.M))
            types.append(fieldtypes.Enum(type_name, vals))

        self.mbrs = []

        for field_index, m in enumerate(re.finditer(r'^\s*(public|private)'
                                                    r'\s+(\S+)' 
                                                    r'\s+(\S+);', src, re.M)):
            access, type_name, field_name = m.groups()
            field_type = next(t for t in types if t.pat.match(type_name))
            self.mbrs.append(Member(field_index, access, type_name, field_name, field_type))

    def decode(self):
        for list_index in count():
            item = {}
            for field in self.mbrs:
                file_off = self.f.tell()
                try:
                    val = field.field_type.read(self.f)
                except EOFError:
                    return
                item_field = {m: getattr(field, m) for m in Member._fields}
                item_field.update({
                    'listindex': list_index,
                    'fileoffdec': file_off,
                    'fileoffhex': '0x{0:08X}'.format(file_off),
                    'val': val
                })
                pprint(item_field)
                item[field.field_name] = val
            self.items.append(item)


def decompile():
    print('Loading assets...')

    rad = AssetDecoder('resourceDB.dat', 'ResourceItem.cs', 292)
    # bad = AssetDecoder('blockDB.dat', 'Block.cs', 292)
    rad.decode()

    return rad
    # bad.decode()


def main():
    if isfile(FN):
        blocks = load()
    else:
        blocks = sorted(iter_blocks())
        save(blocks)

    # analyse(blocks)
    decompile()


main()
