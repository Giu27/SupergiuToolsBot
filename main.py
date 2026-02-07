#Copyright (C) 2025  Giuseppe Caruso
import telebot, os, logging, qrcode, wikipedia, random, faker, unidecode, asyncio, aiofiles
import telebot.async_telebot as asyncTelebot
from dotenv import load_dotenv
from asynctinydb import TinyDB, Query
from telebot import types
from datetime import date
from deep_translator import GoogleTranslator
from localizations import *

class Bot_DB_Manager:
    """Class to manage Database creation and read/write operations"""
    def __init__(self, db_path : str, *tables : str):
        """Initialize the database with a path, a query and tables"""
        self.db = TinyDB(db_path)
        self.query = Query()
        self.tables = {}
        for table in tables:
            self.tables[table] = self.db.table(table)
    
    async def get_single_doc(self, table : str, condition, attribute: str = None):
        """Returns the first document found or one of its attributes. Useful when searching by a unique id"""
        doc = await db.tables[table].get(condition)
        if doc:
            if attribute: 
                try: return doc[attribute]
                except KeyError: return None
        return doc

    async def get_docs(self, table : str, condition) -> list:
        "Returns a list of all documents in  table matching a conditions"
        docs = await db.tables[table].search(condition)
        return docs

    async def contains(self, table : str, condition) -> bool:
        """Cheks if a table contains the document identified by a condition"""
        return await self.tables[table].contains(condition)

    async def upsert_values(self, table : str, data : dict, condition):
        """Upserts a dict of values"""
        await self.tables[table].upsert(data, condition)
    
    async def remove_values(self, table : str, condition):
        "Removes from a table values matching a condition"
        await self.tables[table].remove(condition)
    
    async def close(self):
        await self.db.close()

load_dotenv()

DEV_MODE = False #switches on/off the online/offline notification if testing on a database with multiple users is needed
LOG = True #switches on/off the logging of messages received by the bot

BOT_TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID"))
bot = asyncTelebot.AsyncTeleBot(BOT_TOKEN)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
os.makedirs("logs", exist_ok=True)
log_path = "logs"

db = Bot_DB_Manager("Bot_DB.JSON", "users", "banned_words", "custom_commands")

async def store_user_data(user, chat_id : int):
    """Creates and updates the user data in the database"""
    user_data = {
        "user_id" : user.id,
        "first_name" : user.first_name,
        "last_name" : user.last_name,
        "username" : user.username,
        "is_bot" : user.is_bot,
        "bot_name" : await get_botname(user.id),
        "chat_id" : chat_id,
        "commands" : await get_permission(user.id),
        "admin_status" : await get_admin(user.id),
        "exclusive_sentence" : await get_excl_sentence(user.id),
        "notifications" : await get_notification_status(user.id),
        "localization" : await get_lang(user.id),
        "gender" : await get_gender(user.id),
        "event" : await get_event(user.id)
        }
    await db.upsert_values("users", user_data, db.query.user_id == user.id)

async def check_banned_name(name : str) -> bool:
    """Return true if name is banned, false otherwise"""
    banned_words = await get_banned_words("banned")
    ultra_banned_words = await get_banned_words("ultrabanned")
    numToCh = [{'1' : 'i', '3' : 'e', '4' : 'r', '0' : 'o', '7' : 'l', '5' : 's', '$': 'e', '€':'e', 'т' : 't', 'п' : 'n', '\u03c5' : 'u', '\u0435' : 'e', 'ε' : 'e', '6' : 'g'},
                {'1' : 'i', '3' : 'e', '4' : 'a', '0' : 'o', '7' : 'l', '5' : 's', '$': 'e', '€':'e', 'т' : 't', 'п' : 'n', '\u03c5' : 'u', '\u0435' : 'e', 'ε' : 'e', '6' : 'g'}]
    for charset in numToCh:
        wordname = ""
        for char in name:
            car = char
            try:
                car = charset[char]
            except KeyError: pass
            if car == ' ': continue
            wordname += car.lower()

        if wordname in banned_words: return True
        elif wordname[::-1] in banned_words: return True

        for word in ultra_banned_words:
            if word in wordname: return True
            elif word[::-1] in wordname: return True

async def logging_procedure(message, bot_answer : str):
    """Standard logging, to a file and console, of the user and bot messages not registered by log function automatically"""
    if LOG:
        await log_and_update(message)
        logger.info(f"Bot: {bot_answer}")
        async with aiofiles.open(f"{log_path}/{message.from_user.id}.txt", "a") as log_file:
            await log_file.write(f"Bot: {bot_answer}\n")

def get_localized_string(source : str, lang : str, element : str = None) -> str:
    """Returns the string from localizations.py in localizations[source][lang] and optionally elements"""
    try:
        if element: return localizations[source][lang][element]
        return localizations[source][lang]
    except KeyError:
        try: return localizations["not_found"][lang]
        except KeyError: return localizations["not_found"]["en"]

async def permission_denied_procedure(message, error_msg : str = ""):
    """Standard procedure, whenever a user doesn't have the permission to do a certain action"""
    user = message.from_user
    lang = await get_lang(user.id)
    bot_answer = f"{get_localized_string("permission_denied", lang, "default")}\n{get_localized_string("permission_denied", lang, str(error_msg))}"
    await bot.reply_to(message, bot_answer)
    await logging_procedure(message, bot_answer)

async def send_on_off_notification(status : str):
    """Sends a notification whenever the bot turns on or off"""
    if not DEV_MODE:
        async for user in db.tables["users"]:
            bot_answer = f"{get_localized_string("notifications", await get_lang(user["user_id"]), "bot")} {status}!"
            try: 
                if user["chat_id"] and await get_notification_status(user["user_id"]):
                    await bot.send_message(user["chat_id"], bot_answer)
                    if LOG: logger.info(f"Bot: {bot_answer}. chat_id: {user["chat_id"]}")
            except (KeyError, telebot.apihelper.ApiTelegramException): pass

