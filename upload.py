#!/usr/bin/env python3

import re
from itertools import count
from requests import get


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
        self.category = self.re_cat.search(content)[1]

        self.discontinued = 'Discontinued' in content
        self.stub = 'Infobox' not in content
        if self.stub:
            return

        self.props = {m[1]: m[2] for m in self.re_prop.finditer(content)}
        self.desc = self.props.get('desc')
        self.res_in, self.res_in_opt, self.res_out = {}, {}, {}
        self.init_resources()

    def init_resources(self):
        for i in count(1):
            in_name = self.props.get('input%d' % i, '').strip()
            if in_name:
                is_opt = self.props.get('opt%d' % i) == 'yes'
                upd = self.res_in_opt if is_opt else self.res_in
                upd[in_name] = float(self.props.get('in_qty%d' % i) or '0')
            out_name = self.props.get('output%d' % i, '').strip()
            if out_name:
                self.res_out[out_name] = float(self.props.get('out_qty%d' % i) or '0')
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
                block = Block(block_data)
                if block.stub:
                    n_stub += 1
                elif block.discontinued:
                    n_discontinued += 1
                else:
                    n_complete += 1
                yield block
            except PagedOutError:
                pass

        print('Processed %d complete, %d discontinued, %d stubs' % (n_complete, n_discontinued, n_stub))

        if 'batchcomplete' in resp:
            break
        params.update(resp['continue'])


def main():
    blocks = sorted(iter_blocks())
    return


main()
