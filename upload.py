#!/usr/bin/env python3

import re
from itertools import count
from requests import get


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


def iter_blocks():
    params = {'action': 'query',
              'generator': 'categorymembers',
              'gcmtitle': 'Category:Blocks',
              'gcmtype': 'page',
              'gcmlimit': 250,
              'prop': 'revisions',
              'rvprop': 'content',
              'format': 'json'}
    n_complete, n_discontinued, n_stub = 0, 0, 0

    while True:
        resp = get('https://blockhood.gamepedia.com/api.php', params=params).json()

        for block_data in resp['query']['pages'].values():
            try:
                yield Block(block_data)
                n_complete += 1
            except PagedOutError:
                pass
            except DiscontinuedError:
                n_discontinued += 1
            except StubError:
                n_stub += 1

        print('Processed %d complete, %d discontinued, %d stubs' % (n_complete, n_discontinued, n_stub))

        if 'batchcomplete' in resp:
            break
        params.update(resp['continue'])


def main():
    blocks = sorted(iter_blocks())
    return


main()
