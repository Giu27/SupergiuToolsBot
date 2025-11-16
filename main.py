import telebot, os, logging, qrcode, wikipedia, random, faker, unidecode
from dotenv import load_dotenv
from tinydb import TinyDB, Query
from telebot import types
from datetime import date
from deep_translator import GoogleTranslator
from localizations import *

load_dotenv()

DEV_MODE = False
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID"))
bot = telebot.TeleBot(BOT_TOKEN)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
log_path = "logs"

db = TinyDB("Bot_DB.JSON")
users_table = db.table("users")
banned_words_table = db.table("banned_words")
User = Query()
Word_type = Query()

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
    users_table.upsert(user_data, User.user_id == user.id)

def check_banned_name(name : str) -> bool:
    """Return true if name is banned, false otherwise"""
    banned_words = get_banned_words("banned")
    ultra_banned_words = get_banned_words("ultrabanned")
    numToCh = {'1' : 'i','3' : 'e','4' : 'r', '0' : 'o', '7' : 'l', '5' : 's','$': 'e','€':'e','т' : 't','п' : 'n'}
    numToCh2 = {'1' : 'i','3' : 'e','4' : 'a', '0' : 'o', '7' : 'l', '5' : 's','$': 'e','€':'e','т' : 't','п' : 'n'}
    wordname = ""
    for char in name:
        car = char
        try:
            car = numToCh[char]
        except KeyError: pass
        if car == ' ': continue
        wordname += car.lower()

    if wordname in banned_words: return True

    for word in ultra_banned_words:
        if word in wordname: return True
    
    wordname = ""
    for char in name:
        car = char
        try:
            car = numToCh2[char]
        except KeyError: pass
        if car == ' ': continue
        wordname += car.lower()
    
    if wordname in banned_words: return True

    for word in ultra_banned_words:
        if word in wordname: return True

def logging_procedure(message, bot_answer : str):
    """Standard logging, to a file and console, of the user and bot messages not registered by log function"""
    log_file = open(f"{log_path}/{message.from_user.id}.txt","a")
    log(message)
    logger.info(f"Bot: {bot_answer}")
    log_file.write(f"Bot: {bot_answer}\n")

def get_localized_string(source : str, lang : str, element : str = None):
    """Returns the string from localizations.py in localizations[source][lang] and optionally elements"""
    try:
        if element: return localizations[source][lang][element]
        return localizations[source][lang]
    except KeyError:
        try:
            return localizations["not_found"][lang]
        except KeyError:
            return localizations["not_found"]["en"]

def permission_denied_procedure(message, error_msg : str = ""):
    """Standard procedure, whenever a user doesn't have the permission to do a certain action"""
    user = message.from_user
    lang = get_lang(user.id)
    bot_answer = f"{get_localized_string("permission_denied",lang,"default")}\n{get_localized_string("permission_denied",lang,error_msg)}"
    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer)

def send_on_off_notification(status : str):
    """Sends a notification whenever the bot turns on or off"""
    if not DEV_MODE:
        for user in users_table:
            bot_answer = f"{get_localized_string("notifications",get_lang(user["user_id"]),"bot")} {status}!"
            try: 
                if user["chat_id"] and get_notification_status(user["user_id"]):
                    bot.send_message(user["chat_id"], bot_answer)
                    logger.info(f"Bot: {bot_answer}. chat_id: {user["chat_id"]}")
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
    except Exception as e:
        bot_answer = f"{get_localized_string("qrcode",lang,"error")} {get_viewed_name(OWNER_ID)}: \n{e}"
    bot.reply_to(message, bot_answer)
    logging_procedure(message,bot_answer)