def generate_random_name(gender : str) -> str:
    """Return a random name between names from Italian, english, French, Ukranian, greek and japanese names"""
    langs = ["it_IT", "en_UK", "fr_Fr", "uk_UA", "el_GR", "ja_JP"]
    lang = random.choice(langs)
    fake = faker.Faker(lang)

    if lang == "ja_JP":
        if gender == 'f': name = fake.first_romanized_name_female()
        else: name = fake.first_romanized_name_male()
    else:
        if gender == 'f': name = fake.first_name_female()
        else: name = fake.first_name_male()
        name = unidecode.unidecode(name)
    return name

async def generate_qrcode(message, chat_id : int):
    """Generates a qr code from a string of text"""
    user = message.from_user
    lang = await get_lang(user.id)
    bot_answer = get_localized_string("sent", lang)
    img_path = f"qr_{user.id}.png"

    img = qrcode.make(message.text)
    img.save(img_path)
    try:
        with open(img_path, "rb") as code:
            await bot.send_photo(chat_id, code)
        os.remove(img_path)
    except Exception as e: bot_answer = f"{get_localized_string("qrcode", lang, "error")} {await get_viewed_name(OWNER_ID)}: \n{e}"
    await bot.reply_to(message, bot_answer)
    await logging_procedure(message, bot_answer)

async def validate_name(message, name : str, type : str = "name", max_chars : int = 200) -> bool:
    """Validates a name (or a sentence), return True if the name is valid"""
    user = message.from_user
    lang = await get_lang(user.id)

    if len(name) > max_chars:
        bot_answer = f"{get_localized_string("set_name", lang, "max_chars")} Max: {max_chars}"
        await bot.reply_to(message, bot_answer)
        await logging_procedure(message, bot_answer)
        return False
    
    if await check_banned_name(name):
        bot_answer = get_localized_string("set_name", lang, "name_banned") if type == "name" else get_localized_string("set_sentence", lang, "sentence_banned")
        await bot.reply_to(message, bot_answer)
        await logging_procedure(message, bot_answer)
        return False
    
    return True

async def get_botname(us_id : int) -> str | None:
    """Returns the botname of the user identified by us_id"""
    botname = await db.get_single_doc("users", db.query.user_id == us_id, "bot_name")
    if botname: 
        if await check_banned_name(botname):
            botname = None
            await db.upsert_values("users", {"bot_name" : botname}, db.query.user_id == us_id)
    return botname

async def set_botname(message, us_id : int, randomName=False):
    """Updates the botname of the user identified by us_id"""
    user = message.from_user
    name = message.text
    lang = await get_lang(user.id)
    if randomName or name == "-r": name = generate_random_name(await get_gender(us_id))
    
    if not await validate_name(message, name): return
    
    target_viewed_name = await get_viewed_name(us_id)
    if user.id == us_id: bot_answer = f"{get_localized_string("set_name", lang, "personal_name")} {name}"
    else: bot_answer = f"{get_localized_string("set_name", lang, "name_of")} {target_viewed_name} {get_localized_string("set_name", lang, "is_now")} {name}"
    await db.upsert_values("users", {"bot_name" : name}, db.query.user_id == us_id)

    await bot.reply_to(message, bot_answer)
    await logging_procedure(message, bot_answer)

async def reset_botname(message, us_id : int):
    """Reset the name of a user identified by us_id"""
    target_name = await db.get_single_doc("users", db.query.user_id == us_id, "first_name")
    user = message.from_user
    lang = await get_lang(user.id)

    await db.upsert_values("users", {"bot_name" : None}, db.query.user_id == us_id)
    bot_answer = f"{get_localized_string("set_name", lang, "name_of")} {target_name} {get_localized_string("set_name", lang, "resetted")}"

    await bot.reply_to(message, bot_answer)
    await logging_procedure(message, bot_answer)

async def get_viewed_name(us_id : int) -> str | None:
    """Returns the currently visualized name in the bot"""
    if await get_botname(us_id): user_name = await get_botname(us_id)
    else: user_name = await db.get_single_doc("users", db.query.user_id == us_id, "first_name")
    return user_name

async def get_chat_id(us_id : int) -> int | None:
    """Return the chat id stored in the database"""
    return await db.get_single_doc("users", db.query.user_id == us_id, "chat_id")

async def get_permission(us_id : int, command : str = None) -> bool | dict | str:
    """Returns true if the user can use a command, false if restricted. If no command is specified returns a dict"""
    if not await db.contains("users", db.query.user_id == us_id): return "not_found"
    commands = await db.get_single_doc("users", db.query.user_id == us_id, "commands")
    if command == None: 
        try:
            if commands != None and commands != "not_found": return commands
            else: return {}
        except KeyError: return {}
    try:
        if commands[command] != None: return commands[command]
        else: raise KeyError
    except KeyError:
        data = commands
        data[command] = True
        await db.upsert_values("users", {"commands" : data}, db.query.user_id == us_id)
        return True
    except TypeError:
        await db.upsert_values("users", {"commands" : {}}, db.query.user_id == us_id)
        return await get_permission(us_id, command)

async def set_permission(message, us_id : int):
    """Updates the status of a command for the user identified by us_id"""
    user = message.from_user
    if await get_admin(us_id) and us_id != user.id and user.id != OWNER_ID:
        await permission_denied_procedure(message, "target_admin")
        return
    
    viewed_name = await get_viewed_name(us_id)
    user = message.from_user
    lang = await get_lang(user.id)
    if await get_permission(us_id, message.text) == True: bot_answer = f"{get_localized_string("permission", lang, "permission_of")} {viewed_name} {get_localized_string("permission", lang, "locked")}"
    else: bot_answer = f"{get_localized_string("permission", lang, "permission_of")} {viewed_name} {get_localized_string("permission", lang, "unlocked")}"

    permissions = await get_permission(us_id)

    if us_id == user.id and not permissions[message.text] and us_id != OWNER_ID:
        await permission_denied_procedure(message, "admin_only")
        return

    permissions[message.text] = not await get_permission(us_id, message.text)
    await db.upsert_values("users", {"commands" : permissions}, db.query.user_id == us_id)

    await bot.reply_to(message, bot_answer, reply_markup=types.ReplyKeyboardRemove())
    await logging_procedure(message, bot_answer)

