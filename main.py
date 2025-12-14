import telebot, os, logging, qrcode, wikipedia, random, faker, unidecode
from dotenv import load_dotenv
from tinydb import TinyDB, Query
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
    
    def get_single_doc(self, table : str, condition, attribute: str = None):
        """Returns the first document found or one of its attributes. Useful when searching by a unique id"""
        doc = db.tables[table].get(condition)
        if doc:
            if attribute: 
                try: return doc[attribute]
                except KeyError: return None
        return doc

    def get_docs(self, table : str, condition) -> list:
        "Returns a list of all documents in  table matching a conditions"
        docs = db.tables[table].search(condition)
        return docs

    def contains(self, table : str, condition) -> bool:
        """Cheks if a table contains the document identified by a condition"""
        return self.tables[table].contains(condition)

    def upsert_values(self, table : str, data : dict, condition):
        """Upserts a dict of values"""
        self.tables[table].upsert(data, condition)
    
    def remove_values(self, table : str, condition):
        "Removes from a table values matching a condition"
        self.tables[table].remove(condition)
    
    def close(self):
        self.db.close()

load_dotenv()

DEV_MODE = False #switches on/off the online/offline notification if testing on a database with multiple users is needed
LOG = False #switches on/off the logging of messages received by the bot

BOT_TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID"))
bot = telebot.TeleBot(BOT_TOKEN)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
os.makedirs("logs", exist_ok=True)
log_path = "logs"

db = Bot_DB_Manager("Bot_DB.JSON", "users", "banned_words", "custom_commands")

def store_user_data(user, chat_id : int):
    """Creates and updates the user data in the database"""
    user_data = {
        "user_id" : user.id,
        "first_name" : user.first_name,
        "last_name" : user.last_name,
        "username" : user.username,
        "is_bot" : user.is_bot,
        "bot_name" : get_botname(user.id),
        "chat_id" : chat_id,
        "commands" : get_permission(user.id),
        "admin_status" : get_admin(user.id),
        "exclusive_sentence" : get_excl_sentence(user.id),
        "notifications" : get_notification_status(user.id),
        "localization" : get_lang(user.id),
        "gender" : get_gender(user.id)
        }
    db.upsert_values("users",user_data, db.query.user_id == user.id)

def check_banned_name(name : str) -> bool:
    """Return true if name is banned, false otherwise"""
    banned_words = get_banned_words("banned")
    ultra_banned_words = get_banned_words("ultrabanned")
    numToCh = [{'1' : 'i','3' : 'e','4' : 'r', '0' : 'o', '7' : 'l', '5' : 's','$': 'e','€':'e','т' : 't', 'п' : 'n', '\u03c5' : 'u', '\u0435' : 'e', 'ε' : 'e'},
                {'1' : 'i','3' : 'e','4' : 'a', '0' : 'o', '7' : 'l', '5' : 's','$': 'e','€':'e','т' : 't','п' : 'n', '\u03c5' : 'u', '\u0435' : 'e', 'ε' : 'e'}]
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

def logging_procedure(message, bot_answer : str):
    """Standard logging, to a file and console, of the user and bot messages not registered by log function"""
    if LOG:
        log_file = open(f"{log_path}/{message.from_user.id}.txt","a")
        log_and_update(message)
        logger.info(f"Bot: {bot_answer}")
        log_file.write(f"Bot: {bot_answer}\n")

def get_localized_string(source : str, lang : str, element : str = None):
    """Returns the string from localizations.py in localizations[source][lang] and optionally elements"""
    try:
        if element: return localizations[source][lang][element]
        return localizations[source][lang]
    except KeyError:
        try: return localizations["not_found"][lang]
        except KeyError: return localizations["not_found"]["en"]

def permission_denied_procedure(message, error_msg : str = ""):
    """Standard procedure, whenever a user doesn't have the permission to do a certain action"""
    user = message.from_user
    lang = get_lang(user.id)
    bot_answer = f"{get_localized_string("permission_denied",lang,"default")}\n{get_localized_string("permission_denied",lang,str(error_msg))}"
    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer)

def send_on_off_notification(status : str):
    """Sends a notification whenever the bot turns on or off"""
    if not DEV_MODE:
        for user in db.tables["users"]:
            bot_answer = f"{get_localized_string("notifications",get_lang(user["user_id"]),"bot")} {status}!"
            try: 
                if user["chat_id"] and get_notification_status(user["user_id"]):
                    bot.send_message(user["chat_id"], bot_answer)
                    if LOG: logger.info(f"Bot: {bot_answer}. chat_id: {user["chat_id"]}")
            except (KeyError, telebot.apihelper.ApiTelegramException): pass

def generate_random_name(gender : str) -> str:
    """Return a random name between names from Italian, english, French, Ukranian, greek and japanese names"""
    langs = ["it_IT", "en_UK", "fr_Fr","uk_UA","el_GR","ja_JP"]
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

