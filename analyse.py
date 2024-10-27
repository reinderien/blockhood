import typing

import numpy as np
import scipy.optimize
from scipy.optimize import linprog


min_air = 500
max_res = 40             # Actually 80 but let's be safe
init_money = 150         # Needs to be below 80 at the end
max_area = 8**2
max_vol = max_area * 10  # include height
rate_units = 20          # rates are in resource per 20s


class Analyse:
    """
    nb=173 blocks, nr=78 resources

    Name dims     meaning
    c    1,173    coefficients to minimize c*x
    x    173,1    independent variable - block counts - comes in return var
    Aub  78,173   upper-bound coefficients for A*x <= b
    bub  78,1     upper bound for A*x <= b, all 0
    bounds (min,max) defaults to [0, inf]                - omit this

    Block counts must not be negative: implied by default value of `bounds`
    """

    def __init__(
        self,
        blocks: typing.Sequence[dict[str, typing.Any]],
        resources: typing.Sequence[dict[str, typing.Any]],
    ) -> None:
        self.resources, self.blocks = resources, blocks
        self.res_inds = {r['alias']: i for i, r in enumerate(resources)}
        self.air_index = self.res_inds['FRESH AIR']
        self.wild_index = self.res_inds['WILDERNESS']
        self.money_index = self.res_inds['MONEY']
        self.nr, self.nb = len(resources), len(blocks)
        self.rates_no_opt, self.rates_opt = self._get_rates()

        # Generate as few resources as possible - except for fresh air, which should be maximized
        self.c = self._get_c()
        self.aub, self.bub = self._get_bounds()

    def _get_rates(self) -> tuple[np.ndarray, np.ndarray]:
        rates_no_opt = np.empty((self.nr, 0))          # Resource rates without optionals
        rates_opt = np.empty((self.nr, 0))             # Optional rates

        for b, block in enumerate(self.blocks):
            nocol = np.zeros((self.nr, 1))             # Column of mandatory rates for this block
            opcol = np.zeros((self.nr, 1))             # Column of optional rates for this block

            for res, qty in block['inputs'].items():
                nocol[self.res_inds[res]] -= qty
            for res, qty in block['optionalInputs'].items():
                opcol[self.res_inds[res]] -= qty
            for res, qty in block['outputs'].items():
                if qty < 0:
                    col = opcol
                else:
                    col = nocol
                col[self.res_inds[res]] += qty

            rates_no_opt = np.append(rates_no_opt, nocol, 1)
            rates_opt = np.append(rates_opt, opcol, 1)
        return rates_no_opt, rates_opt

    def _get_c(self) -> float:
        rates = self.rates_no_opt + self.rates_opt
        rates[self.air_index, :] *= -1  # Air production counts against cost
        rates[self.wild_index, :] = 0   # Wilderness does not count at all
        rates[self.money_index, :] = 0  # Money merit is non-linear so don't weigh it here
        return rates.sum(axis=0)

    def _get_bounds(self) -> tuple[np.ndarray, np.ndarray]:
        a_lower_rates = self.rates_no_opt              # Only mandatory rates influence minima
        b_lower_rates = np.zeros((self.nr, 1))         # Minimum rate for most resources is 0
        b_lower_rates[self.air_index] = min_air        # Lowest fresh air allowable
        b_lower_rates[self.money_index] = -init_money  # Lowest rate of money - left with nothing

        a_upper_rates = self.rates_no_opt + self.rates_opt  # Allow opt inputs to help rate maxima
        b_upper_rates = np.full((self.nr, 1), max_res)      # Upper rate for most resources is 80
        b_upper_rates[self.money_index] -= init_money       # Most amount of money left at end is 80

        # Neither fresh air nor wilderness have maxima
        a_upper_rates = np.delete(a_upper_rates, (self.air_index, self.wild_index), 0)
        b_upper_rates = np.delete(b_upper_rates, (self.air_index, self.wild_index), 0)

        # The map is an 8x8 x 10 grid. As such, there is an upper bound on the block count.
        a_upper_count = np.ones((1, self.nb))
        b_upper_count = np.array(max_vol, ndmin=2)

        # Lower bounds must be negated
        a_upper = np.append(-a_lower_rates,
                  np.append(a_upper_rates, a_upper_count, 0), 0)
        b_upper = np.append(-b_lower_rates,
                  np.append(b_upper_rates, b_upper_count, 0), 0)
        return a_upper, b_upper

    def _show(self, res: scipy.optimize.OptimizeResult) -> None:
        print('Iterations:', res.nit)
        print(res.message)
        print()
        if res.status != 0:
            return

        block_counts = res.x
        n_blocks = sum(block_counts)
        norm_block_counts = block_counts * max_area/n_blocks
        round_block_counts = np.around(norm_block_counts)

        print('Block count: optimized count, area-normalized, rounded:')
        print('{:20s} {:>6s} {:>6s} {:>6s}'.format('Block', 'N', 'NormN', 'Round'))
        print('\n'.join('{:20s} {:>6.1f} {:>6.1f} {:>6d}'.format(self.blocks[i]['toolTipHeader'], c,n,int(r))
                        for i, (c,n,r) in enumerate(zip(block_counts, norm_block_counts, round_block_counts))
                        if c > 0.01))
        print()

        xr = np.array(round_block_counts, ndmin=2).T
        nr = np.matmul(self.rates_no_opt, xr) / rate_units
        oR = np.matmul(self.rates_opt, xr) / rate_units
        time = min_air/nr[self.air_index]

        init = np.zeros((self.nr, 1))
        init[self.money_index] = init_money
        # Final amounts won't go lower than zero if optional inputs drain them
        reff = []
        for n,o in zip(nr, oR):
            n,o = n[0], o[0]
            if o > 0 or n > -o:
                r = n + o
            elif n > 0:
                r = 0
            else:
                r = n
            reff.append(r)
        xwin = init + time*np.array(reff, ndmin=2).T

        print('After normalizing and rounding,')
        print('Resource production rate, mandatory/optional; count at win:')
        print('{:15s} {:>8s} {:>8s} {:>8s}'.format('Resource', 'Mand', 'Opt', 'Win'))
        print('\n'.join('{:15s} {:8.2f} {:8.2f} {:8.1f}'
                        .format(self.resources[i]['alias'], *(v[0] for v in vals))
                        for i, vals in enumerate(zip(nr, oR, xwin))
                        if any(abs(v[0]) >= 1e-3 for v in vals)))
        print()

        print('Number of blocks: %d' % sum(xr))
        print('Time to win (s): %.1f' % time)

    def analyse(self) -> None:
        print('Calculating a solution for the zero-footprint challenge...')

        # Interior point converges much faster for this problem than simplex, which isn't surprising considering that it
        # "is intended to provide a faster and more reliable alternative to simplex, especially for large, sparse
        # problems."
        res = linprog(c=self.c, A_ub=self.aub, b_ub=self.bub, method='interior-point')
        self._show(res)