async def get_permissions_list(message, us_id : int):
    """Shows the status of all the commands that can be restricted for the user identified by us_id"""
    user = message.from_user
    lang = await get_lang(user.id)

    if await get_permission(us_id):
        bot_answer = f"{get_localized_string("permission", lang, "list")} {await get_viewed_name(us_id)}: \n"
        for command, permission in (await get_permission(us_id)).items():
            bot_answer += f"{command}: {permission};\n"
    else: bot_answer = get_localized_string("choose_argument", lang, "not_found")

    await bot.reply_to(message, bot_answer)
    await logging_procedure(message, bot_answer)

async def get_lang(us_id : int) -> str:
    """Returns the user language code, if not found defaults to en"""
    localization = await db.get_single_doc("users", db.query.user_id == us_id, "localization")
    if localization: return localization
    else: return "en"

async def set_lang(message, us_id : int):
    """Change the bot language, for the user identified by us_id, into italian or english"""
    viewed_name = await get_viewed_name(us_id)
    if await get_lang(us_id) == "it":
        bot_answer = f"{viewed_name} {get_localized_string("set_lang", "en")}"
        lang = "en"
    else:
        bot_answer = f"{viewed_name} {get_localized_string("set_lang", "it")}"
        lang = "it"

    await db.upsert_values("users", {"localization" : lang}, db.query.user_id == us_id)
    await bot.reply_to(message, bot_answer)
    await logging_procedure(message, bot_answer)

async def get_gender(us_id : int) -> str:
    """Returns the user gender, if not found defaults to m(ale)"""
    gender = await db.get_single_doc("users", db.query.user_id == us_id, "gender")
    if gender: return gender
    else: return 'm'

async def set_gender(message, us_id : int):
    """Change the gender of the name chosen by randomname, for the user identified by us_id, into male or female"""
    viewed_name = await get_viewed_name(us_id)
    user = message.from_user
    lang = await get_lang(user.id)
    if await get_gender(us_id) == 'm':
        bot_answer = f"{viewed_name} {get_localized_string("set_gender", lang, 'f')}"
        gender = 'f'
    else:
        bot_answer = f"{viewed_name} {get_localized_string("set_gender", lang, 'm')}"
        gender = 'm'
 
    await db.upsert_values("users", {"gender" : gender}, db.query.user_id == us_id)
    await bot.reply_to(message, bot_answer)
    await logging_procedure(message, bot_answer)

async def get_admin(us_id : int) -> bool:
    """Return true if the user identified by us_id is admin, false otherwise"""
    admin = await db.get_single_doc("users", db.query.user_id == us_id, "admin_status")
    if us_id == OWNER_ID and admin == None: return True
    if admin == None: return False
    return admin

async def set_admin(message, us_id : int):
    """Turn the user identified by us_id into an admin or vice versa"""
    viewed_name = await get_viewed_name(us_id)
    user = message.from_user
    lang = await get_lang(user.id)

    if await get_admin(us_id) == True: bot_answer = f"{viewed_name} {get_localized_string("set_admin", lang, "remove")}"
    else: bot_answer = f"{viewed_name} {get_localized_string("set_admin", lang, "add")}"
     
    await db.upsert_values("users", {"admin_status" : not await get_admin(us_id)}, db.query.user_id == us_id)

    await bot.reply_to(message, bot_answer)
    await logging_procedure(message, bot_answer)

async def get_notification_status(us_id : int) -> bool:
    """Returns true if the user has on/off notifications active, false otherwise"""
    notifications = await db.get_single_doc("users", db.query.user_id == us_id, "notifications")
    if notifications == None: return True
    else: return notifications

async def get_excl_sentence(us_id : int) -> str | None:
    """Returns the special sentence of the user us_id"""
    return await db.get_single_doc("users", db.query.user_id == us_id, "exclusive_sentence")

async def set_excl_sentence(message, us_id : int): 
    """Set a special sentence the user identified by us_id receives when greeted by the bot"""
    user = message.from_user
    lang = await get_lang(user.id)
    sentence = message.text
    
    if not await validate_name(message, sentence, "sentence"): return
    
    target_viewed_name = await get_viewed_name(us_id)
    if sentence.lower() == "none": sentence = None
        
    if user.id == us_id: bot_answer = f"{get_localized_string("set_sentence", lang, "personal_sentence")} {sentence}"
    else: bot_answer = f"{get_localized_string("set_sentence", lang, "sentence_of")} {target_viewed_name} {get_localized_string("set_name", lang, "is_now")} {sentence}"
            
    await db.upsert_values("users", {"exclusive_sentence" : sentence}, db.query.user_id == us_id)

    await bot.reply_to(message, bot_answer)
    await logging_procedure(message, bot_answer)

async def get_info(message, us_id : int):
    """The bot sends a message with basic user informations"""
    user_doc = await db.get_single_doc("users", db.query.user_id == us_id)
    user = message.from_user
    lang = await get_lang(user.id)

    if user_doc:
        bot_answer = f"{get_localized_string("info", lang, "name")} {user_doc["first_name"]}\n{get_localized_string("info", lang, "last_name")} {user_doc["last_name"]}\nUsername: {user_doc["username"]}\n{get_localized_string("info", lang, "user_id")} {user_doc["user_id"]}\n{get_localized_string("info", lang, "bot_name")} {await get_botname(us_id)}\n{get_localized_string("info", lang, "sentence")} {await get_excl_sentence(us_id)}\n{get_localized_string("info", lang, "language")} {await get_lang(us_id)}\n{get_localized_string("info", lang, "gender")} {await get_gender(us_id)}\n{get_localized_string("info", lang, "notification")} {await get_notification_status(us_id)}\n{get_localized_string("info", lang, "admin")} {await get_admin(us_id)}"
    else: bot_answer = get_localized_string("choose_argument", lang, "not_found")

    await bot.reply_to(message, bot_answer)
    await logging_procedure(message, bot_answer)

async def get_event(us_id : int):
    """Return the current pending event to handle for that user"""
    return await db.get_single_doc("users", db.query.user_id == us_id, "event")