def set_botname(message, us_id : int, randomName=False):
    """Updates the botname of the user identified by us_id"""
    MAX_CHARS = 200
    user = message.from_user
    name = message.text
    lang = get_lang(user.id)
    if randomName or name == "-r": name = generate_random_name(get_gender(us_id))
    
    if len(name) > MAX_CHARS:
        bot_answer = f"{get_localized_string("set_name",lang,"max_chars")} Max: {MAX_CHARS}"
        bot.reply_to(message,bot_answer)
        logging_procedure(message,bot_answer)
        return
    
    if check_banned_name(name):
        bot_answer = get_localized_string("set_name",lang,"name_banned")
        bot.reply_to(message,bot_answer)
        logging_procedure(message,bot_answer)
        return
    
    user_doc = users_table.search(User.user_id == us_id)
    if user_doc:
        target_viewed_name = get_viewed_name(us_id)
        user_doc[0]["bot_name"] = name
        if user.id == us_id:
            bot_answer = f"{get_localized_string("set_name",lang,"personal_name")} {name}"
        else:
            bot_answer = f"{get_localized_string("set_name",lang,"name_of")} {target_viewed_name} {get_localized_string("set_name",lang,"is_now")} {name}"
            user_data = {"bot_name" : name}
            users_table.upsert(user_data, User.user_id == us_id)

    else: bot_answer = get_localized_string("choose_text",lang,"not_found")
    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer)

def reset_botname(message, us_id : int):
    """Reset the name of a user identified by us_id"""
    user_doc = users_table.search(User.user_id == us_id)
    user = message.from_user
    lang = get_lang(user.id)
    if user_doc:
        target_name = user_doc[0]["first_name"]
        user_data = {"bot_name" : None}
        users_table.upsert(user_data, User.user_id == us_id)
        bot_answer = f"{get_localized_string("set_name",lang,"name_of")} {target_name} {get_localized_string("set_name",lang,"resetted")}"
    else:
        bot_answer = get_localized_string("choose_text",lang,"not_found")
    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer)

def get_botname(us_id : int) -> str | None:
    """Returns the botname of the user identified by us_id"""
    user_doc = users_table.search(User.user_id == us_id)
    if user_doc: 
        botname = user_doc[0]["bot_name"]
        if botname: 
            if check_banned_name(botname):
                botname = None
                user_data = {"bot_name" : None}
                users_table.upsert(user_data, User.user_id == us_id)
        return botname
    else: return None

def get_viewed_name(us_id : int) -> str | None:
    """Returns the currently visualized name in the bot"""
    if get_botname(us_id): user_name = get_botname(us_id)
    else: 
        user_doc = users_table.search(User.user_id == us_id)
        if user_doc: user_name = user_doc[0]["first_name"]
        else: return None
    return user_name

def get_chat_id(us_id : int) -> int | None:
    """Return the chat id stored in the database"""
    user_doc = users_table.search(User.user_id == us_id)
    if user_doc: 
        ch_id = user_doc[0]["chat_id"]
        if ch_id: return ch_id
        else: return None
    else: return None

def set_permission(message, us_id : int):
    """Updates the status of a user from normal to restricted and vice versa"""
    user = message.from_user
    if get_admin(us_id) and us_id != user.id:
        permission_denied_procedure(message, "target_admin")
        return
    
    viewed_name = get_viewed_name(us_id)
    user = message.from_user
    lang = get_lang(user.id)
    if get_permission(us_id, message.text) == True:
        bot_answer = f"{get_localized_string("permission",lang,"permission_of")} {viewed_name} {get_localized_string("permission",lang,"locked")}"
    else:
        bot_answer = f"{get_localized_string("permission",lang,"permission_of")} {viewed_name} {get_localized_string("permission",lang,"unlocked")}"

    data = get_permission(us_id)

    if us_id == user.id and not data[message.text] and us_id != OWNER_ID:
        permission_denied_procedure(message, "admin_only")
        return

    data[message.text] = not get_permission(us_id, message.text)
    user_data = {"commands" : data}
    users_table.upsert(user_data, User.user_id == us_id)
    bot.reply_to(message, bot_answer, reply_markup=types.ReplyKeyboardRemove())
    logging_procedure(message,bot_answer)