def generate_qrcode(message,chat_id):
    """Generates a qr code from a string of text"""
    user = message.from_user
    lang = get_lang(user.id)
    bot_answer = get_localized_string("sent",lang)
    img_path = f"qr_{user.id}.png"

    img = qrcode.make(message.text)
    img.save(img_path)
    try:
        with open(img_path, "rb") as code:
            bot.send_photo(chat_id,code)
        os.remove(img_path)
    except Exception as e: bot_answer = f"{get_localized_string("qrcode",lang,"error")} {get_viewed_name(OWNER_ID)}: \n{e}"
    bot.reply_to(message, bot_answer)
    logging_procedure(message,bot_answer)

def validate_name(message, name : str, type : str = "name", max_chars : int = 200):
    """Validates a name (or a sentence), return True if the name is valid"""
    user = message.from_user
    lang = get_lang(user.id)

    if len(name) > max_chars:
        bot_answer = f"{get_localized_string("set_name",lang,"max_chars")} Max: {max_chars}"
        bot.reply_to(message,bot_answer)
        logging_procedure(message,bot_answer)
        return False
    
    if check_banned_name(name):
        bot_answer = get_localized_string("set_name",lang,"name_banned") if type == "name" else get_localized_string("set_sentence",lang,"sentence_banned")
        bot.reply_to(message,bot_answer)
        logging_procedure(message,bot_answer)
        return False
    
    return True

def get_botname(us_id : int) -> str | None:
    """Returns the botname of the user identified by us_id"""
    botname = db.get_single_doc("users", db.query.user_id == us_id, "bot_name")
    if botname: 
        if check_banned_name(botname):
            botname = None
            db.upsert_values("users", {"bot_name" : botname}, db.query.user_id == us_id)
    return botname

def set_botname(message, us_id : int, randomName=False):
    """Updates the botname of the user identified by us_id"""
    user = message.from_user
    name = message.text
    lang = get_lang(user.id)
    if randomName or name == "-r": name = generate_random_name(get_gender(us_id))
    
    if not validate_name(message, name): return
    
    target_viewed_name = get_viewed_name(us_id)
    if user.id == us_id: bot_answer = f"{get_localized_string("set_name",lang,"personal_name")} {name}"
    else: bot_answer = f"{get_localized_string("set_name",lang,"name_of")} {target_viewed_name} {get_localized_string("set_name",lang,"is_now")} {name}"
    db.upsert_values("users", {"bot_name" : name}, db.query.user_id == us_id)

    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer)

def reset_botname(message, us_id : int):
    """Reset the name of a user identified by us_id"""
    user_doc = db.get_single_doc("users", db.query.user_id == us_id)
    user = message.from_user
    lang = get_lang(user.id)
    if user_doc:
        target_name = user_doc["first_name"]
        db.upsert_values("users", {"bot_name" : None}, db.query.user_id == us_id)
        bot_answer = f"{get_localized_string("set_name",lang,"name_of")} {target_name} {get_localized_string("set_name",lang,"resetted")}"

    else: bot_answer = get_localized_string("choose_argument",lang,"not_found")
    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer)

def get_viewed_name(us_id : int) -> str | None:
    """Returns the currently visualized name in the bot"""
    if get_botname(us_id): user_name = get_botname(us_id)
    else: user_name = db.get_single_doc("users", db.query.user_id == us_id, "first_name")
    return user_name

def get_chat_id(us_id : int) -> int | None:
    """Return the chat id stored in the database"""
    return db.get_single_doc("users", db.query.user_id == us_id, "chat_id")

def get_permission(us_id : int, command : str = None) -> bool | dict | str:
    """Returns true if the user can use a command, false if restricted. If no command is specified returns a dict"""
    if not db.contains("users", db.query.user_id == us_id): return "not_found"
    commands = db.get_single_doc("users", db.query.user_id == us_id, "commands")
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
        db.upsert_values("users", {"commands" : data}, db.query.user_id == us_id)
        return True
    except TypeError:
        db.upsert_values("users", {"commands" : {}}, db.query.user_id == us_id)
        return get_permission(us_id, command)

def set_permission(message, us_id : int):
    """Updates the status of a command for the user identified by us_id"""
    user = message.from_user
    if get_admin(us_id) and us_id != user.id and user.id != OWNER_ID:
        permission_denied_procedure(message, "target_admin")
        return
    
    viewed_name = get_viewed_name(us_id)
    user = message.from_user
    lang = get_lang(user.id)
    if get_permission(us_id, message.text) == True: bot_answer = f"{get_localized_string("permission",lang,"permission_of")} {viewed_name} {get_localized_string("permission",lang,"locked")}"
    else: bot_answer = f"{get_localized_string("permission",lang,"permission_of")} {viewed_name} {get_localized_string("permission",lang,"unlocked")}"

    permissions = get_permission(us_id)

    if us_id == user.id and not permissions[message.text] and us_id != OWNER_ID:
        permission_denied_procedure(message, "admin_only")
        return

    permissions[message.text] = not get_permission(us_id, message.text)
    db.upsert_values("users", {"commands" : permissions}, db.query.user_id == us_id)

    bot.reply_to(message, bot_answer, reply_markup=types.ReplyKeyboardRemove())
    logging_procedure(message,bot_answer)