async def set_event(message, next_step : callable , content = None, command : callable = None, second_arg : bool = None):
    user = message.from_user

    next_step = next_step.__name__ if not isinstance(next_step, str) else next_step
    command_name = command.__name__ if command else None
    
    await db.upsert_values("users", {"event" : {"next" : next_step, "content" : content, "command" : command_name, "second_arg" : second_arg}}, db.query.user_id == user.id)

async def send_message(message, chat_id : int, scope : str = None, acknowledge : bool = True):
    """Send a message to the chat identified by chat_id"""
    user = message.from_user
    lang = await get_lang(user.id)
    bot_answer = get_localized_string("sent", lang)
    viewed_name = await get_viewed_name(user.id)

    from_text = f"{get_localized_string("send_to", await get_lang(chat_id), "from")} {viewed_name}({user.id}):"
    if scope == 'B': from_text = f"{get_localized_string("broadcast", await get_lang(chat_id), "from")} {viewed_name}:"
    if scope == 'A': from_text = f"{get_localized_string("broadcast", await get_lang(chat_id), "admin_from")} {viewed_name}:"

    if message.content_type in ("text", "photo", "audio", "voice", "sticker", "document"):
        try:
            await bot.send_message(chat_id, from_text)
            if message.content_type == "text":
                await bot.send_message(chat_id, message.text)
            elif message.content_type == "photo":
                file_id = message.photo[-1].file_id
                caption = message.caption if message.caption else None
                await bot.send_photo(chat_id, file_id, caption)
            elif message.content_type == "audio":
                file_id = message.audio.file_id
                caption = message.caption if message.caption else None
                await bot.send_audio(chat_id, file_id, caption)
            elif message.content_type == "voice":
                file_id = message.voice.file_id
                caption = message.caption if message.caption else None
                await bot.send_voice(chat_id, file_id, caption) 
            elif message.content_type == "sticker":
                file_id = message.sticker.file_id
                await bot.send_sticker(chat_id, file_id)
            elif message.content_type == "document":
                file_id = message.document.file_id
                caption = message.caption if message.caption else None
                await bot.send_document(chat_id, file_id, caption=caption)         
        except telebot.apihelper.ApiTelegramException: bot_answer = get_localized_string("send_to", lang, "blocked")
    else: bot_answer = get_localized_string("send_to", lang, "unsupported")
        
    if acknowledge: 
        await bot.reply_to(message, bot_answer)
        await logging_procedure(message, bot_answer)

async def broadcast(message, admin_only=False):
    """Send a message to all the users of the bot, or if admin only to just the admins"""
    acknowledge = True
    async for user in db.tables["users"]:
        try: 
            if user["chat_id"]:
                if admin_only and user["admin_status"]:
                    await send_message(message, user["chat_id"], 'A', acknowledge)
                    acknowledge = False
                if not admin_only:
                    await send_message(message, user["chat_id"], 'B', acknowledge)
                    acknowledge = False
        except (KeyError, telebot.apihelper.ApiTelegramException): pass

async def ask_target(message, command : callable, second_arg : bool = True):
    """First step of the admin framework, it prompts the admin to specify the user who they're targeting with their command. The admin framework let the admins reuse the functions written for normal use in a specific admin mode"""
    user = message.from_user
    bot_answer = get_localized_string("choose_target", await get_lang(user.id))

    is_admin = await get_admin(user.id)
    if not is_admin:
        await permission_denied_procedure(message, "admin_only")
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, selective=True)
    async for user_data in db.tables["users"]:
        if user_data["username"]: button = types.KeyboardButton(user_data["username"])
        else: button = types.KeyboardButton(user_data["first_name"])
        markup.add(button)

    await bot.reply_to(message, bot_answer, reply_markup=markup)
    await set_event(message, validate_target, command=command, second_arg=second_arg)
    await logging_procedure(message, bot_answer)

async def validate_target(message, command : callable, second_arg : bool = True):
    """Checks is the name is unique, it it isn't prompts the admin to specify the id"""
    admin_user = message.from_user
    lang = await get_lang(admin_user.id)

    us_id = await db.get_single_doc("users", db.query.username == message.text, "user_id")
    if not us_id:
        user_docs = await db.get_docs("users", db.query.first_name == message.text)
        if len(user_docs) == 1: us_id = user_docs[0]["user_id"] #One user found, everything is fine
        elif len(user_docs) > 1: #Multiple users found, specify which one is the correct one!
            bot_answer = f"{get_localized_string("choose_argument", lang, "multiple_found")}"

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, selective=True)
            for user in user_docs:
                us_id = user["user_id"]
                button = types.KeyboardButton(us_id)
                markup.add(button)
                bot_answer += f"\n{us_id}:\nBotname: {get_viewed_name(us_id)}\n"
            
            await bot.reply_to(message, bot_answer, reply_markup=markup)
            await logging_procedure(message, bot_answer)
            await set_event(message, handle_multiple_users, command=command, second_arg=second_arg)
            return
        else: #No users found
            bot_answer = get_localized_string("choose_argument", lang, "not_found")
            await bot.reply_to(message, bot_answer, reply_markup=types.ReplyKeyboardRemove())
            await logging_procedure(message, bot_answer)
            return 
        
    await ask_argument(message, command, us_id, second_arg)

async def handle_multiple_users(message, command : callable, second_arg : bool = True):
    admin_user = message.from_user
    lang = await get_lang(admin_user.id)

    us_id = await db.get_single_doc("users", db.query.user_id == int(message.text), "user_id")
    if not us_id:
        bot_answer = get_localized_string("choose_argument", lang, "not_found")
        await bot.reply_to(message, bot_answer, reply_markup=types.ReplyKeyboardRemove())
        return
    
    await ask_argument(message, command, us_id, second_arg)

