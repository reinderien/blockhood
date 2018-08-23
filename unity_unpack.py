from collections import namedtuple
from fieldtypes import *
from io import SEEK_SET, BytesIO
from struct import unpack_from
import re

Member = namedtuple('MemberType', ('field_index', 'access', 'type_name', 'field_name', 'field_type'))
verbose = False


class AssetDecoder:
    def __init__(self, f, source_fn, first_offset):
        self.f = f
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


class JumbledAssetDecoder(AssetDecoder):
    def __init__(self, f, source_fn, first_offset):
        super().__init__(f, source_fn, first_offset)

    def decode_one(self, sections):
        if verbose:
            print()
            print()
            row = '{:>6} {:>6} {:>6} {:>4} {:>4} {:>4} {:25} {:25}'
            header = row.format('From', 'To', 'Bytes', 'M1', 'M2', 'Mbrs', 'StartField', 'EndField')
            print('Used:')
            print(header)
            used_ranges = []

        item = {}
        for off, mbr_first, mbr_last in sections:
            if off < 0:  # relative
                self.f.seek(-off, SEEK_CUR)
                curr = self.f.tell()
            else:
                self.f.seek(off, SEEK_SET)
                curr = off
            mbr_i = next(i for i,m in enumerate(self.mbrs) if m.field_name == mbr_first)
            mbr_j = mbr_i + 1 + next(j for j,m in enumerate(self.mbrs[mbr_i:]) if m.field_name == mbr_last)
            for mbr in self.mbrs[mbr_i:mbr_j]:
                before_fail_pos = self.f.tell()
                val = mbr.field_type.read(self.f)
                item[mbr.field_name] = val
            end = self.f.tell()

            if verbose:
                used_ranges.append((mbr_i, mbr_j, curr, end))
                print(row.format(curr, end, end-curr, mbr_i, mbr_j-1, mbr_j-mbr_i,
                                 *(self.mbrs[i].field_name for i in (mbr_i, mbr_j-1))))
        if verbose:
            print('Missed:')
            print(header)
            used_ranges = sorted(used_ranges)
            used_ranges.append((len(self.mbrs), '?', '?', '?'))
            prev_i = 0
            for used_i, used_j, used_o1, used_o2 in used_ranges:
                if used_i > prev_i:
                    try:
                        missed_o1 = next(o2 for u1, u2, o1, o2 in used_ranges
                                         if u2 == prev_i)
                    except StopIteration:
                        missed_o1 = '?'

                    print(row.format(
                        missed_o1, used_o1,  '?',
                        prev_i, used_i-1, used_i-prev_i,
                        *(self.mbrs[i].field_name for i in (prev_i, used_i-1))))
                prev_i = used_j
        return item


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


def get_block_sections(bad, data, agent_list_start):
    # Find a run of printable characters before the agent list
    descstart, descend, descstr = find_str(data, agent_list_start)

    if descstr.isupper():
        namestart, nameend, namestr = descstart, descend, descstr
        descstart, descend, descstr = nameend, nameend + 4, ''
        assert (unpack('I', data[descstart: descstart + 4]) == (0,))
    else:
        namestart, nameend, namestr = find_by_int(data, descstart)

    is_walkable_start = namestart - 92
    my_name_start, my_name_end, my_name_str = find_by_int(data, is_walkable_start)
    block_to_copy_start = my_name_start - 24

    block_mbr_i = next(i for i,m in enumerate(bad.mbrs) if m.field_name == 'blockToCopy')
    str_end = block_to_copy_start
    for mbr_i in range(block_mbr_i-1, -1, -1):
        mbr = bad.mbrs[mbr_i]
        if mbr.field_name == 'icon':
            break
        new_start, new_end, content = find_by_int(data, str_end)
        str_end = new_start

    # It's doubtful that altTexture1 actually starts here - it looks like boolean data - but...
    # whatever, it parses, and gets us the i18n data correctly after
    tex_start = new_start - 80

    # This list is not exhaustive
    return [(tex_start, 'altTexture1', 'toolTipContent'),
            (descend + 8, 'distanceToStreet', 'distanceToStreet'),
            (descend + 16, 'inputs', 'optionalInputsAmounts'),
            (agent_list_start, 'allAgentFunctionsString', 'needsAccessToProduce')]
            # (-24, 'myType', 'prevSynergy')]


def unpack_dbs(block_data, resource_data):
    print('Unpacking resource database...', end=' ')
    with BytesIO(resource_data) as f:
        rad = AssetDecoder(f, 'ResourceItem.cs', 248)
        rad.decode()
    print('%d resources.' % len(rad.items))

    print('Unpacking block database...', end=' ')
    agent_str_start = 0
    agent_needle = 'oneAdjacentNeighbor'.encode('utf-8')
    first = True

    blocks = []
    with BytesIO(block_data) as f:
        bad = JumbledAssetDecoder(f, 'Block.cs', 0)
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
                block_sects = get_block_sections(bad, block_data, agent_list_start)
                block = bad.decode_one(block_sects)

                # This is a straight-up error in the data
                if not (block['toolTipHeader'] == 'WETLAND' and block['myName'] == 'T Old Cactus'):
                    blocks.append(block)

            agent_str_start += len(agent_needle)

    for b in blocks:
        for kn in ('inputs', 'outputs', 'optionalInputs'):
            ka = kn + 'Amounts'
            b[kn] = {rad.items[n-1]['alias']: round(a, 8)  # Deal with single-to-double error
                     for n, a in zip(b[kn], b[ka])}

    print('%d blocks.' % len(blocks))
    print()

    return (sorted(blocks, key=lambda b: b['toolTipHeader']),
            sorted(rad.items, key=lambda r: r['alias']))