def get_permissions_list(message, us_id : int):
    """Shows the status of all the commands that can be restricted for the user identified by us_id"""
    user = message.from_user
    lang = get_lang(user.id)

    if get_permission(us_id):
        bot_answer = f"{get_localized_string("permission", lang, "list")} {get_viewed_name(us_id)}: \n"
        for command, permission in get_permission(us_id).items():
            bot_answer += f"{command}: {permission};\n"
    else: bot_answer = get_localized_string("choose_argument",lang,"not_found")

    bot.reply_to(message, bot_answer)
    logging_procedure(message,bot_answer)

def get_lang(us_id : int) -> str:
    """Returns the user language code, if not found defaults to en"""
    localization = db.get_single_doc("users", db.query.user_id == us_id, "localization")
    if localization: return localization
    else: return "en"

def set_lang(message, us_id : int):
    """Change the bot language, for the user identified by us_id, into italian or english"""
    viewed_name = get_viewed_name(us_id)
    if get_lang(us_id) == "it":
        bot_answer = f"{viewed_name} {get_localized_string("set_lang","en")}"
        lang = "en"
    else:
        bot_answer = f"{viewed_name} {get_localized_string("set_lang","it")}"
        lang = "it"

    db.upsert_values("users", {"localization" : lang}, db.query.user_id == us_id)
    bot.reply_to(message, bot_answer)
    logging_procedure(message,bot_answer)

def get_gender(us_id : int) -> str:
    """Returns the user gender, if not found defaults to m(ale)"""
    gender = db.get_single_doc("users", db.query.user_id == us_id, "gender")
    if gender: return gender
    else: return 'm'

def set_gender(message, us_id : int):
    """Change the gender of the name chosen by randomname, for the user identified by us_id, into male or female"""
    viewed_name = get_viewed_name(us_id)
    user = message.from_user
    lang = get_lang(user.id)
    if get_gender(us_id) == 'm':
        bot_answer = f"{viewed_name} {get_localized_string("set_gender",lang,'f')}"
        gender = 'f'
    else:
        bot_answer = f"{viewed_name} {get_localized_string("set_gender",lang,'m')}"
        gender = 'm'
 
    db.upsert_values("users", {"gender" : gender}, db.query.user_id == us_id)
    bot.reply_to(message, bot_answer)
    logging_procedure(message,bot_answer)

def get_admin(us_id : int) -> bool:
    """Return true if the user identified by us_id is admin, false otherwise"""
    admin = db.get_single_doc("users", db.query.user_id == us_id, "admin_status")
    if us_id == OWNER_ID and admin == None: return True
    if admin == None: return False
    return admin

def set_admin(message,us_id : int):
    """Turn the user identified by us_id into an admin or vice versa"""
    viewed_name = get_viewed_name(us_id)
    user = message.from_user
    lang = get_lang(user.id)

    if get_admin(us_id) == True: bot_answer = f"{viewed_name} {get_localized_string("set_admin",lang,"remove")}"
    else: bot_answer = f"{viewed_name} {get_localized_string("set_admin",lang,"add")}"
     
    db.upsert_values("users", {"admin_status" : not get_admin(us_id)}, db.query.user_id == us_id)

    bot.reply_to(message, bot_answer)
    logging_procedure(message,bot_answer)

def get_notification_status(us_id : int) -> bool:
    """Returns true if the user has on/off notifications active, false otherwise"""
    notifications = db.get_single_doc("users", db.query.user_id == us_id, "notifications")
    if notifications == None: return True
    else: return notifications

def get_excl_sentence(us_id : int) -> str | None:
    """Returns the special sentence of the user us_id"""
    return db.get_single_doc("users", db.query.user_id == us_id, "exclusive_sentence")

def set_excl_sentence(message, us_id : int): 
    """Set a special sentence the user identified by us_id receives when greeted by the bot"""
    user = message.from_user
    lang = get_lang(user.id)
    sentence = message.text
    
    if not validate_name(message, sentence, "sentence"): return
    
    target_viewed_name = get_viewed_name(us_id)
    if sentence.lower() == "none": sentence = None
        
    if user.id == us_id: bot_answer = f"{get_localized_string("set_sentence",lang,"personal_sentence")} {sentence}"
    else: bot_answer = f"{get_localized_string("set_sentence",lang,"sentence_of")} {target_viewed_name} {get_localized_string("set_name",lang,"is_now")} {sentence}"
            
    db.upsert_values("users", {"exclusive_sentence" : sentence}, db.query.user_id == us_id)

    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer)

def get_info(message,us_id : int):
    """The bot sends a message with basic user informations"""
    user_doc = db.get_single_doc("users", db.query.user_id == us_id)
    user = message.from_user
    lang = get_lang(user.id)

    if user_doc:
        bot_answer = f"{get_localized_string("info",lang,"name")} {user_doc["first_name"]}\n{get_localized_string("info",lang,"last_name")} {user_doc["last_name"]}\nUsername: {user_doc["username"]}\n{get_localized_string("info",lang,"user_id")} {user_doc["user_id"]}\n{get_localized_string("info",lang,"bot_name")} {get_botname(us_id)}\n{get_localized_string("info",lang,"sentence")} {get_excl_sentence(us_id)}\n{get_localized_string("info",lang,"language")} {get_lang(us_id)}\n{get_localized_string("info",lang,"gender")} {get_gender(us_id)}\n{get_localized_string("info",lang,"notification")} {get_notification_status(us_id)}\n{get_localized_string("info",lang,"admin")} {get_admin(us_id)}"
    else: bot_answer = get_localized_string("choose_argument",lang,"not_found")

    bot.reply_to(message, bot_answer)
    logging_procedure(message,bot_answer)