async def ask_argument(message, command : callable, us_id : int, second_arg : bool = True):
    """Second step of the admin framework, right after user selection. it prompts for the required text argument of certain commands"""
    admin_user = message.from_user
    lang = await get_lang(admin_user.id)
    markup = types.ReplyKeyboardRemove()

    bot_answer = f"{get_localized_string("choose_argument", lang, "selected")} {await get_viewed_name(us_id)} ({us_id}). \n{get_localized_string("choose_argument", lang, "argument")}"

    if not second_arg:
        bot_answer = f"{get_localized_string("choose_argument", lang, "selected")} {await get_viewed_name(us_id)} ({us_id})."
        await bot.reply_to(message, bot_answer, reply_markup=types.ReplyKeyboardRemove())
        await set_event(message, command, us_id)
        await handle_events(message)
        return
    
    if command == set_permission.__name__:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, selective=True)
        commands = await db.get_single_doc("users", db.query.user_id == us_id, "commands")
        if commands:
            for command_name in commands:
                button = types.KeyboardButton(command_name)
                markup.add(button)

    await bot.reply_to(message, bot_answer, reply_markup=markup)
    await set_event(message, command, content=us_id)
    await logging_procedure(message, bot_answer)

async def get_banned_words(word_type) -> list[str]:
    """Return the list of a specified type of banned world"""
    banned_list = await db.get_single_doc("banned_words", db.query.type == word_type, "list")
    if banned_list == None: banned_list = []
    return banned_list

async def add_banned_words(message, word_type : str):
    """Add a word to the banned words list"""
    word = (message.text).lower()
    user = message.from_user
    lang = await get_lang(user.id)
    banned_list = await get_banned_words(word_type)

    if word in banned_list:
        bot_answer = get_localized_string("banned_words", lang, "already_banned")
        await bot.reply_to(message, bot_answer)
        await logging_procedure(message, bot_answer)
        return
    
    banned_list.append(word)
    list_data = {"list":banned_list, "type" : word_type}
    await db.upsert_values("banned_words", list_data, db.query.type == word_type)

    bot_answer = f"{word} {get_localized_string("banned_words", lang, "banned")}"
    await bot.reply_to(message, bot_answer)
    await logging_procedure(message, bot_answer)

async def remove_banned_words(message, word_type : str):
    """Remove a word from the banned words list"""
    word = (message.text).lower()
    user = message.from_user
    lang = await get_lang(user.id)
    banned_list = await get_banned_words(word_type)

    if word in banned_list:
        banned_list.remove(word)
        bot_answer = f"{word} {get_localized_string("banned_words", lang, "unbanned")}"
        list_data = {"list":banned_list, "type" : word_type}
        await db.upsert_values("banned_words", list_data, db.query.type == word_type)

        await bot.reply_to(message, bot_answer)
        await logging_procedure(message, bot_answer)
        return
        
    bot_answer = get_localized_string("banned_words", lang, "already_unbanned")
    await bot.reply_to(message, bot_answer)
    await logging_procedure(message, bot_answer)

async def get_custom_commands_names() -> list[str]:
    """Returns a list of the dynamically created commands"""
    commands = []
    async for command in db.tables["custom_commands"]:
        commands.append(command["name"])
    return commands

async def ask_custom_command_content(message):
    """Asks the content needed to create the commands"""
    user = message.from_user
    bot_answer = get_localized_string("custom_commands", await get_lang(user.id), "add_command_content")
    markup = types.ReplyKeyboardRemove()
    
    await bot.reply_to(message, bot_answer, reply_markup=markup)
    await set_event(message, add_custom_command, content=message.text)
    await logging_procedure(message, bot_answer)

async def add_custom_command(message, name: str):
    user = message.from_user
    if message.content_type == "photo": file_id = message.photo[-1].file_id
    elif message.content_type == "audio": file_id = message.audio.file_id
    elif message.content_type == "voice": file_id = message.voice.file_id
    elif message.content_type == "sticker": file_id = message.sticker.file_id
    elif message.content_type == "document": file_id = message.document.file_id
    elif message.content_type == "text": file_id = None
    else: 
        await bot.reply_to(message, get_localized_string("send_to", await get_lang(user.id), "unsupported"))
        return

    command_data = {"content" : {"type" : message.content_type, "text" : message.text, "file_id" : file_id, "caption" : message.caption}, "name" : name.lower()}
    await db.upsert_values("custom_commands", command_data, db.query.name == name.lower())

    bot_answer = f"{name} {get_localized_string("custom_commands", await get_lang(user.id), "added")}"
    await bot.reply_to(message, bot_answer)
    await logging_procedure(message, bot_answer)

async def remove_custom_command(message):
    user = message.from_user
    markup = types.ReplyKeyboardRemove()

    if not(message.text in await get_custom_commands_names()):
        bot_answer = f"{get_localized_string("custom_commands", await get_lang(user.id), "not_found")}"
        await bot.reply_to(message, bot_answer, reply_markup=markup)
        await logging_procedure(message, bot_answer)
        return

    await db.remove_values("custom_commands", db.query.name == message.text.lower())

    bot_answer = f"{message.text} {get_localized_string("custom_commands", await get_lang(user.id), "removed")}"
    await bot.reply_to(message, bot_answer, reply_markup=markup)
    await logging_procedure(message, bot_answer)

def generate_wikipedia_event(lang):
    wikipedia.set_lang("it")
    engToIta = {"January": "gennaio", "February" : "febbraio", "March" : "marzo", "April" : "aprile", "May" : "maggio", "June" : "giugno",
                "July" : "luglio", "August" : "agosto", "September" : "settembre", "October" : "ottobre" , "November" : "novembre", "December" : "dicembre"}
    month = engToIta[date.today().strftime("%B")] 
    page_title = f"{date.today().day}_{month}"
    section_name = "Eventi"
    try:
        page = wikipedia.page(page_title)
        content = page.section(section_name)
        events_list = [line for line in content.split("\n")]
        event = random.choice(events_list)
        if lang != "it":
            translator = GoogleTranslator("it", lang)
            event = translator.translate(event)
        bot_answer = f"{event}"
    except wikipedia.exceptions.PageError:
        bot_answer = get_localized_string("wikipedia", lang, "page404")
    return bot_answer

@bot.message_handler(commands=["start", "hello"])
async def send_greets(message):
    """Greet the user with its name and a special sentence"""
    user = message.from_user
    lang = await get_lang(user.id)
    await store_user_data(user, message.chat.id) #Create or update the user's table when starting
    viewed_name = await get_viewed_name(user.id)

    if await get_excl_sentence(user.id): special_reply = f"\n{await get_excl_sentence(user.id)}"
    else: special_reply = ""
    
    bot_answer = f"{get_localized_string("greet", lang)} {viewed_name}!{special_reply}"

    await bot.reply_to(message, bot_answer)
    await logging_procedure(message, bot_answer)

