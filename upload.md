Block Wiki Uploader Bot
=======================

GamePedia uses MediaWiki 1.29.2.

First we need to create a password via the wiki's
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