def send_message(message, chat_id : int, scope : str = None, acknowledge : bool = True):
    """Send a message to the chat identified by chat_id"""
    user = message.from_user
    lang = get_lang(user.id)
    bot_answer = get_localized_string("sent",lang)
    viewed_name = get_viewed_name(user.id)

    from_text = f"{get_localized_string("send_to", get_lang(chat_id), "from")} {viewed_name}({user.id}):"
    if scope == 'B': from_text = f"{get_localized_string("broadcast",get_lang(chat_id),"from")} {viewed_name}:"
    if scope == 'A': from_text = f"{get_localized_string("broadcast",get_lang(chat_id),"admin_from")} {viewed_name}:"

    if message.content_type in ("text", "photo", "audio", "voice"):
        try:
            bot.send_message(chat_id,from_text)
            if message.content_type == "text":
                bot.send_message(chat_id,message.text)
            elif message.content_type == "photo":
                file_id = message.photo[-1].file_id
                caption = message.caption if message.caption else None
                bot.send_photo(chat_id,file_id,caption)
            elif message.content_type == "audio":
                file_id = message.audio.file_id
                caption = message.caption if message.caption else None
                bot.send_audio(chat_id,file_id,caption)
            elif message.content_type == "voice":
                file_id = message.voice.file_id
                caption = message.caption if message.caption else None
                bot.send_voice(chat_id,file_id,caption)          
        except telebot.apihelper.ApiTelegramException: bot_answer = get_localized_string("send_to",lang,"blocked")
    else: bot_answer = get_localized_string("send_to",lang,"unsupported")
        
    if acknowledge: 
        bot.reply_to(message,bot_answer)
        logging_procedure(message,bot_answer)

def broadcast(message, admin_only=False):
    """Send a message to all the users of the bot, or if admin only to just the admins"""
    acknowledge = True
    for user in db.tables["users"]:
        try: 
            if user["chat_id"]:
                if admin_only and user["admin_status"]:
                    send_message(message, user["chat_id"], 'A', acknowledge)
                    acknowledge = False
                if not admin_only:
                    send_message(message, user["chat_id"], 'B', acknowledge)
                    acknowledge = False
        except (KeyError, telebot.apihelper.ApiTelegramException): pass

def choose_target(message,command : callable, second_arg : bool = True):
    """First step of the admin framework, it prompts the admin to get the user who they're targeting with their command. The admin framework let the admins reuse the functions written for normal use in a specific admin mode"""
    user = message.from_user
    bot_answer = get_localized_string("choose_target",get_lang(user.id))

    admin_status = get_admin(user.id)
    if not admin_status:
        permission_denied_procedure(message,"admin_only")
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True,one_time_keyboard=True,selective=True)
    for user_data in db.tables["users"]:
        if user_data["username"]: button = types.KeyboardButton(user_data["username"])
        else: button = types.KeyboardButton(user_data["first_name"])
        markup.add(button)

    bot.reply_to(message, bot_answer, reply_markup=markup)
    bot.register_next_step_handler(message, select_target,command, second_arg)
    logging_procedure(message,bot_answer)

def select_target(message, command : callable, second_arg : bool = True):
    """Checks is the name is unique, it it isn't prompts the admin to specify the id"""
    admin_user = message.from_user
    lang = get_lang(admin_user.id)

    us_id = db.get_single_doc("users", db.query.username == message.text, "user_id")
    if not us_id:
        user_docs = db.get_docs("users", db.query.first_name == message.text)
        if len(user_docs) == 1: us_id = user_docs[0]["user_id"] #One user found, everything is fine
        elif len(user_docs) > 1: #Multiple users found, specify which one is the correct one!
            bot_answer = f"{get_localized_string("choose_argument",lang,"multiple_found")}"

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True,one_time_keyboard=True,selective=True)
            for user in user_docs:
                us_id = user["user_id"]
                button = types.KeyboardButton(us_id)
                markup.add(button)
                bot_answer += f"\n{us_id}:\nBotname: {get_viewed_name(us_id)}\n"
            
            bot.reply_to(message, bot_answer, reply_markup=markup)
            logging_procedure(message, bot_answer)
            bot.register_next_step_handler(message, handle_multiple_users, command, second_arg)
            return
        else:
            bot_answer = get_localized_string("choose_argument",lang,"not_found")
            bot.reply_to(message, bot_answer, reply_markup=types.ReplyKeyboardRemove())
            return 
        
    choose_argument(message, command, us_id, second_arg)

def handle_multiple_users(message, command : callable, second_arg : bool = True):
    admin_user = message.from_user
    lang = get_lang(admin_user.id)

    us_id = db.get_single_doc("users", db.query.user_id == int(message.text), "user_id")
    if not us_id:
        bot_answer = get_localized_string("choose_argument",lang,"not_found")
        bot.reply_to(message, bot_answer, reply_markup=types.ReplyKeyboardRemove())
        return
    
    choose_argument(message, command, us_id, second_arg)

