import numpy as np


def get_rates(blocks, res_inds, nr):
    rates_no_opt = np.empty((nr, 0))          # Resource rates without optionals
    rates_opt = np.empty((nr, 0))             # Optional rates

    for b, block in enumerate(blocks):
        nocol = np.zeros((nr, 1))             # Column of mandatory rates for this block
        opcol = np.zeros((nr, 1))             # Column of optional rates for this block

        for res, qty in block.inputs.items():
            nocol[res_inds[res]] -= qty
        for res, qty in block.opt_inputs.items():
            opcol[res_inds[res]] -= qty
        for res, qty in block.outputs.items():
            if qty < 0:
                col = opcol
            else:
                col = nocol
            col[res_inds[res]] += qty

        rates_no_opt = np.append(rates_no_opt, nocol, 1)
        rates_opt = np.append(rates_opt, opcol, 1)
    return rates_no_opt, rates_opt


def get_c(rates_no_opt, rates_opt, res_inds):
    # Calculate c: sum opt and no_opt to eliminate resources dimension
    air_index = res_inds['FRESH AIR']
    air_weight = -10

    rates_no_opt_air = np.copy(rates_no_opt)
    rates_no_opt_air[air_index, :] *= air_weight
    rates_opt_air = np.copy(rates_opt)
    rates_opt_air[air_index, :] *= air_weight
    return np.sum(rates_opt_air, 0) + np.sum(rates_no_opt_air, 0)


def analyse(blocks, resources):
    """
    nb=231 blocks, nr=78 resources

    Name dims     meaning
    c    1,231    coefficients to minimize c*x
    x    231,1    independent variable - block counts - comes in return var
    Aub  78,231   upper-bound coefficients for A*x <= b
    bub  78,1     upper bound for A*x <= b, all 0
    bounds (min,max) defaults to [0, inf]                - omit this

    Block counts must not be negative:
      implied by default value of `bounds`

    Block count should not run away to insanity: maybe specify a fixed count of 200

    Should generate as few non-air resources as possible, and as much fresh air as possible:
      needs to affect c.
      maybe form c from a sum through the resource axis of all blocks, with air negative.
      Include the effects of optional inputs here.

    No resource rates may be negative, unless the negative only impacts optional inputs:
      for each resource, calculate the net rate without considering optional inputs.
      Use Aub and bub for this.
    """

    res_inds = {r['alias']: i for i, r in enumerate(resources)}

    nr, nb = len(resources), len(blocks)
    rates_no_opt, rates_opt = get_rates(blocks, res_inds, nr)
    c = get_c(rates_no_opt, rates_opt, res_inds)

    return None