def get_permission(us_id : int, command : str = None) -> bool | dict:
    """Returns true if the user can use a command, false if restricted. If no command is specified returns a dict"""
    user_doc = users_table.search(User.user_id == us_id)
    if user_doc:
        if command == None: 
            try:
                if user_doc[0]["commands"]: return user_doc[0]["commands"]
                else: return {}
            except KeyError:
                return {}
        try:
            return user_doc[0]["commands"][command]
        except KeyError:
            data = user_doc[0]["commands"]
            data[command] = True
            user_data = {"commands" : data}
            users_table.upsert(user_data, User.user_id == us_id)
            return True

def set_lang(message, us_id : int):
    """Change the bot language, for the user identified by us_id, into italian or english"""
    viewed_name = get_viewed_name(us_id)
    if get_lang(us_id) == "it":
        bot_answer = f"{viewed_name} {get_localized_string("set_lang","en")}"
        lang = "en"
    else:
        bot_answer = f"{viewed_name} {get_localized_string("set_lang","it")}"
        lang = "it"
    user_data = {
        "localization" : lang
        }
    users_table.upsert(user_data, User.user_id == us_id)
    bot.reply_to(message, bot_answer)
    logging_procedure(message,bot_answer)

def get_lang(us_id : int) -> str:
    """Returns the user language code, if not found defaults to en"""
    user_doc = users_table.search(User.user_id == us_id)
    if user_doc: 
        try: 
            return user_doc[0]["localization"]
        except KeyError:
            return "en"
    return "en"

def set_gender(message, us_id : int):
    """Change the gender of the name chosen by randomname, for the user identified by us_id, into male or female"""
    viewed_name = get_viewed_name(us_id)
    user = message.from_user
    lang = get_lang(user.id)
    if get_gender(us_id) == "m":
        bot_answer = f"{viewed_name} {get_localized_string("set_gender",lang,"f")}"
        gender = "f"
    else:
        bot_answer = f"{viewed_name} {get_localized_string("set_gender",lang,"m")}"
        gender = "m"
    user_data = {
        "gender" : gender
        }
    users_table.upsert(user_data, User.user_id == us_id)
    bot.reply_to(message, bot_answer)
    logging_procedure(message,bot_answer)

def get_gender(us_id : int) -> str:
    """Returns the user gender, if not found defaults to m(ale)"""
    user_doc = users_table.search(User.user_id == us_id)
    if user_doc: 
        try: 
            return user_doc[0]["gender"]
        except KeyError:
            return "m"
    return "m"

def get_admin(us_id : int) -> bool:
    """Return true if the user identified by us_id is admin, false otherwise"""
    user_doc = users_table.search(User.user_id == us_id)
    if user_doc: 
        try:
            if us_id == OWNER_ID and user_doc[0]["admin_status"] == None: return True
            if user_doc[0]["admin_status"] == None: return False
            return user_doc[0]["admin_status"]
        except KeyError:
            return False
    return None

def set_admin(message,us_id : int):
    """Turn the user identified by us_id into an admin or vice versa"""
    viewed_name = get_viewed_name(us_id)
    user = message.from_user
    lang = get_lang(user.id)
    if get_admin(us_id) == True:
        bot_answer = f"{viewed_name} {get_localized_string("set_admin",lang,"remove")}"
    else:
        bot_answer = f"{viewed_name} {get_localized_string("set_admin",lang,"add")}"
    user_data = {
        "admin_status" : not get_admin(us_id)
        }
    users_table.upsert(user_data, User.user_id == us_id)
    bot.reply_to(message, bot_answer)
    logging_procedure(message,bot_answer)

def get_notification_status(us_id : int) -> bool:
    """Returns true if the user has on/off notifications active, false otherwise"""
    user_doc = users_table.search(User.user_id == us_id)
    if user_doc: 
        try: 
            return user_doc[0]["notifications"]
        except KeyError:
            return True
    return True

