# SupergiuToolsBot
Bot I made in my free time out of boredom and willingness to learn.

## What can the user do?
The bot is pretty general and doesn't really do much specific, leaving room for extension and customization.

By default, users are able to choose a name to use in the bots, contact the owner or all the admins, get an event that happened on this day and generate a QR Code from text (and text only)

# Warning!
Messages sent to the bot can be logged for development purpose!

## What can admins do?
Admins (based on privilege) can interact with some user info, ban certain names, revoke certain user's rights, send messages to a user or to all in broadcast. Also, custom commands that do not require interactions can be created from the bot itself!

## How can I use the bot code for my own bot?
The bot is saved as a class, so just import it and pass to it the required information: Token, Owner's id and the database path.

Optionally other parameters are editable, like the list of selectable languages, the commands list or the texts even.

# License
Based on PyTelegramBotApi (Telebot), sharing the same GNU GPL 2.0.

Also, the bot makes use of the following libraries:

* [qrcode](https://pypi.org/project/qrcode/) 
* [wikipedia](https://pypi.org/project/wikipedia/)
* [faker](https://pypi.org/project/Faker/)
* [unidecode](https://pypi.org/project/Unidecode/)
* [aiofiles](https://pypi.org/project/aiofiles/)
* [asynctinydb](https://pypi.org/project/async-tinydb/)
* [deep_translator](https://pypi.org/project/deep-translator/)