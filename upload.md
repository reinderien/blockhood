Block Wiki Uploader Bot
=======================

Since we have some ~~deeply sketchy~~ perfectly serviceable block database loading code, let's do the community a favour
and update their sorely incomplete
[wiki](https://blockhood.gamepedia.com).

The HTTP transactions, as always, use [requests](http://docs.python-requests.org). They utilize GamePedia's
[MediaWiki API](https://www.mediawiki.org/wiki/API:Main_page). GamePedia uses MediaWiki 1.29.2.

To authenticate, first we need to create a password via the wiki's
[Bot Password Generator](https://blockhood.gamepedia.com/Special:BotPasswords). Its username is:

    Reinderien@block_updater

The bot has been granted:

- Basic rights
- High-volume editing
- Edit existing pages
- Create, edit and move pages

It's been granted access from my ISP's IP ranges only.

The bot uses the
[`token` query](https://www.mediawiki.org/wiki/API:Tokens) and
[`login` action](https://www.mediawiki.org/wiki/API:Login#The_login_action)
to authenticate.

The bot essentially runs these steps:

1. Do a paginated bulk load of all block pages. This takes about five calls.
2. Load blocks from the game database.
3. Merge the game database and web database using the block title.
4. Decide on what to update - stubs, missing pages, etc.
5. Upload. I couldn't find a bulk operation for this, so I just did it in a loop.

A typical run looks like:

    Loading blocks from Gamepedia...
    Processed 50 complete, 0 discontinued, 0 stubs
    Processed 99 complete, 0 discontinued, 1 stubs
    Processed 149 complete, 0 discontinued, 1 stubs
    Processed 197 complete, 0 discontinued, 3 stubs
    Processed 219 complete, 0 discontinued, 3 stubs
    
    Loading game databases... Loaded blockDB_current 785kiB, resourceDB 71kiB.
    Unpacking resource database... 78 resources.
    Unpacking block database... 241 blocks.
    
    Blocks only on the web, probably deprecated: Old Man Cactus, Gmo Cotton Field
    Blocks missing from the web: 11
    Blocks present in both: 220
    
    Editing 1/10 - Lowland Desert
    Editing 2/10 - Alpine Highland
    Editing 3/10 - Central Deciduous Forest
    Editing 4/10 - Highland Deciduous Forest
    Editing 5/10 - Central Tundra
    Editing 6/10 - Central Savanna
    Editing 7/10 - Lowland Chaparral
    Editing 8/10 - Central Desert Scrub
    Editing 9/10 - Blokcorp Hq
    Editing 10/10 - Highland Tundra
