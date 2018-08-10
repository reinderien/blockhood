Block'Hood Analytics
====================

Block'Hood ([home page](https://www.plethora-project.com/blockhood),
[Steam page](https://store.steampowered.com/app/416210/Blockhood)
is a city-building game by Jose Sanchez of the
[Plethora Project](http://www.plethora-project.com).

I'm unaffiliated. I bought and enjoy the game, so I wrote this application to do some analysis on its economic model.

First, this application pulls data from the community-maintained
[wiki](https://blockhood.gamepedia.com) using

- [Python](https://www.python.org) 3
- [requests](http://docs.python-requests.org)
- The [MediaWiki API](https://www.mediawiki.org/wiki/API:Main_page)

Then, it does some caching and data munging, for eventual processing by
[Numpy](http://www.numpy.org)/[Scipy](https://scipy.org).
The eventual goal is to apply a
[Dantzig linear programming solver](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html)
to explore some optimal consumption patterns - especially for something like the
[Zero Footprint Challenge](https://blockhood.gamepedia.com/Challenges#12._Zero_footprint).

Unfortunately, there are big gaps in the wiki's block pages.