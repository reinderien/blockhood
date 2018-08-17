from collections import namedtuple
from fieldtypes import *
from io import SEEK_SET, BytesIO
from struct import unpack_from
import re

Member = namedtuple('MemberType', ('field_index', 'access', 'type_name', 'field_name', 'field_type'))


class AssetDecoder:
    def __init__(self, data, source_fn, first_offset):
        self.f = BytesIO(data)
        self.f.seek(first_offset, SEEK_SET)
        self.items = []

        with open(source_fn, encoding='utf-8') as f:
            src = f.read()
        self.mbrs = list(get_members(src))

    def decode(self):
        while True:
            item = {}
            for field in self.mbrs:
                try:
                    val = field.field_type.read(self.f)
                except EOFError:
                    return
                item[field.field_name] = val
            self.items.append(item)


def get_types(src):
    types = {n: t()
             for t in (Int, Float, Bool, String, AssetRef, GameObject, Vector3)
             for n in t.names}

    enum_re = re.compile(r'\s*public enum (\S+)$', re.M)
    for tm in enum_re.finditer(src):
        type_name = tm.group(1)
        start = tm.start(1)
        end = src.index('}', start)
        val_src = src[start:end]
        vals = tuple(m[1] for m in
                     re.finditer(r'\s*(\S+),$', val_src, re.M))
        types[type_name] = Enum(vals)

    list_re = re.compile(r'(List<([^<>]+)>)|'
                         r'(\S+)\[\]', re.M)
    for tm in list_re.finditer(src):
        inner = types[tm[2] or tm[3]]
        types[tm[0]] = List(inner)

    return types


def get_members(src):
    types = get_types(src)

    mbr_re = re.compile(r'^\s*(public|private)'
                        r'\s+(\S+)' 
                        r'\s+(\S+)(;| =)', re.M)
    for field_index, m in enumerate(mbr_re.finditer(src, re.M)):
        access, type_name, field_name = m.groups()[:3]
        field_type = types[type_name]
        yield Member(field_index, access, type_name, field_name, field_type)


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
        clen = unpack('I', data[i:i+4])[0]
        if 0 < clen < 500:
            break
    else:
        return None
    start_i = i+4

    if not(0 <= end-start_i - clen < 4):
        newend = start_i + align4(clen)
        end = newend

    content = data[start_i:start_i+clen].decode('utf-8')
    return start_i - 4, end, content


BlockRates = namedtuple('BlockRates', ('name', 'inputs', 'outputs', 'opt_inputs'))

t_bool, t_int, t_float = Bool(), Int(), Float()
t_int_list, t_float_list = List(t_int), List(t_float)


def get_block(data, agent_list_start, rad_items):
    def read_res():
        return (rad_items[i - 1]['alias'] for i in t_int_list.read(rate_sect))

    def read_rate():
        return t_float_list.read(rate_sect)

    # Find a run of printable characters before the agent list
    descstart, descend, descstr = find_str(data, agent_list_start)

    if descstr.isupper():
        namestart, nameend, namestr = descstart, descend, descstr
        descstart, descend, descstr = nameend, nameend + 4, ''
        assert (unpack('I', data[descstart: descstart + 4]) == (0,))
    else:
        namestart, nameend, namestr = find_by_int(data, descstart)

    rate_sect = BytesIO(data[descend: agent_list_start])
    t_bool.read(rate_sect)  # connect
    assert (t_int.read(rate_sect) == 0)  # junk
    t_int.read(rate_sect)  # distanceToStreet
    assert (t_int.read(rate_sect) == 0)  # junk

    input_names, output_names = read_res(), read_res()
    input_amounts, output_amounts = read_rate(), read_rate()
    optional_input_names, optional_input_amounts = read_res(), read_rate()

    return BlockRates(namestr,
                      {n: a for n, a in zip(input_names, input_amounts)},
                      {n: a for n, a in zip(output_names, output_amounts)},
                      {n: a for n, a in zip(optional_input_names, optional_input_amounts)})


def unpack_blocks(block_data, resource_data):
    print('Unpacking resource database...')
    rad = AssetDecoder(resource_data, 'ResourceItem.cs', 248)
    rad.decode()
    print('%d resources.' % len(rad.items))
    print()

    print('Unpacking block database...')
    agent_str_start = 0
    agent_needle = 'oneAdjacentNeighbor'.encode('utf-8')
    first = True

    blocks = {}
    while True:
        agent_str_start = block_data.find(agent_needle, agent_str_start)
        if agent_str_start == -1:
            break

        agent_list_start = agent_str_start - 8
        lens = unpack_from('II', block_data, agent_list_start)
        if lens[1] != len(agent_needle) or lens[0] < 1 or lens[0] > 20:
            print('Warning: weird lengths', lens)
        elif first:
            first = False
        else:
            block = get_block(block_data, agent_list_start, rad.items)
            blocks[block.name] = block

        agent_str_start += len(agent_needle)
    print('%d blocks.' % len(blocks))
    print()

    return (sorted(blocks.values(), key=lambda b: b.name),
            sorted(rad.items, key=lambda r: r['alias']))
