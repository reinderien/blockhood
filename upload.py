#!/usr/bin/env python3

import re
from requests import session
from string import Template
from unity_asset_dir import get_dbs
from unity_unpack import unpack_dbs


mwurl = 'https://blockhood.gamepedia.com/api.php'


class PagedOutError(Exception):
    pass


class Block:
    re_prop = re.compile(r'\| (\w+) *= *(.*)$', re.M)
    re_cat = re.compile(r'\[\[Category:(?!Blocks)([^\]]+)\]\]')

    cats = {'BUILDINGS':       'Buildings',
            'ADV_BUILDINGS':   'Buildings',
            'PUBLIC_SPACE':    'Public Space',
            'ADV_PUBLICSPACE': 'Public Space',
            'ADV_PUBLIC_2':    'Public Space',
            'PRODUCTION':      'Production',
            'ADV_PRODUCTION':  'Production',
            'ORGANIC':         'Organics',
            'ADV_ORGANIC':     'Organics',
            'WILD_TILES':      'Natural blocks'}

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
            self.props = {}
        else:
            self.props = {m[1]: m[2] for m in self.re_prop.finditer(content)}

    def _add_p(self, name_k, qty_k, name, val, index):
        self.props.update({'%s%d' % (name_k, index): name.title(),
                           '%s_qty%d' % (qty_k, + index): '%g' % val})

    def load_unity(self):
        self.props['desc'] = self.unity_data['toolTipContent']
        self.category = Block.cats[self.unity_data['category']]

        # Initialize to defaults
        self.props.update({k + str(i): ''
                           for k in ('input', 'in_qty', 'output', 'out_qty', 'opt')
                           for i in range(1, 5)})

        in_i = 0
        for in_i, (in_n, in_x) in enumerate(self.unity_data['inputs'].items(), start=1):
            self._add_p('input', 'in', in_n, in_x, in_i)
        for opt_i, (opt_n, opt_x) in enumerate(self.unity_data['optionalInputs'].items(), start=in_i+1):
            self._add_p('input', 'in', opt_n, opt_x, opt_i)
            self.props['opt%d' % opt_i] = 'yes'
        for out_i, (out_n, out_x) in enumerate(self.unity_data['outputs'].items(), start=1):
            self._add_p('output', 'out', out_n, out_x, out_i)

    def __str__(self):
        return self.category + '.' + self.title

    def __lt__(self, other):
        return str(self) < str(other)

    def get_mwpage(self):
        with open('mwpage.tpl') as f:
            tpl = Template(f.read())
        return tpl.substitute(self.props, cat=self.category)


def download(sess):
    print('Loading blocks from Gamepedia...')
    params = {'action': 'query',
              'generator': 'categorymembers',
              'gcmtitle': 'Category:Blocks',
              'gcmtype': 'page',
              'gcmlimit': 250,
              'prop': 'revisions',
              'rvprop': 'content',
              'meta': 'tokens'}
    blocks = []
    n_complete, n_discontinued, n_stub = 0, 0, 0
    edit_token = None

    while True:
        resp = sess.get(mwurl, params=params)
        resp.raise_for_status()
        body = resp.json()
        new_token = body['query'].get('tokens', {}).get('csrftoken')
        if new_token:
            edit_token = new_token

        for block_data in body['query']['pages'].values():
            try:
                block = Block(block_data)
                if block.stub:
                    n_stub += 1
                elif block.discontinued:
                    n_discontinued += 1
                else:
                    n_complete += 1
                blocks.append(block)
            except PagedOutError:
                pass

        print('Processed %d complete, %d discontinued, %d stubs' % (n_complete, n_discontinued, n_stub))

        if 'batchcomplete' in body:
            break
        params.update(body['continue'])
    print()

    return sorted(blocks), edit_token


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
            bw.load_unity()

    print('Blocks only on the web, probably deprecated:',
          ', '.join(only_web))
    print('Blocks missing from the web:', len(only_un))
    print('Blocks present in both:', len(both))
    print()


def login():
    sess = session()
    sess.params['format'] = 'json'
    resp = sess.get(mwurl, params={'action': 'query',
                                   'meta': 'tokens',
                                   'type': 'login'})
    resp.raise_for_status()
    body = resp.json()
    assert('batchcomplete' in body)
    token = body['query']['tokens']['logintoken']

    with open('.mwpass') as f:
        resp = sess.post(mwurl, params={'action': 'login', 'lgname': 'Reinderien@block_updater'},
                         data={'lgpassword': f.read(), 'lgtoken': token})
    resp.raise_for_status()
    body = resp.json()
    assert(body['login']['result'] == 'Success')
    return sess


def upload(sess, blocks, edit_token):
    for i,b in enumerate(blocks):
        print('Editing %d/%d - %s' % (i+1, len(blocks), b.title))

        params = {'action': 'edit',
                  'pageid': b.id,
                  'bot': True,
                  'nocreate': True}
        data = {'text': b.get_mwpage(),
                'token': edit_token}
        resp = sess.post(mwurl, params=params, data=data)
        resp.raise_for_status()
        body = resp.json()
        assert(body['edit']['result'] == 'Success')


def main():
    sess = login()
    blocks_web, edit_token = download(sess)
    merge(blocks_web)

    stubs = [b for b in blocks_web if b.stub and not b.discontinued]
    upload(sess, stubs, edit_token)
    return


main()