def choose_argument(message, command : callable, us_id : int, second_arg : bool = True):
    """Second step of the admin framework, right after user selection. it takes in the required text argument of certain commands"""
    admin_user = message.from_user
    lang = get_lang(admin_user.id)
    markup = types.ReplyKeyboardRemove()

    bot_answer = f"{get_localized_string("choose_argument",lang,"selected")} {get_viewed_name(us_id)} ({us_id}). \n{get_localized_string("choose_argument",lang,"argument")}"

    if not second_arg:
        bot_answer = f"{get_localized_string("choose_argument",lang,"selected")} {get_viewed_name(us_id)} ({us_id})."
        bot.reply_to(message, bot_answer, reply_markup=types.ReplyKeyboardRemove())
        command(message,us_id)
        return
    
    if command == set_permission:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True,one_time_keyboard=True,selective=True)
        commands = db.get_single_doc("users", db.query.user_id == us_id, "commands")
        if commands:
            for command_name in commands:
                button = types.KeyboardButton(command_name)
                markup.add(button)

    bot.reply_to(message, bot_answer, reply_markup=markup)
    bot.register_next_step_handler(message, command, us_id)
    logging_procedure(message,bot_answer)

def get_banned_words(word_type) -> list:
    """Return the list of a specified type of banned world"""
    banned_list = db.get_single_doc("banned_words", db.query.type == word_type, "list")
    if banned_list == None: banned_list = []
    return banned_list

def add_banned_words(message, word_type : str):
    """Add a word to the banned words list"""
    word = (message.text).lower()
    user = message.from_user
    lang = get_lang(user.id)
    banned_list = get_banned_words(word_type)

    if word in banned_list:
        bot_answer = get_localized_string("banned_words", lang, "already_banned")
        bot.reply_to(message,bot_answer)
        logging_procedure(message,bot_answer)
        return
    
    banned_list.append(word)
    list_data = {"list":banned_list, "type" : word_type}
    db.upsert_values("banned_words",list_data, db.query.type == word_type)

    bot_answer = f"{word} {get_localized_string("banned_words", lang, "banned")}"
    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer)

def remove_banned_words(message, word_type : str):
    """Remove a word from the banned words list"""
    word = (message.text).lower()
    user = message.from_user
    lang = get_lang(user.id)
    banned_list = get_banned_words(word_type)

    if word in banned_list:
        banned_list.remove(word)
        bot_answer = f"{word} {get_localized_string("banned_words", lang, "unbanned")}"
        list_data = {"list":banned_list, "type" : word_type}
        db.upsert_values("banned_words",list_data, db.query.type == word_type)

        bot.reply_to(message,bot_answer)
        logging_procedure(message,bot_answer)
        return
        
    bot_answer = get_localized_string("banned_words", lang, "already_unbanned")
    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer)

def get_custom_commands_names() -> list[str]:
    """Returns a list of the dynamically created commands"""
    commands = []
    for command in db.tables["custom_commands"]:
        commands.append(command["name"])
    return commands

def add_custom_command_content(message):
    """Receives the content needed to create the commands"""
    user = message.from_user
    bot_answer = get_localized_string("custom_commands",get_lang(user.id),"add_command_content")
    markup = types.ReplyKeyboardRemove()
    
    bot.reply_to(message, bot_answer, reply_markup=markup)
    bot.register_next_step_handler(message,add_custom_command, message.text)
    logging_procedure(message,bot_answer)

def add_custom_command(message, name: str):
    user = message.from_user
    if message.content_type == "photo": file_id = message.photo[-1].file_id
    elif message.content_type == "audio": file_id = message.audio.file_id
    elif message.content_type == "voice": file_id = message.voice.file_id
    elif message.content_type == "text": file_id = None
    else: 
        bot.reply_to(message, get_localized_string("send_to",get_lang(user.id),"unsupported"))
        return

    command_data = {"content" : {"type" : message.content_type, "text" : message.text, "file_id" : file_id, "caption" : message.caption}, "name" : name.lower()}
    db.upsert_values("custom_commands", command_data, db.query.name == name.lower())

    bot_answer = f"{name} {get_localized_string("custom_commands", get_lang(user.id), "added")}"
    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer)

def remove_custom_command(message):
    user = message.from_user
    markup = types.ReplyKeyboardRemove()

    if not(message.text in get_custom_commands_names()):
        bot_answer = f"{get_localized_string("custom_commands", get_lang(user.id), "not_found")}"
        bot.reply_to(message,bot_answer, reply_markup=markup)
        logging_procedure(message,bot_answer)
        return

    db.remove_values("custom_commands", db.query.name == message.text.lower())

    bot_answer = f"{message.text} {get_localized_string("custom_commands", get_lang(user.id), "removed")}"
    bot.reply_to(message,bot_answer, reply_markup=markup)
    logging_procedure(message,bot_answer)

bot.set_my_commands(commands_en) #default
bot.set_my_commands(commands_it, language_code="it")