def set_excl_sentence(message, us_id : int): 
    """Set a special sentence the user identified by us_id receives when greeted by the bot"""
    MAX_CHARS = 200
    user = message.from_user
    lang = get_lang(user.id)
    sentence = message.text
    
    if len(sentence) > MAX_CHARS:
        bot_answer = f"{get_localized_string("set_name",lang,"max_chars")} Max: {MAX_CHARS}"
        bot.reply_to(message,bot_answer)
        logging_procedure(message, bot_answer)
        return
    
    if check_banned_name(sentence):
        bot_answer = {get_localized_string("set_sentence",lang,"sentence_banned")}
        bot.reply_to(message,bot_answer)
        logging_procedure(message, bot_answer)
        return
    
    user_doc = users_table.search(User.user_id == us_id)
    if user_doc:
        target_viewed_name = get_viewed_name(us_id)
        if sentence.lower() == "none": sentence = None
        user_doc[0]["exclusive_sentence"] = sentence
        if user.id == us_id:
            bot_answer = f"{get_localized_string("set_sentence",lang,"personal_sentence")} {sentence}"
        else:
            bot_answer = f"{get_localized_string("set_sentence",lang,"sentence_of")} {target_viewed_name} {get_localized_string("set_name",lang,"is_now")} {sentence}"
            user_data = {
                "exclusive_sentence" : sentence
            }
            users_table.upsert(user_data, User.user_id == us_id)

    else: bot_answer = get_localized_string("choose_text",lang,"not_found")
    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer)

def get_excl_sentence(us_id : int) -> str | None:
    """Returns the special sentence of the user us_id"""
    user_doc = users_table.search(User.user_id == us_id)
    if user_doc: 
        try: 
            return user_doc[0]["exclusive_sentence"]
        except KeyError:
            return None
    return None

def get_info(message,us_id : int):
    """The bot sends a message with basic user informations"""
    user_doc = users_table.search(User.user_id == us_id)
    user = message.from_user
    lang = get_lang(user.id)

    if user_doc:
        bot_answer = f"{get_localized_string("info",lang,"name")} {user_doc[0]["first_name"]}\n{get_localized_string("info",lang,"last_name")} {user_doc[0]["last_name"]}\nUsername: {user_doc[0]["username"]}\n{get_localized_string("info",lang,"user_id")} {user_doc[0]["user_id"]}\n{get_localized_string("info",lang,"bot_name")} {get_botname(us_id)}\n{get_localized_string("info",lang,"sentence")} {get_excl_sentence(us_id)}\n{get_localized_string("info",lang,"language")} {get_lang(us_id)}\n{get_localized_string("info",lang,"gender")} {get_gender(us_id)}\n{get_localized_string("info",lang,"notification")} {get_notification_status(us_id)}\n{get_localized_string("info",lang,"admin")} {get_admin(us_id)}"
    else: bot_answer = get_localized_string("choose_text",lang,"not_found")
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
        except telebot.apihelper.ApiTelegramException:
            bot_answer = get_localized_string("send_to",lang,"blocked")
    else:
        bot_answer = get_localized_string("send_to",lang,"unsupported")
        
    if acknowledge: 
        bot.reply_to(message,bot_answer)
        logging_procedure(message,bot_answer)

def broadcast(message, admin_only=False):
    """Send a message to all the users of the bot, or if admin only to just the admins"""
    acknowledge = True
    for user in users_table:
        try: 
            if user["chat_id"]:
                if admin_only and user["admin_status"]:
                    send_message(message, user["chat_id"], 'A', acknowledge)
                    acknowledge = False
                if not admin_only:
                    send_message(message, user["chat_id"], 'B', acknowledge)
                    acknowledge = False
        except (KeyError, telebot.apihelper.ApiTelegramException): pass