@bot.message_handler(commands=["lang"])
async def set_user_lang(message):
    user = message.from_user

    has_permission = await get_permission(user.id, "lang")
    if has_permission != True:
        await permission_denied_procedure(message, has_permission)
        return
    
    await set_lang(message, user.id)

@bot.message_handler(commands=["setname"])
async def set_name(message):
    """Start the event chain to set the user's botname"""
    user = message.from_user
    bot_answer = get_localized_string("set_name", await get_lang(user.id), "prompt")

    has_permission = await get_permission(user.id, "setname")
    if has_permission != True:
        await permission_denied_procedure(message, has_permission)
        return
    
    await bot.reply_to(message, bot_answer)
    await set_event(message, set_botname, content=user.id)
    await logging_procedure(message, bot_answer)

@bot.message_handler(commands=["resetname"])
async def reset_name(message):
    """Call function to reset the user's botname."""
    user = message.from_user
    has_permission = await get_permission(user.id, "resetname")
    if has_permission != True:
        await permission_denied_procedure(message, has_permission)
        return
    
    await reset_botname(message, user.id)

@bot.message_handler(commands=["sendtoowner"])
async def send_to_owner(message):
    """Send a message to the owner of the bot"""
    user = message.from_user
    owner_name = await get_viewed_name(OWNER_ID)
    bot_answer = f"{get_localized_string("send_to", await get_lang(user.id), "user")} {owner_name}?"

    has_permission = await get_permission(user.id, "sendtoowner")
    if has_permission != True:
        await permission_denied_procedure(message, has_permission)
        return
    
    await bot.reply_to(message, bot_answer)
    await set_event(message, send_message, content=OWNER_ID)
    await logging_procedure(message, bot_answer)

@bot.message_handler(commands=["sendtoadmin"])
async def send_to_admin(message):
    """Send a message to all the admins of the bot"""
    user = message.from_user
    bot_answer = get_localized_string("send_to", await get_lang(user.id), "admins")

    has_permission = await get_permission(user.id, "sendtoadmin")
    if has_permission != True:
        await permission_denied_procedure(message, has_permission)
        return
    
    await bot.reply_to(message, bot_answer)
    await set_event(message, broadcast, content=True)
    await logging_procedure(message, bot_answer)

@bot.message_handler(commands=["eventstoday"])
async def events_on_wikipedia(message):
    """send a random event of the day from italian wikipedia"""
    user = message.from_user
    lang = await get_lang(user.id)
    loop = asyncio.get_running_loop()
    bot_answer = await loop.run_in_executor(None, generate_wikipedia_event, lang)
    await bot.reply_to(message, bot_answer)
    await logging_procedure(message, bot_answer)

@bot.message_handler(commands=["gender"])
async def set_user_gender(message):
    """Call function to set the user's gender"""
    user = message.from_user

    has_permission = await get_permission(user.id, "gender")
    if has_permission != True:
        await permission_denied_procedure(message, has_permission)
        return
    
    await set_gender(message, user.id)

@bot.message_handler(commands=["randomnumber"])
async def random_number(message):
    """Return the user a random number"""
    bot_answer = random.randrange(0, 999)
    await bot.reply_to(message, bot_answer)
    await logging_procedure(message, bot_answer)

@bot.message_handler(commands=["randomname"])
async def random_name(message):
    """Set the user a random name, also doable by using -r as argument for setname"""
    user = message.from_user
    has_permission = await get_permission(user.id, "randomname")
    if has_permission != True:
        await permission_denied_procedure(message, has_permission)
        return
    
    await set_botname(message, user.id, True)

@bot.message_handler(commands=["qrcode"])
async def request_qrcode(message):
    user = message.from_user
    chat_id = await get_chat_id(user.id)
    has_permission = await get_permission(user.id, "qrcode")
    if has_permission != True:
        await permission_denied_procedure(message, has_permission)
        return
    
    bot_answer = get_localized_string("qrcode", await get_lang(user.id), "msg_to_send")
    await bot.reply_to(message, bot_answer)
    await set_event(message, generate_qrcode, content=chat_id)
    await logging_procedure(message, bot_answer)

@bot.message_handler(commands=["notifications"])
async def set_notifications(message):
    user = message.from_user
    lang = await get_lang(user.id)
    
    if not await db.contains("users", db.query.user_id == user.id):
        await permission_denied_procedure(message, "not_found")
        return

    if await get_notification_status(user.id): bot_answer = get_localized_string("notifications", lang, "off")
    else: bot_answer = get_localized_string("notifications", lang, "on")

    await db.upsert_values("users", {"notifications" : not await get_notification_status(user.id)}, db.query.user_id == user.id)
    await bot.reply_to(message, bot_answer)

    await logging_procedure(message, bot_answer)

@bot.message_handler(commands=["info"])
async def info(message):
    user = message.from_user
    await get_info(message, user.id)

@bot.message_handler(commands=["permissionlist"])
async def permissions_list(message):
    """Return the user a list with all the commands they can and can't use"""
    user = message.from_user
    await get_permissions_list(message, user.id)

@bot.message_handler(commands=["cancel"])
async def cancel_command(message, reply=True):
    user = message.from_user
    markup = types.ReplyKeyboardRemove()
    await db.upsert_values("users", {"event" : None}, db.query.user_id == user.id)

    if reply:
        bot_answer = get_localized_string("cancel", await get_lang(user.id))
        await bot.reply_to(message, bot_answer, reply_markup=markup)
        await logging_procedure(message, bot_answer)

@bot.message_handler(commands=["about"])
async def about(message):
    """Return a sponsor to myself, really"""
    user = message.from_user
    markup = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton("Github", url="github.com/Giu27/SupergiuToolsBot")
    markup.row(button)
    bot_answer = get_localized_string("about", await get_lang(user.id))
    await bot.reply_to(message, bot_answer, reply_markup=markup)
    await logging_procedure(message, bot_answer)