send_on_off_notification("online")

@bot.message_handler(commands=["start","hello"])
def send_greets(message):
    """Greet the user with its name and a special sentence"""
    user = message.from_user
    lang = get_lang(user.id)
    store_user_data(user, message.chat.id) #Create or update the user's table when starting
    viewed_name = get_viewed_name(user.id)

    if get_excl_sentence(user.id): special_reply = f"\n{get_excl_sentence(user.id)}"
    else: special_reply = ""
    
    bot_answer = f"{get_localized_string("greet",lang)} {viewed_name}!{special_reply}"

    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["lang"])
def set_user_lang(message):
    user = message.from_user

    current_permission = get_permission(user.id, "lang")
    if current_permission != True:
        permission_denied_procedure(message,current_permission)
        return
    
    set_lang(message, user.id)

@bot.message_handler(commands=["setname"])
def set_name(message):
    """Start the event chain to set the user's botname"""
    user = message.from_user
    bot_answer = get_localized_string("set_name",get_lang(user.id),"prompt")

    current_permission = get_permission(user.id, "setname")
    if current_permission != True:
        permission_denied_procedure(message,current_permission)
        return
    
    bot.reply_to(message, bot_answer)
    bot.register_next_step_handler(message,set_botname,user.id)
    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["resetname"])
def reset_name(message):
    """Call function to reset the user's botname."""
    user = message.from_user
    current_permission = get_permission(user.id, "resetname")
    if current_permission != True:
        permission_denied_procedure(message, current_permission)
        return
    
    reset_botname(message,user.id)

@bot.message_handler(commands=["sendtoowner"])
def send_to_owner(message):
    """Send a message to the owner of the bot"""
    user = message.from_user
    owner_name = get_viewed_name(OWNER_ID)
    bot_answer = f"{get_localized_string("send_to", get_lang(user.id),"user")} {owner_name}?"

    current_permission = get_permission(user.id, "sendtoowner")
    if current_permission != True:
        permission_denied_procedure(message, current_permission)
        return
    
    bot.reply_to(message, bot_answer)
    bot.register_next_step_handler(message,send_message,OWNER_ID)
    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["sendtoadmin"])
def send_to_admin(message):
    """Send a message to all the admins of the bot"""
    user = message.from_user
    bot_answer = get_localized_string("send_to", get_lang(user.id),"admins")

    current_permission = get_permission(user.id, "sendtoadmin")
    if current_permission != True:
        permission_denied_procedure(message, current_permission)
        return
    
    bot.reply_to(message, bot_answer)
    bot.register_next_step_handler(message,broadcast,True)
    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["eventstoday"])
def events_on_wikipedia(message):
    """send a random event of the day from italian wikipedia"""
    user = message.from_user
    lang = get_lang(user.id)
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
            translator = GoogleTranslator("it",lang)
            event = translator.translate(event)
        bot_answer = f"{event}"
    except wikipedia.exceptions.PageError:
        bot_answer = get_localized_string("wikipedia",lang,"page404")
    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["gender"])
def set_user_gender(message):
    """Call function to set the user's gender"""
    user = message.from_user

    current_permission = get_permission(user.id, "gender")
    if current_permission != True:
        permission_denied_procedure(message,current_permission)
        return
    
    set_gender(message, user.id)

@bot.message_handler(commands=["randomnumber"])
def random_number(message):
    """Return the user a random number"""
    bot_answer = random.randrange(0,999)
    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["randomname"])
def random_name(message):
    """Set the user a random name, also doable by using -r as argument for setname"""
    user = message.from_user
    current_permission = get_permission(user.id, "randomname")
    if current_permission != True:
        permission_denied_procedure(message, current_permission)
        return
    
    set_botname(message,user.id,True)

@bot.message_handler(commands=["qrcode"])
def request_qrcode(message):
    user = message.from_user
    chat_id = get_chat_id(user.id)
    current_permission = get_permission(user.id, "qrcode")
    if current_permission != True:
        permission_denied_procedure(message, current_permission)
        return
    
    bot_answer = get_localized_string("qrcode",get_lang(user.id),"msg_to_send")
    bot.reply_to(message,bot_answer)
    bot.register_next_step_handler(message, generate_qrcode,chat_id)
    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["notifications"])
def set_notifications(message):
    user = message.from_user
    lang = get_lang(user.id)
    
    if not db.contains("users", db.query.user_id == user.id):
        permission_denied_procedure(message,"not_found")
        return

    if get_notification_status(user.id): bot_answer = get_localized_string("notifications",lang,"off")
    else: bot_answer = get_localized_string("notifications",lang,"on")

    db.upsert_values("users", {"notifications" : not get_notification_status(user.id)}, db.query.user_id == user.id)
    bot.reply_to(message,bot_answer)

    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["info"])
def info(message):
    user = message.from_user
    get_info(message,user.id)

@bot.message_handler(commands=["permissionlist"])
def permissions_list(message):
    """Return the user a list with all the commands they can and can't use"""
    user = message.from_user
    get_permissions_list(message,user.id)

