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


def get_c(rates_no_opt, rates_opt, air_index, wild_index):
    # Calculate c: sum opt and no_opt to eliminate resources dimension

    # Fresh air counts against cost, not toward it
    rates_no_opt_c = np.copy(rates_no_opt)
    rates_no_opt_c[air_index, :] *= -1
    rates_opt_c = np.copy(rates_opt)
    rates_opt_c[air_index, :] *= -1

    # Apparently wilderness does not count toward or against us as a resource
    rates_no_opt_c[wild_index, :] = 0
    rates_opt_c[wild_index, :] = 0

    return np.sum(rates_opt_c, 0) + np.sum(rates_no_opt_c, 0)


def get_limits(rates_no_opt, rates_opt, air_index, wild_index, money_index, nr, nb):
    min_air = 500
    max_res = 50      # Actually 80 but let's be safe
    init_money = 150

    a_lower_rates = rates_no_opt              # Only mandatory rates influence minima
    b_lower_rates = np.zeros((nr, 1))         # Minimum rate for most resources is 0
    b_lower_rates[air_index] = min_air        # Lowest fresh air allowable
    b_lower_rates[money_index] = -init_money  # Lowest rate of money - left with nothing

    a_upper_rates = rates_no_opt + rates_opt   # Allow opt inputs to help rate maxima
    b_upper_rates = np.full((nr, 1), max_res)  # Upper rate for most resources is 80
    b_upper_rates[money_index] -= init_money   # Most amount of money left at end is 80

    # Neither fresh air nor wilderness have maxima
    a_upper_rates = np.delete(a_upper_rates, (air_index, wild_index), 0)
    b_upper_rates = np.delete(b_upper_rates, (air_index, wild_index), 0)

    a_upper_blocks = np.ones((1, nb))        # Count all blocks
    b_upper_blocks = np.array(500, ndmin=2)  # Choose some reasonable maximum

    # Lower bounds must be negated
    a_upper = np.append(-a_lower_rates,
              np.append(a_upper_rates, a_upper_blocks, 0), 0)
    b_upper = np.append(-b_lower_rates,
              np.append(b_upper_rates, b_upper_blocks, 0), 0)
    return a_upper, b_upper


def show(res, blocks, resources, rates_no_opt, rates_opt):
    print('Iterations:', res.nit)
    print(res.message)
    print()
    if res.status != 0:
        return

    print('{:20s} {:>6s}'.format('Block', 'Count'))
    print('\n'.join('{:20s} {:>6.1f}'.format(blocks[i].name, c)
                    for i, c in enumerate(res.x)
                    if abs(c) >= 0.1))
    print()

    x = np.array(res.x, ndmin=2).T
    no_opt = np.matmul(rates_no_opt, x)
    opt = np.matmul(rates_opt, x)
    print('{:15s} {:>8s} {:>8s}'.format('Resource', 'Mand', 'Opt'))
    print('\n'.join('{:15s} {:8.2f} {:8.2f}'
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

    print('Calculating a solution for the zero-footprint challenge...')

    res_inds = {r['alias']: i for i, r in enumerate(resources)}
    air_index = res_inds['FRESH AIR']
    wild_index = res_inds['WILDERNESS']
    money_index = res_inds['MONEY']
    nr, nb = len(resources), len(blocks)
    rates_no_opt, rates_opt = get_rates(blocks, res_inds, nr)

    # Generate as few resources as possible - except for fresh air, which should be maximized
    c = get_c(rates_no_opt, rates_opt, air_index, wild_index)

    aub, bub = get_limits(rates_no_opt, rates_opt, air_index, wild_index, money_index, nr, nb)

    # Interior point converges much faster for this problem than simplex, which isn't surprising considering that it
    # "is intended to provide a faster and more reliable alternative to simplex, especially for large, sparse problems."
    res = linprog(c=c, A_ub=aub, b_ub=bub, method='interior-point')
    show(res, blocks, resources, rates_no_opt, rates_opt)