#Admin version of the commands above + extra
@bot.message_handler(commands=["getpersoninfo"])
async def get_person_info(message):
    await ask_target(message, get_info, False)

@bot.message_handler(commands=["setpersonname"])
async def set_person_name(message):
    user = message.from_user
    has_permission = await get_permission(user.id, "setpersonname")
    if not has_permission:
        await permission_denied_procedure(message, "admin_only")
        return
    
    await ask_target(message, set_botname)

@bot.message_handler(commands=["resetpersonname"])
async def reset_person_name(message):
    user = message.from_user
    has_permission = await get_permission(user.id, "resetpersonname")
    if not has_permission:
        await permission_denied_procedure(message, "admin_only")
        return
    
    await ask_target(message, reset_botname, False)

@bot.message_handler(commands=["setpersonpermission"])
async def set_person_permission(message):
    user = message.from_user
    has_permission = await get_permission(user.id, "setpersonpermission")
    if not has_permission:
        await permission_denied_procedure(message, "admin_only")
        return
    
    await ask_target(message, set_permission)

@bot.message_handler(commands=["getpersonpermission"])
async def get_person_permissions(message):
    user = message.from_user
    has_permission = await get_permission(user.id, "getpersonpermission")
    if not has_permission:
        await permission_denied_procedure(message, "admin_only")
        return
    await ask_target(message, get_permissions_list, False)

@bot.message_handler(commands=["setpersonadmin"])
async def set_person_admin(message):
    """Adds an admin to the bot"""
    user = message.from_user
    if user.id != OWNER_ID:
        await permission_denied_procedure(message, "owner_only")
        return
    await ask_target(message, set_admin, False)

@bot.message_handler(commands=["setpersonsentence"])
async def set_person_sentence(message):
    """Gives a personal sentence easter egg to a user"""
    user = message.from_user
    has_permission = await get_permission(user.id, "setpersonsentence")
    if not has_permission:
        await permission_denied_procedure(message, "admin_only")
        return
    
    await ask_target(message, set_excl_sentence)

@bot.message_handler(commands=["setpersonlang"])
async def set_person_lang(message):
    user = message.from_user
    has_permission = await get_permission(user.id, "setpersonlang")
    if not has_permission:
        await permission_denied_procedure(message, "admin_only")
        return
    
    await ask_target(message, set_lang, False)

@bot.message_handler(commands=["setpersongender"])
async def set_person_gender(message):
    user = message.from_user
    has_permission = await get_permission(user.id, "setpersongender")
    if not has_permission:
        await permission_denied_procedure(message, "admin_only")
        return
    
    await ask_target(message, set_gender, False)

@bot.message_handler(commands=["getids"])
async def get_ids(message):
    """Returns a list with all the bot users"""
    user = message.from_user
    bot_answer = ""

    is_admin = await get_admin(user.id)
    if not is_admin:
        await permission_denied_procedure(message, "admin_only")
        return
    
    async for user in db.tables["users"]:
        try: 
            if user["user_id"]: bot_answer += f"\n\n{user["user_id"]}: {user["first_name"]} {user["last_name"]}\nBotname: {await get_botname(user["user_id"])}"
        except KeyError: pass

    await bot.reply_to(message, bot_answer)
    await logging_procedure(message, bot_answer.lstrip())

@bot.message_handler(commands=["sendto"])
async def send_to_target(message):
    user = message.from_user
    has_permission = await get_permission(user.id, "sendto")
    if not has_permission:
        await permission_denied_procedure(message, "admin_only")
        return
    
    await ask_target(message, send_message)

@bot.message_handler(commands=["broadcast"])
async def send_in_broadcast(message):
    """Event chain to send a message in broadcast"""
    user = message.from_user
    bot_answer = get_localized_string("broadcast", await get_lang(user.id), "msg_to_send")

    is_admin = await get_admin(user.id)
    has_permission = await get_permission(user.id, "broadcast")
    if not is_admin or not has_permission:
        await permission_denied_procedure(message, "admin_only")
        return
    
    await bot.reply_to(message, bot_answer)
    await set_event(message, broadcast)
    await logging_procedure(message, bot_answer)

#banned words events
@bot.message_handler(commands=["addbanned"])
async def add_banned(message):
    user = message.from_user
    bot_answer = get_localized_string("banned_words", await get_lang(user.id), "add_banned")

    is_admin = await get_admin(user.id)
    has_permission = await get_permission(user.id, "addbanned")
    if not is_admin or not has_permission:
        await permission_denied_procedure(message, "admin_only")
        return
    
    await bot.reply_to(message, bot_answer)
    await set_event(message, add_banned_words, content="banned")
    await logging_procedure(message, bot_answer)

@bot.message_handler(commands=["removebanned"])
async def remove_banned(message):
    user = message.from_user
    bot_answer = get_localized_string("banned_words", await get_lang(user.id), "remove_banned")

    is_admin = await get_admin(user.id)
    has_permission = await get_permission(user.id, "removebanned")
    if not is_admin or not has_permission:
        await permission_denied_procedure(message, "admin_only")
        return
    
    await bot.reply_to(message, bot_answer)
    await set_event(message, remove_banned_words, content="banned")
    await logging_procedure(message, bot_answer)

@bot.message_handler(commands=["addultrabanned"])
async def add_ultra_banned(message):
    user = message.from_user
    bot_answer = get_localized_string("banned_words", await get_lang(user.id), "add_ultrabanned")

    is_admin = await get_admin(user.id)
    has_permission = await get_permission(user.id, "addbanned")
    if not is_admin or not has_permission:
        await permission_denied_procedure(message, "admin_only")
        return
    
    await bot.reply_to(message, bot_answer)
    await set_event(message, add_banned_words, content="ultrabanned")
    await logging_procedure(message, bot_answer)

@bot.message_handler(commands=["removeultrabanned"])
async def remove_ultra_banned(message):
    user = message.from_user
    bot_answer = get_localized_string("banned_words", await get_lang(user.id), "remove_banned")

    is_admin = await get_admin(user.id)
    has_permission = await get_permission(user.id, "removebanned")
    if not is_admin or not has_permission:
        await permission_denied_procedure(message, "admin_only")
        return
    
    await bot.reply_to(message, bot_answer)
    await set_event(message, remove_banned_words, content="ultrabanned")
    await logging_procedure(message, bot_answer)