@bot.message_handler(commands=["about"])
def about(message):
    """Return a sponsor to myself, really"""
    user = message.from_user
    markup = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton("Github",url="github.com/Giu27/SupergiuToolsBot")
    markup.row(button)
    bot_answer = get_localized_string("about",get_lang(user.id))
    bot.reply_to(message,bot_answer, reply_markup=markup)
    logging_procedure(message,bot_answer)

#Admin version of the commands above + extra
@bot.message_handler(commands=["getpersoninfo"])
def get_person_info(message):
    choose_target(message,get_info, False)

@bot.message_handler(commands=["setpersonname"])
def set_person_name(message):
    user = message.from_user
    permission = get_permission(user.id, "setpersonname")
    if not permission:
        permission_denied_procedure(message, "admin_only")
        return
    
    choose_target(message, set_botname)

@bot.message_handler(commands=["resetpersonname"])
def reset_person_name(message):
    user = message.from_user
    permission = get_permission(user.id, "resetpersonname")
    if not permission:
        permission_denied_procedure(message, "admin_only")
        return
    
    choose_target(message, reset_botname, False)

@bot.message_handler(commands=["setpersonpermission"])
def set_person_permission(message):
    user = message.from_user
    permission = get_permission(user.id, "setpersonpermission")
    if not permission:
        permission_denied_procedure(message, "admin_only")
        return
    
    choose_target(message, set_permission)

@bot.message_handler(commands=["getpersonpermission"])
def get_person_permissions(message):
    user = message.from_user
    permission = get_permission(user.id, "getpersonpermission")
    if not permission:
        permission_denied_procedure(message, "admin_only")
        return
    choose_target(message, get_permissions_list, False)

@bot.message_handler(commands=["setpersonadmin"])
def set_person_admin(message):
    """Adds an admin to the bot"""
    user = message.from_user
    if user.id != OWNER_ID:
        permission_denied_procedure(message, "owner_only")
        return
    choose_target(message, set_admin, False)

@bot.message_handler(commands=["setpersonsentence"])
def set_person_sentence(message):
    """Gives a personal sentence easter egg to a user"""
    user = message.from_user
    permission = get_permission(user.id, "setpersonsentence")
    if not permission:
        permission_denied_procedure(message, "admin_only")
        return
    
    choose_target(message, set_excl_sentence)

@bot.message_handler(commands=["setpersonlang"])
def set_person_lang(message):
    user = message.from_user
    permission = get_permission(user.id, "setpersonlang")
    if not permission:
        permission_denied_procedure(message, "admin_only")
        return
    
    choose_target(message, set_lang, False)

@bot.message_handler(commands=["setpersongender"])
def set_person_gender(message):
    user = message.from_user
    permission = get_permission(user.id, "setpersongender")
    if not permission:
        permission_denied_procedure(message, "admin_only")
        return
    
    choose_target(message, set_gender, False)

@bot.message_handler(commands=["getids"])
def get_ids(message):
    """Returns a list with all the bot users"""
    user = message.from_user
    bot_answer = ""

    admin_status = get_admin(user.id)
    if not admin_status:
        permission_denied_procedure(message, "admin_only")
        return
    
    for user in db.tables["users"]:
        try: 
            if user["user_id"]: bot_answer += f"\n\n{user["user_id"]}: {user["first_name"]} {user["last_name"]}\nBotname: {get_botname(user["user_id"])}"
        except KeyError: pass

    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer.lstrip())

@bot.message_handler(commands=["sendto"])
def send_to_target(message):
    user = message.from_user
    permission = get_permission(user.id, "sendto")
    if not permission:
        permission_denied_procedure(message, "admin_only")
        return
    
    choose_target(message,send_message)

@bot.message_handler(commands=["broadcast"])
def send_in_broadcast(message):
    """Event chain to send a message in broadcast"""
    user = message.from_user
    bot_answer = get_localized_string("broadcast", get_lang(user.id), "msg_to_send")

    admin_status = get_admin(user.id)
    permission = get_permission(user.id, "broadcast")
    if not admin_status or not permission:
        permission_denied_procedure(message, "admin_only")
        return
    
    bot.reply_to(message, bot_answer)
    bot.register_next_step_handler(message,broadcast)
    logging_procedure(message,bot_answer)

#banned words events
@bot.message_handler(commands=["addbanned"])
def add_banned(message):
    user = message.from_user
    bot_answer = get_localized_string("banned_words",get_lang(user.id),"add_banned")

    admin_status = get_admin(user.id)
    permission = get_permission(user.id, "addbanned")
    if not admin_status or not permission:
        permission_denied_procedure(message, "admin_only")
        return
    
    bot.reply_to(message, bot_answer)
    bot.register_next_step_handler(message,add_banned_words,"banned")
    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["removebanned"])
def remove_banned(message):
    user = message.from_user
    bot_answer = get_localized_string("banned_words",get_lang(user.id),"remove_banned")

    admin_status = get_admin(user.id)
    permission = get_permission(user.id, "removebanned")
    if not admin_status or not permission:
        permission_denied_procedure(message, "admin_only")
        return
    
    bot.reply_to(message, bot_answer)
    bot.register_next_step_handler(message,remove_banned_words,"banned")
    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["addultrabanned"])