def choose_text(message,command : callable):
    """Second step of the admin framework, it takes in the required text argument of certain commands"""
    admin_user = message.from_user
    lang = get_lang(admin_user.id)
    markup = types.ReplyKeyboardRemove()
    user_doc = users_table.search(User.username == message.text)
    if user_doc:
        us_id = user_doc[0]["user_id"]
    else:
        user_doc = users_table.search(User.first_name == message.text)
        if user_doc:
            us_id = user_doc[0]["user_id"]
        else:
            bot_answer = get_localized_string("choose_text",lang,"not_found")
            bot.reply_to(message, bot_answer, reply_markup=types.ReplyKeyboardRemove())
            return
    bot_answer = f"{get_localized_string("choose_text",lang,"selected")} {get_viewed_name(us_id)} ({us_id}). \n{get_localized_string("choose_text",lang,"argument")}"

    if command == reset_botname or command == set_admin or command == get_info or command == set_lang or command == set_gender:
        bot_answer = f"{get_localized_string("choose_text",lang,"selected")} {get_viewed_name(us_id)} ({us_id})."
        bot.reply_to(message, bot_answer, reply_markup=types.ReplyKeyboardRemove())
        command(message,us_id)
        return
    
    if command == set_permission:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True,one_time_keyboard=True,selective=True)
        user_doc = users_table.search(User.user_id == us_id)
        if user_doc[0]["commands"]:
            for command_name in user_doc[0]["commands"]:
                button = types.KeyboardButton(command_name)
                markup.add(button)

    bot.reply_to(message, bot_answer, reply_markup=markup)
    bot.register_next_step_handler(message, command, us_id)
    logging_procedure(message,bot_answer)

def choose_target(message,command : callable):
    """First step of the admin framework, it specifies the user who the admin is targeting with its command. The admin framework let the admins reuse the functions written for normal use in a specific admin mode"""
    user = message.from_user
    bot_answer = get_localized_string("choose_target",get_lang(user.id))

    admin_status = get_admin(user.id)
    if not admin_status:
        permission_denied_procedure(message,"admin_only")
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True,one_time_keyboard=True,selective=True)
    for user_data in users_table:
        if user_data["username"]:
            button = types.KeyboardButton(user_data["username"])
        else:
            button = types.KeyboardButton(user_data["first_name"])
        markup.add(button)

    bot.reply_to(message, bot_answer, reply_markup=markup)
    bot.register_next_step_handler(message, choose_text,command)
    logging_procedure(message,bot_answer)

def update_banned_words(message, word_type : str):
    """Updates the lists of banned worlds"""
    word = (message.text).lower()
    user = message.from_user
    lang = get_lang(user.id)
    banned_doc = banned_words_table.search(Word_type.type == word_type)
    if banned_doc:
        banned_list = banned_doc[0]["list"]
        if word in banned_list:
            bot_answer = get_localized_string("banned_words", lang, "already_banned")
            bot.reply_to(message,bot_answer)
            logging_procedure(message,bot_answer)
            return
        banned_list.append(word)
        list_data = {"list":banned_list, "type" : word_type}
        banned_words_table.upsert(list_data, Word_type.type == word_type)
    else:
        banned_list = []
        banned_list.append(word)
        list_data = {"list":banned_list, "type" : word_type}
        banned_words_table.upsert(list_data, Word_type.type == word_type)
    bot_answer = f"{word} {get_localized_string("banned_words", lang, "banned")}"
    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer)

def get_banned_words(word_type) -> list:
    """Return the list of a specified type of banned world"""
    banned_doc = banned_words_table.search(Word_type.type == word_type)
    if banned_doc: banned_list = banned_doc[0]["list"]
    else: banned_list = []
    return banned_list

bot.set_my_commands(commands_en) #default
bot.set_my_commands(commands_it, language_code="it")

send_on_off_notification("online")

@bot.message_handler(commands=["lang"])
def set_user_lang(message):
    user = message.from_user

    current_permission = get_permission(user.id, "lang")
    if not current_permission:
        permission_denied_procedure(message,"Blocked")
        return
    
    set_lang(message, user.id)

@bot.message_handler(commands=["start","hello"])
def send_greets(message):
    """Greet the user with its name and a special sentence"""
    user = message.from_user
    lang = get_lang(user.id)
    if get_botname(user.id): viewed_name = get_botname(user.id)
    else: viewed_name = user.first_name

    if get_excl_sentence(user.id): special_reply = get_excl_sentence(user.id)
    else: special_reply = ""
    
    bot_answer = f"{get_localized_string("greet",lang)} {viewed_name}!"
    try: bot_answer = f"{bot_answer}\n{special_reply}"
    except KeyError: pass

    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["setname"])