#custom commands events
@bot.message_handler(commands=["getcommandslist"])
async def get_command_list(message):
    user = message.from_user
    is_admin = await get_admin(user.id)

    if not is_admin:
        await permission_denied_procedure(message, "admin_only")
        return

    bot_answer = get_localized_string("custom_commands", await get_lang(user.id), "list")
    for command in await get_custom_commands_names():
        bot_answer += (f"\n{command}")

    await bot.reply_to(message, bot_answer)
    await logging_procedure(message, bot_answer)

@bot.message_handler(commands=["addcommand"])
async def add_command(message):
    user = message.from_user
    bot_answer = get_localized_string("custom_commands", await get_lang(user.id), "add_command")

    is_admin = await get_admin(user.id)
    has_permission = await get_permission(user.id, "addcommand")
    if not is_admin or not has_permission:
        await permission_denied_procedure(message, "admin_only")
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, selective=True)
    for command in await get_custom_commands_names():
        button = types.KeyboardButton(command)
        markup.add(button)
    
    await bot.reply_to(message, bot_answer, reply_markup=markup)
    await set_event(message, ask_custom_command_content)
    await logging_procedure(message, bot_answer)

@bot.message_handler(commands=["removecommand"])
async def remove_command(message):
    user = message.from_user
    bot_answer = get_localized_string("custom_commands", await get_lang(user.id), "remove_command")

    is_admin = await get_admin(user.id)
    has_permission = await get_permission(user.id, "addcommand")
    if not is_admin or not has_permission:
        await permission_denied_procedure(message, "admin_only")
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, selective=True)
    for command in await get_custom_commands_names():
        button = types.KeyboardButton(command)
        markup.add(button)
    
    await bot.reply_to(message, bot_answer, reply_markup=markup)
    await set_event(message, remove_custom_command)
    await logging_procedure(message, bot_answer)

@bot.message_handler(func= lambda message: message.text.startswith('/'))
async def handle_custom_commands(message):
    """Handle dynamically generated commands"""
    user = message.from_user
    command = message.text[1:]
    if command in await get_custom_commands_names():
        has_permission = await get_permission(user.id, command)
        if not has_permission:
            await permission_denied_procedure(message, has_permission)
            return
        
        message_data = await db.get_single_doc("custom_commands", db.query.name == command, "content")
        if message_data["type"] == "text": await bot.send_message(message.chat.id, message_data["text"])
        elif message_data["type"] == "photo": await bot.send_photo(message.chat.id, message_data["file_id"], message_data["caption"])
        elif message_data["type"] == "audio": await bot.send_audio(message.chat.id, message_data["file_id"], message_data["caption"])
        elif message_data["type"] == "voice": await bot.send_voice(message.chat.id, message_data["file_id"], message_data["caption"])
        elif message_data["type"] == "sticker": await bot.send_sticker(message.chat.id, message_data["file_id"])
        elif message_data["type"] == "document": await bot.send_document(message.chat.id, message_data["file_id"], caption=message_data["caption"])
        else: await bot.reply_to(message, get_localized_string("send_to", get_lang(user.id), "unsupported"))

        if message_data["type"] == "text": content = message_data["text"]
        else: content = message_data["type"]
        await logging_procedure(message, content)
    else: await log_and_update(message)

#General handlers
@bot.message_handler(content_types=["text","photo", "video", "sticker", "animation", "document", "audio", "voice"],func= lambda commands:True)
async def handle_events(message):
    user = message.from_user
    await store_user_data(user, message.chat.id)

    functions = {"validate_target" : validate_target, "set_botname" : set_botname, "send_message" : send_message, "broadcast" : broadcast, "generate_qrcode" : generate_qrcode, "reset_botname" : reset_botname,
                 "ask_custom_command_content" : ask_custom_command_content, "add_custom_command" : add_custom_command, "remove_custom_command" : remove_custom_command, "set_excl_sentence" : set_excl_sentence,
                 "set_permission" : set_permission, "set_lang" : set_lang, "set_gender" : set_gender, "get_info" : get_info, "get_permissions_list" : get_permissions_list, "set_admin" : set_admin,
                 "add_banned_words" : add_banned_words, "remove_banned_words" : remove_banned_words}
    event = await get_event(user.id)

    if event:
        await cancel_command(message, False)
        if event["command"]:
            await functions[event["next"]](message, event["command"], event["second_arg"])
        elif event["content"]:
           await functions[event["next"]](message, event["content"]) 
        else: await functions[event["next"]](message)
    
    else: 
        if message.text == None: await handle_media(message)
        else: await log_and_update(message)

async def handle_media(message):
    user = message.from_user
    lang = await get_lang(user.id)

    bot_answer = f"{get_localized_string("greet", lang)} {await get_viewed_name(user.id)}, {get_localized_string("handle_media", lang, "image")}"
    if (message.voice or message.audio): bot_answer = f"{get_localized_string("greet", lang)} {await get_viewed_name(user.id)}, {get_localized_string("handle_media", lang, "audio")}"

    await bot.reply_to(message, bot_answer)
    await logging_procedure(message, bot_answer)

async def log_and_update(message):
    """Logs messages and updates the database"""
    user = message.from_user
    await store_user_data(user, message.chat.id)

    if LOG:
        if user.username: user_info = user.username
        else: user_info = f"{user.first_name} {user.last_name}"

        if message.content_type == "text": content = message.text
        else: content = message.content_type

        logger.info(f"{user.id}, {user_info}: {content}")
        async with aiofiles.open(f"{log_path}/{user.id}.txt", "a") as log_file:
            await log_file.write(f"{user.id}, {user_info}: {content}\n")

async def main():
    await bot.set_my_commands(commands_en) #default
    await bot.set_my_commands(commands_it, language_code="it")

    await send_on_off_notification("online")

    await bot.polling()

    await send_on_off_notification("offline")

    await db.close()
    await bot.close_session()

if __name__ == "__main__":
    asyncio.run(main())