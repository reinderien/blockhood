import numpy as np
from scipy.optimize import linprog


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
    air_weight = -1

    rates_no_opt_air = np.copy(rates_no_opt)
    rates_no_opt_air[air_index, :] *= air_weight
    rates_opt_air = np.copy(rates_opt)
    rates_opt_air[air_index, :] *= air_weight
    return np.sum(rates_opt_air, 0) + np.sum(rates_no_opt_air, 0)


def show(res, blocks, resources, rates_no_opt, rates_opt):
    print('Iterations:', res.nit)
    print('Status code:', res.status)
    print(res.message)
    print()

    print('{:25s} {:>6s}'.format('Block', 'Count'))
    print('\n'.join('{:25s} {:>6.1f}'.format(blocks[i].name, c)
                    for i, c in enumerate(res.x)
                    if c > 1e-3))
    print()

    x = np.array(res.x, ndmin=2).T
    no_opt = np.matmul(rates_no_opt, x)
    opt = np.matmul(rates_opt, x)
    print('{:15s} {:>8s} {:>8s}'.format('Resource', 'Mand', 'Opt'))
    print('\n'.join('{:15s} {:+8.2f} {:+8.2f}'
                    .format(resources[i]['alias'], rn[0], ro[0])
                    for i, (rn, ro) in enumerate(zip(no_opt, opt))
                    if abs(rn) >= 1e-2 or abs(ro) >= 1e-2))


def analyse(blocks, resources):
    """
    nb=231 blocks, nr=78 resources

    Name dims     meaning
    c    1,231    coefficients to minimize c*x
    x    231,1    independent variable - block counts - comes in return var
    Aub  78,231   upper-bound coefficients for A*x <= b
    bub  78,1     upper bound for A*x <= b, all 0
    bounds (min,max) defaults to [0, inf]                - omit this

    Block counts must not be negative: implied by default value of `bounds`
    """

    print('Calculating resource rates...')
    res_inds = {r['alias']: i for i, r in enumerate(resources)}
    nr, nb = len(resources), len(blocks)
    rates_no_opt, rates_opt = get_rates(blocks, res_inds, nr)

    print('Calculating a solution for the zero-footprint challenge...')

    # Generate as few resources as possible - except for fresh air, which should be maximized
    c = get_c(rates_no_opt, rates_opt, res_inds)

    # "upper bound of zero on mandatory negative resource generation"; i.e.
    # mandatory resource rates cannot go below zero for a sustainable economy
    Aub = -rates_no_opt
    bub = np.zeros((nr, 1))

    # total block count should not exceed something reasonable
    Aub = np.append(Aub, np.ones((1, nb)), 0)
    bub = np.append(bub, np.array(200, ndmin=2), 0)

    res = linprog(c=c, A_ub=Aub, b_ub=bub)
    show(res, blocks, resources, rates_no_opt, rates_opt)
