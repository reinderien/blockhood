#!/usr/bin/env python3

import fieldtypes, numpy as np, struct
from collections import namedtuple
from functools import reduce
from io import SEEK_SET, BytesIO
from scipy.optimize import linprog


def analyse(blocks, resources):
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

    resource_names = sorted(r['alias'] for r in resources)
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
        while True:
            item = {}
            for field in self.mbrs:
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
        end = newend

    content = data[start_i:start_i+clen].decode('utf-8')
    return start_i - 4, end, content


BlockRates = namedtuple('BlockRates', ('name', 'inputs', 'outputs', 'opt_inputs'))


def decompile():
    print('Loading resource database...')
    rad = AssetDecoder('resourceDB.dat', 'ResourceItem.cs', 292)
    rad.decode()

    print('Loading block database...')
    with open('blockDB.dat', 'rb') as f:
        data = f.read()

    agent_str_start = 0
    agent_needle = 'oneAdjacentNeighbor'.encode('utf-8')
    first = True
    t_bool, t_int, t_float = fieldtypes.Bool(), fieldtypes.Int(), fieldtypes.Float()
    t_int_list, t_float_list = fieldtypes.List(t_int), fieldtypes.List(t_float)

    def read_res():
        return (rad.items[i - 1]['alias'] for i in t_int_list.read(rate_sect))

    def read_rate():
        return t_float_list.read(rate_sect)

    blocks = []
    while True:
        agent_str_start = data.find(agent_needle, agent_str_start)
        if agent_str_start == -1:
            break

        agent_list_start = agent_str_start - 8
        lens = struct.unpack_from('II', data, agent_list_start)
        if lens[1] != len(agent_needle) or lens[0] < 1 or lens[0] > 20:
            print('Warning: weird lengths', lens)
        else:
            if first:
                first = False
            else:
                # Find a run of printable characters before the agent list
                descstart, descend, descstr = find_str(data, agent_list_start)

                if descstr.isupper():
                    namestart, nameend, namestr = descstart, descend, descstr
                    descstart, descend, descstr = nameend, nameend + 4, ''
                    assert(struct.unpack('I', data[descstart: descstart+4]) == (0,))
                else:
                    namestart, nameend, namestr = find_by_int(data, descstart)

                rate_sect = BytesIO(data[descend: agent_list_start])
                t_bool.read(rate_sect)              # connect
                assert(t_int.read(rate_sect) == 0)  # junk
                t_int.read(rate_sect)               # distanceToStreet
                assert(t_int.read(rate_sect) == 0)  # junk

                input_names, output_names = read_res(), read_res()
                input_amounts, output_amounts = read_rate(), read_rate()
                optional_input_names, optional_input_amounts = read_res(), read_rate()

                blocks.append(BlockRates(
                    namestr,
                    {n: a for n, a in zip(input_names, input_amounts)},
                    {n: a for n, a in zip(output_names, output_amounts)},
                    {n: a for n, a in zip(optional_input_names, optional_input_amounts)}))

        agent_str_start += len(agent_needle)
    return sorted(blocks, key=lambda b: b.name), rad.items


def main():
    blocks, resources = decompile()
    analyse(blocks, resources)
    return


main()
