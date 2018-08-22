#!/usr/bin/env python3

import re
from itertools import count
from requests import get
from unity_asset_dir import get_dbs
from unity_unpack import unpack_dbs


class PagedOutError(Exception):
    pass


class Block:
    re_prop = re.compile(r'\| (\w+) *= *(.*)$', re.M)
    re_cat = re.compile(r'\[\[Category:(?!Blocks)([^\]]+)\]\]')

    def __init__(self, data):
        self.title = data['title']
        self.id = data['pageid']
        self.unity_data = None
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
    print('Loading blocks from Gamepedia...')
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
    print()


def merge(blocks_web):
    block_db, resource_db = get_dbs(r'D:\Program Files\SteamLibrary')
    blocks_un, resources_un = unpack_dbs(block_db['data'], resource_db['data'])

    web_names = {w.title.title() for w in blocks_web}
    un_names = {b['toolTipHeader'].title() for b in blocks_un}

    both = web_names & un_names
    only_web = web_names - un_names
    only_un = un_names - web_names

    for bw in blocks_web:
        bw_title = bw.title.title()
        if bw_title in both:
            bw.unity_data = next(bu for bu in blocks_un if bu['toolTipHeader'].title() == bw_title)

    print('Blocks only on the web, probably deprecated:',
          ', '.join(only_web))
    print('Blocks missing from the web:', len(only_un))
    print('Blocks present in both:', len(both))
    print()


def main():
    blocks_web = sorted(iter_blocks())
    merge(blocks_web)

    return


main()