def set_name(message):
    user = message.from_user
    bot_answer = get_localized_string("set_name",get_lang(user.id),"prompt")

    current_permission = get_permission(user.id, "setname")
    if not current_permission:
        permission_denied_procedure(message,"Blocked")
        return
    
    bot.reply_to(message, bot_answer)
    bot.register_next_step_handler(message,set_botname,user.id)
    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["resetname"])
def reset_name(message):
    user = message.from_user
    current_permission = get_permission(user.id, "resetname")
    if not current_permission:
        permission_denied_procedure(message, "Blocked")
        return
    
    reset_botname(message,user.id)

@bot.message_handler(commands=["sendtoowner"])
def send_to_owner(message):
    """Send a message to the owner of the bot"""
    user = message.from_user
    owner_name = get_viewed_name(OWNER_ID)
    bot_answer = f"{get_localized_string("send_to", get_lang(user.id),"user")} {owner_name}?"

    current_permission = get_permission(user.id, "sendtoowner")
    if not current_permission:
        permission_denied_procedure(message, "Blocked")
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
    if not current_permission:
        permission_denied_procedure(message, "Blocked")
        return
    
    bot.reply_to(message, bot_answer)
    bot.register_next_step_handler(message,broadcast,True)
    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["gender"])
def set_user_gender(message):
    user = message.from_user

    current_permission = get_permission(user.id, "gender")
    if not current_permission:
        permission_denied_procedure(message,"Blocked")
        return
    
    set_gender(message, user.id)

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

@bot.message_handler(commands=["randomnumber"])
def random_number(message):
    bot_answer = random.randrange(0,999)
    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["randomname"])
def random_name(message):
    user = message.from_user
    current_permission = get_permission(user.id, "randomname")
    if not current_permission:
        permission_denied_procedure(message, "Blocked")
        return
    
    set_botname(message,user.id,True)

@bot.message_handler(commands=["notifications"])
def set_notifications(message):
    user = message.from_user
    lang = get_lang(user.id)
    
    if get_notification_status(user.id):
        bot_answer = get_localized_string("notifications",lang,"off")
    else:
        bot_answer = get_localized_string("notifications",lang,"on")

    user_data = {"notifications" : not get_notification_status(user.id)}
    users_table.upsert(user_data, User.user_id == user.id)
    bot.reply_to(message,bot_answer)

    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["qrcode"])
def request_qrcode(message):
    user = message.from_user
    chat_id = get_chat_id(user.id)
    current_permission = get_permission(user.id, "qrcode")
    if not current_permission:
        permission_denied_procedure(message, "Blocked")
        return
    
    bot_answer = get_localized_string("qrcode",get_lang(user.id),"msg_to_send")
    bot.reply_to(message,bot_answer)
    bot.register_next_step_handler(message, generate_qrcode,chat_id)
    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["info"])
def info(message):
    user = message.from_user
    get_info(message,user.id)

@bot.message_handler(commands=["about"])
def about(message):
    user = message.from_user
    markup = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton("Github",url="github.com/Giu27/SupergiuToolsBot")
    markup.row(button)
    bot_answer = get_localized_string("about",get_lang(user.id))
    bot.reply_to(message,bot_answer, reply_markup=markup)
    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["setpersonname"])
def set_person_name(message):
    user = message.from_user
    permission = get_permission(user.id, "setpersonname")
    if not permission:
        permission_denied_procedure(message, "admin_only")
        return
    
    choose_target(message, set_botname)

@bot.message_handler(commands=["setpersonpermission"])
def set_person_permission(message):
    user = message.from_user
    permission = get_permission(user.id, "setpersonpermission")
    if not permission:
        permission_denied_procedure(message, "admin_only")
        return
    
    choose_target(message, set_permission)

@bot.message_handler(commands=["setpersonadmin"])
def set_person_admin(message):
    user = message.from_user
    if user.id != OWNER_ID:
        permission_denied_procedure(message, "owner_only")
        return
    choose_target(message, set_admin)