def add_ultra_banned(message):
    user = message.from_user
    bot_answer = get_localized_string("banned_words",get_lang(user.id),"add_ultrabanned")

    admin_status = get_admin(user.id)
    permission = get_permission(user.id, "addbanned")
    if not admin_status or not permission:
        permission_denied_procedure(message, "admin_only")
        return
    
    bot.reply_to(message, bot_answer)
    bot.register_next_step_handler(message,add_banned_words,"ultrabanned")
    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["removeultrabanned"])
def remove_ultra_banned(message):
    user = message.from_user
    bot_answer = get_localized_string("banned_words",get_lang(user.id),"remove_banned")

    admin_status = get_admin(user.id)
    permission = get_permission(user.id, "removebanned")
    if not admin_status or not permission:
        permission_denied_procedure(message, "admin_only")
        return
    
    bot.reply_to(message, bot_answer)
    bot.register_next_step_handler(message,remove_banned_words,"ultrabanned")
    logging_procedure(message,bot_answer)

#custom commands events
@bot.message_handler(commands=["getcommandslist"])
def get_command_list(message):
    user = message.from_user
    admin_status = get_admin(user.id)

    if not admin_status:
        permission_denied_procedure(message, "admin_only")
        return

    bot_answer = get_localized_string("custom_commands",get_lang(user.id),"list")
    for command in get_custom_commands_names():
        bot_answer += (f"\n{command}")

    bot.reply_to(message, bot_answer)
    logging_procedure(message, bot_answer)

@bot.message_handler(commands=["addcommand"])
def add_command(message):
    user = message.from_user
    bot_answer = get_localized_string("custom_commands",get_lang(user.id),"add_command")

    admin_status = get_admin(user.id)
    permission = get_permission(user.id, "addcommand")
    if not admin_status or not permission:
        permission_denied_procedure(message, "admin_only")
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True,one_time_keyboard=True,selective=True)
    for command in get_custom_commands_names():
        button = types.KeyboardButton(command)
        markup.add(button)
    
    bot.reply_to(message, bot_answer, reply_markup=markup)
    bot.register_next_step_handler(message,add_custom_command_content)
    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["removecommand"])
def remove_command(message):
    user = message.from_user
    bot_answer = get_localized_string("custom_commands",get_lang(user.id),"remove_command")

    admin_status = get_admin(user.id)
    permission = get_permission(user.id, "addcommand")
    if not admin_status or not permission:
        permission_denied_procedure(message, "admin_only")
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True,one_time_keyboard=True,selective=True)
    for command in get_custom_commands_names():
        button = types.KeyboardButton(command)
        markup.add(button)
    
    bot.reply_to(message, bot_answer, reply_markup=markup)
    bot.register_next_step_handler(message,remove_custom_command)
    logging_procedure(message,bot_answer)

@bot.message_handler(func= lambda message: message.text.startswith('/'))
def handle_custom_commands(message):
    """Handle dynamically generated commands"""
    user = message.from_user
    command = message.text[1:]
    if command in get_custom_commands_names():
        permission = get_permission(user.id, command)
        if not permission:
            permission_denied_procedure(message, permission)
            return
        
        message_data = db.get_single_doc("custom_commands", db.query.name == command, "content")
        if message_data["type"] == "text": bot.send_message(message.chat.id,message_data["text"])
        elif message_data["type"] == "photo": bot.send_photo(message.chat.id,message_data["file_id"],message_data["caption"])
        elif message_data["type"] == "audio": bot.send_audio(message.chat.id,message_data["file_id"],message_data["caption"])
        elif message_data["type"] == "voice": bot.send_voice(message.chat.id,message_data["file_id"],message_data["caption"])
        else: bot.reply_to(message, get_localized_string("send_to",get_lang(user.id),"unsupported"))

        if message_data["type"] == "text": content = message_data["text"]
        else: content = message_data["type"]
        logging_procedure(message, content)
    else: log_and_update(message)

#General handlers
@bot.message_handler(content_types=["photo","video","sticker","animation","document","audio","voice"])
def handle_media(message):
    user = message.from_user
    lang = get_lang(user.id)

    bot_answer = f"{get_localized_string("greet",lang)} {get_viewed_name(user.id)}, {get_localized_string("handle_media",lang,"image")}"
    if (message.voice or message.audio): bot_answer = f"{get_localized_string("greet",lang)} {get_viewed_name(user.id)}, {get_localized_string("handle_media",lang,"audio")}"

    bot.reply_to(message, bot_answer)
    logging_procedure(message,bot_answer)

@bot.message_handler(func= lambda commands:True)
def log_and_update(message):
    """Logs messages and updates the database"""
    user = message.from_user
    store_user_data(user,message.chat.id)

    if LOG:
        if user.username: user_info = user.username
        else: user_info = f"{user.first_name} {user.last_name}"

        if message.content_type == "text": content = message.text
        else: content = message.content_type

        log_file = open(f"{log_path}/{user.id}.txt","a")
        logger.info(f"{user.id}, {user_info}: {content}")
        log_file.write(f"{user.id}, {user_info}: {content}\n")
    
bot.infinity_polling()

send_on_off_notification("offline")

db.close()