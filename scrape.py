#!/usr/bin/env python3

import lzma, pickle, re
from functools import reduce
from itertools import count
from numpy import ndarray
from requests import get
from scipy.optimize import linprog

FN = 'blocks.pickle.xz'


class DiscontinuedError(Exception):
    pass


class IncompleteError(Exception):
    pass


class Block:
    re_prop = re.compile(r'\| (\w+) *= *(.*)$', re.M)
    re_cat = re.compile(r'\[\[Category:(?!Blocks)([^\]]+)\]\]')

    def __init__(self, data):
        self.title = data['title']
        revs = data.get('revisions')
        if not revs:
            raise IncompleteError(self.title + ' is incomplete')

        content = data['revisions'][0]['*']
        if 'Discontinued' in content:
            raise DiscontinuedError(self.title + ' is discontinued')

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

        n_complete, n_incomplete, n_discontinued = 0, 0, 0

        for block_data in resp['query']['pages'].values():
            try:
                yield Block(block_data)
                n_complete += 1
            except IncompleteError:
                n_incomplete += 1
            except DiscontinuedError:
                n_discontinued += 1

        print('Processed %d complete, %d incomplete, %d discontinued' %
              (n_complete, n_incomplete, n_discontinued))

        if 'batchcomplete' in resp:
            break
        params.update(resp['continue'])


def save():
    blocks = sorted(iter_blocks())
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
    resource_indices = {n: i for i, n in enumerate(resource_names.keys())}

    return None


# save()
analyse(load())
