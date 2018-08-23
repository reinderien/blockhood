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

    def __init__(self, title, category, props, id=None, stub=False, discontinued=False, web=False, unity=False):
        self.title, self.category, self.props, self.id, self.stub, self.discontinued, self.web, self.unity = \
            title, category, props, id, stub, discontinued, web, unity

    @staticmethod
    def from_web(data):
        revs = data.get('revisions')
        if not revs:
            raise PagedOutError()
        content = data['revisions'][0]['*']
        stub = 'Infobox' not in content
        if stub:
            props = {}
        else:
            props = {m[1]: m[2] for m in Block.re_prop.finditer(content)}
        return Block(title=data['title'], id=data['pageid'], props=props, stub=stub, web=True,
                     category=Block.re_cat.search(content)[1],
                     discontinued='Discontinued' in content)

    @staticmethod
    def _add_p(props, name_k, qty_k, name, val, index):
        props.update({'%s%d' % (name_k, index): name.title(),
                      '%s_qty%d' % (qty_k, + index): '%g' % val})

    @staticmethod
    def from_unity(data):
        # Initialize to defaults
        props = {'desc': data['toolTipContent']}
        props.update({k + str(i): ''
                      for k in ('input', 'in_qty', 'output', 'out_qty', 'opt')
                      for i in range(1, 5)})
        in_i = 0
        for in_i, (in_n, in_x) in enumerate(data['inputs'].items(), start=1):
            Block._add_p(props, 'input', 'in', in_n, in_x, in_i)
        for opt_i, (opt_n, opt_x) in enumerate(data['optionalInputs'].items(), start=in_i+1):
            Block._add_p(props, 'input', 'in', opt_n, opt_x, opt_i)
            props['opt%d' % opt_i] = 'yes'
        for out_i, (out_n, out_x) in enumerate(data['outputs'].items(), start=1):
            Block._add_p(props, 'output', 'out', out_n, out_x, out_i)

        return Block(title=data['toolTipHeader'].title(),
                     category=Block.cats[data['category']], props=props, unity=True)

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
                block = Block.from_web(block_data)
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


def load_un():
    block_db, resource_db = get_dbs(r'D:\Program Files\SteamLibrary')
    blocks_un, resources_un = unpack_dbs(block_db['data'], resource_db['data'])
    return [Block.from_unity(b) for b in blocks_un]


def merge(blocks_web, blocks_un):
    web_lookup = {w.title.title(): w for w in blocks_web}
    un_lookup = {u.title.title(): u for u in blocks_un}
    web_names = set(web_lookup.keys())
    un_names = set(un_lookup.keys())
    both = web_names & un_names
    only_web = web_names - un_names
    only_un = un_names - web_names

    merged = []

    for bn in only_un:
        merged.append(un_lookup[bn])
    for bn in only_web:
        merged.append(web_lookup[bn])
    for bn in both:
        bu = un_lookup[bn]
        bw = web_lookup[bn]
        bu.id, bu.web, bu.stub, bu.discontinued = bw.id, bw.web, bw.stub, bw.discontinued

    print('Blocks only on the web, probably deprecated:', ', '.join(only_web))
    print('Blocks missing from the web:', len(only_un))
    print('Blocks present in both:', len(both))
    print()

    return merged


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


def upload(sess, blocks, edit_token, update=True):
    for i,b in enumerate(blocks):
        print('Editing %d/%d - %s' % (i+1, len(blocks), b.title))

        params = {'action': 'edit',
                  'bot': True}
        if update:
            params['nocreate'] = True
        else:
            params['createonly'] = True
        if b.id:
            params['pageid'] = b.id
        else:
            params['title'] = b.title
        data = {'text': b.get_mwpage(),
                'token': edit_token}
        resp = sess.post(mwurl, params=params, data=data)
        resp.raise_for_status()
        body = resp.json()
        assert(body['edit']['result'] == 'Success')


def main():
    sess = login()
    blocks_web, edit_token = download(sess)
    blocks_un = load_un()
    blocks = merge(blocks_web, blocks_un)

    # Update stubs only
    # to_update = [b for b in blocks if b.stub and not b.discontinued]

    # Create anything missing
    to_update = [b for b in blocks if not b.web
                 and b.title != 'Grassland']  # Conflict with biome of same name

    upload(sess, to_update, edit_token, update=False)
    return


main()