@bot.message_handler(commands=["setpersonsentence"])
def set_person_sentence(message):
    user = message.from_user
    permission = get_permission(user.id, "setpersonsentence")
    if not permission:
        permission_denied_procedure(message, "admin_only")
        return
    
    choose_target(message, set_excl_sentence)

@bot.message_handler(commands=["resetpersonname"])
def reset_person_name(message):
    user = message.from_user
    permission = get_permission(user.id, "resetpersonname")
    if not permission:
        permission_denied_procedure(message, "admin_only")
        return
    
    choose_target(message, reset_botname)

@bot.message_handler(commands=["getpersoninfo"])
def get_person_info(message):
    choose_target(message,get_info)

@bot.message_handler(commands=["setpersonlang"])
def set_person_lang(message):
    user = message.from_user
    permission = get_permission(user.id, "setpersonlang")
    if not permission:
        permission_denied_procedure(message, "admin_only")
        return
    
    choose_target(message, set_lang)

@bot.message_handler(commands=["setpersongender"])
def set_person_lang(message):
    user = message.from_user
    permission = get_permission(user.id, "setpersongender")
    if not permission:
        permission_denied_procedure(message, "admin_only")
        return
    
    choose_target(message, set_gender)

@bot.message_handler(commands=["getids"])
def get_ids(message):
    user = message.from_user
    bot_answer = ""

    admin_status = get_admin(user.id)
    if not admin_status:
        permission_denied_procedure(message, "admin_only")
        return
    
    for user in users_table:
        try: 
            if user["user_id"]:
                bot_answer += f"{user["user_id"]}: {user["first_name"]} {user["last_name"]}\nBotname: {get_botname(user["user_id"])}\n\n"
        except KeyError: pass

    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer)

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

@bot.message_handler(commands=["addbanned"])
def add_banned_word(message):
    user = message.from_user
    bot_answer = get_localized_string("banned_words",get_lang(user.id),"add_banned")

    admin_status = get_admin(user.id)
    permission = get_permission(user.id, "addbanned")
    if not admin_status or not permission:
        permission_denied_procedure(message, "admin_only")
        return
    
    bot.reply_to(message, bot_answer)
    bot.register_next_step_handler(message,update_banned_words,"banned")
    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["addultrabanned"])
def add_ultra_banned_word(message):
    user = message.from_user
    bot_answer = get_localized_string("banned_words",get_lang(user.id),"add_ultrabanned")

    admin_status = get_admin(user.id)
    permission = get_permission(user.id, "addbanned")
    if not admin_status or not permission:
        permission_denied_procedure(message, "admin_only")
        return
    
    bot.reply_to(message, bot_answer)
    bot.register_next_step_handler(message,update_banned_words,"ultrabanned")
    logging_procedure(message,bot_answer)

@bot.message_handler(content_types=["photo","video","sticker","animation","document","audio","voice"])
def handle_media(message):
    user = message.from_user
    lang = get_lang(user.id)
    bot_answer = f"{get_localized_string("greet",lang)} {get_viewed_name(user.id)}, {get_localized_string("handle_media",lang,"image")}"
    if (message.voice or message.audio): bot_answer = f"{get_localized_string("greet",lang)} {get_viewed_name(user.id)}, {get_localized_string("handle_media",lang,"audio")}"
    bot.reply_to(message, bot_answer)
    logging_procedure(message,bot_answer)

@bot.message_handler(func= lambda commands:True)
def log(message):
    """Logs messages that aren't commands and updates the database"""
    user = message.from_user
    log_file = open(f"{log_path}/{user.id}.txt","a")
    store_user_data(user,message.chat.id)
    if user.username: user_info = user.username
    else: user_info = f"{user.first_name} {user.last_name}"
    if message.content_type == "text": content = message.text
    else: content = message.content_type
    logger.info(f"{user.id}, {user_info}: {content}")
    log_file.write(f"{user.id}, {user_info}: {content}\n")
    
bot.infinity_polling()

send_on_off_notification("offline")

db.close()