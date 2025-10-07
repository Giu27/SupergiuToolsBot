import telebot, os, logging, qrcode, wikipedia, random, faker, unidecode
from dotenv import load_dotenv
from tinydb import TinyDB, Query
from telebot import types
from datetime import date

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

denied_messages = {
    "target_admin" : "Non puoi bloccare un admin.",
    "owner_only" : "Devi essere owner.",
    "admin_only" : "Devi essere admin",
    "Blocked" : "Il tuo account è soggetto a restrizioni."
}

commands = [
    types.BotCommand("ciao","Saluta l'utente "),
    types.BotCommand("setname","Modifica il tuo nome"),
    types.BotCommand("resetname","Ripristina il tuo nome originale"),
    types.BotCommand("sendtoowner","Invia un messaggio all'owner"),
    types.BotCommand("sendtoadmin","Invia un messaggio a tutti gli admin"),
    types.BotCommand("eventstoday","Restituisce curiosità storiche sulla data di oggi"),
    types.BotCommand("randomnumber","Restituisce un numero casuale tra 0 e 999"),
    types.BotCommand("randomname","Imposta un nome casuale"),
    types.BotCommand("qrcode", "Crea un QR Code di un contenuto testuale inviato"),
    types.BotCommand("notifications","Attiva/Disattiva le notifiche"),
    types.BotCommand("info","Restituisce le informazioni memorizzate dal bot"),
    types.BotCommand("about","Restituisce informazioni sul bot")
]

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
        "can_use_commands" : get_permission(user.id),
        "admin_status" : get_admin(user.id),
        "exclusive_sentence" : get_excl_sentence(user.id),
        "notifications" : get_notification_status(user.id)
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

def permission_denied_procedure(message, error_msg : str = ""):
    """Standard procedure, whenever a user doesn't have the permission to do a certain action"""
    bot_answer = f"Non hai il permesso di usare questo comando!\n{error_msg}"
    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer)

def send_on_off_notification(status : str):
    """Sends a notification whenever the bot turns on or off"""
    if not DEV_MODE:
        for user in users_table:
            bot_answer = f"Il bot è {status}!"
            try: 
                if user["chat_id"] and get_notification_status(user["user_id"]):
                    bot.send_message(user["chat_id"], bot_answer)
                    logger.info(f"Bot: {bot_answer}. chat_id: {user["chat_id"]}")
            except (KeyError, telebot.apihelper.ApiTelegramException): pass

def generate_random_name() -> str:
    """Return a random name between names from Italian, english, French, Ukranian, greek and japanese names"""
    langs = ["it_IT", "en_UK", "fr_Fr","uk_UA","el_GR","ja_JP"]
    lang = random.choice(langs)
    fake = faker.Faker(lang)
    if lang == "ja_JP":
        name = fake.first_romanized_name()
    else:
        name = fake.first_name()
        name = unidecode.unidecode(name)
    return name

def generate_qrcode(message,chat_id):
    """Generates a qr code from a string of text"""
    user = message.from_user
    bot_answer = "Inviato!"
    img_path = f"qr_{user.id}.png"
    img = qrcode.make(message.text)
    img.save(img_path)
    try:
        with open(img_path, "rb") as code:
            bot.send_photo(chat_id,code)
        os.remove(img_path)
    except Exception as e:
        bot_answer = f"errore, per favore invia questo a {get_viewed_name(OWNER_ID)}: \n{e}"
    bot.reply_to(message, bot_answer)
    logging_procedure(message,bot_answer)

def set_botname(message, us_id : int, randomName=False):
    """Updates the botname of the user identified by us_id"""
    MAX_CHARS = 200
    user = message.from_user
    name = message.text
    if randomName: name = generate_random_name()
    
    if len(name) > MAX_CHARS:
        bot_answer = f"Riesegui il comando usando meno caratteri. max: {MAX_CHARS}"
        bot.reply_to(message,bot_answer)
        logging_procedure(message,bot_answer)
        return
    
    if check_banned_name(name):
        bot_answer = f"Riesegui il comando usando un nome consentito"
        bot.reply_to(message,bot_answer)
        logging_procedure(message,bot_answer)
        return
    
    user_doc = users_table.search(User.user_id == us_id)
    if user_doc:
        target_viewed_name = get_viewed_name(us_id)
        user_doc[0]["bot_name"] = name
        if user.id == us_id:
            bot_answer = f"Il tuo nome è ora {name}"
        else:
            bot_answer = f"Il nome di {target_viewed_name} è ora {name}"
            user_data = { "bot_name" : name }
            users_table.upsert(user_data, User.user_id == us_id)

    else: bot_answer = "Utente non trovato"
    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer)

def reset_botname(message, us_id : int):
    """Reset the name of a user identified by us_id"""
    user_doc = users_table.search(User.user_id == us_id)
    if user_doc:
        target_name = user_doc[0]["first_name"]
        user_data = {"bot_name" : None}
        users_table.upsert(user_data, User.user_id == us_id)
        bot_answer = f"Nome di {target_name} resettato!"
    else:
        bot_answer = "Utente non trovato"
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

def set_permission(message,us_id : int):
    """Updates the status of a user from normal to restricted and vice versa"""
    if get_admin(us_id):
        permission_denied_procedure(message, denied_messages["target_admin"])
        return
    
    viewed_name = get_viewed_name(us_id)
    if get_permission(us_id) == True:
        bot_answer = f"Permessi di {viewed_name} bloccati!"
    else:
        bot_answer = f"Permessi di {viewed_name} sbloccati!"
    user_data = {
        "can_use_commands" : not get_permission(us_id)
        }
    users_table.upsert(user_data, User.user_id == us_id)
    bot.reply_to(message, bot_answer)
    logging_procedure(message,bot_answer)

def get_permission(us_id : int) -> bool:
    """Returns true if the user has a normal status, false if restricted """
    user_doc = users_table.search(User.user_id == us_id)
    if user_doc: 
        try: 
            return user_doc[0]["can_use_commands"]
        except KeyError:
            return True
    return True

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
    if get_admin(us_id) == True:
        bot_answer = f"{viewed_name} non è più admin!"
    else:
        bot_answer = f"{viewed_name} è ora admin!"
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
    sentence = message.text
    
    if len(sentence) > MAX_CHARS:
        bot_answer = f"Riesegui il comando usando meno caratteri. max: {MAX_CHARS}"
        bot.reply_to(message,bot_answer)
        logging_procedure(message, bot_answer)
        return
    
    if check_banned_name(sentence):
        bot_answer = f"Riesegui il comando usando una frase con termini consentiti"
        bot.reply_to(message,bot_answer)
        logging_procedure(message, bot_answer)
        return
    
    user_doc = users_table.search(User.user_id == us_id)
    if user_doc:
        target_viewed_name = get_viewed_name(us_id)
        if sentence.lower() == "none": sentence = None
        user_doc[0]["exclusive_sentence"] = sentence
        if user.id == us_id:
            bot_answer = f"La tua frase è ora {sentence}"
        else:
            bot_answer = f"La frase di {target_viewed_name} è ora {sentence}"
            user_data = {
                "exclusive_sentence" : sentence
            }
            users_table.upsert(user_data, User.user_id == us_id)

    else: bot_answer = "Utente non trovato"
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

    if user_doc:
        bot_answer = f"Nome utente: {user_doc[0]["first_name"]}\nCognome utente: {user_doc[0]["last_name"]}\nUsername: {user_doc[0]["username"]}\nUser ID: {user_doc[0]["user_id"]}\nNome in uso nel bot: {get_botname(us_id)}\nFrase personale: {get_excl_sentence(us_id)}\nNotifiche attivate: {get_notification_status(us_id)}\nAccount bloccato: {not get_permission(us_id)}\nAccount amministratore: {get_admin(us_id)}"
    else: bot_answer = "Utente non trovato"
    bot.reply_to(message, bot_answer)
    logging_procedure(message,bot_answer)

def send_message(message, chat_id : int):
    """Send a message to the chat identified by chat_id"""
    user = message.from_user
    bot_answer = "Inviato!"
    viewed_name = get_viewed_name(user.id)
    message_to_send = f"Da: {viewed_name}({user.id}):\n{message.text}"
    try:
        bot.send_message(chat_id,message_to_send)
    except telebot.apihelper.ApiTelegramException:
        bot_answer = "Errore, l'utente ha bloccato il bot"
    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer)

def broadcast(message, admin_only=False):
    """Send a message to all the users of the bot, or if admin only to just the admins"""
    user = message.from_user
    user_name = get_viewed_name(user.id)

    for user in users_table:
        bot_answer = f"Annuncio di {user_name}:\n{message.text}"
        if admin_only: bot_answer = f"Messaggio per gli admin di {user_name}:\n{message.text}"
        try: 
            if user["chat_id"]:
                if admin_only and user["admin_status"]:
                    bot.send_message(user["chat_id"], bot_answer)
                if not admin_only:
                    bot.send_message(user["chat_id"], bot_answer)
        except (KeyError, telebot.apihelper.ApiTelegramException): pass
    bot.reply_to(message,"Inviato!")
    logging_procedure(message,bot_answer)

def choose_text(message,command : callable):
    """Second step of the admin framework, it takes in the required text argument of certain commands"""
    user_doc = users_table.search(User.username == message.text)
    if user_doc:
        us_id = user_doc[0]["user_id"]
    else:
        user_doc = users_table.search(User.first_name == message.text)
        if user_doc:
            us_id = user_doc[0]["user_id"]
        else:
            bot_answer = "Utente non trovato"
            bot.reply_to(message, bot_answer, reply_markup=types.ReplyKeyboardRemove())
            return
    bot_answer = f"Utente selezionato {get_viewed_name(us_id)} ({us_id}). \nInserisci l'argomento:"

    if command == set_permission or command == reset_botname or command == set_admin or command == get_info:
        bot_answer = f"Utente selezionato {get_viewed_name(us_id)} ({us_id})."
        bot.reply_to(message, bot_answer, reply_markup=types.ReplyKeyboardRemove())
        command(message,us_id)
        return

    bot.reply_to(message, bot_answer, reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, command, us_id)
    logging_procedure(message,bot_answer)

def choose_target(message,command : callable):
    """First step of the admin framework, it specifies the user who the admin is targeting with its command. The admin framework let the admins reuse the functions written for normal use in a specific admin mode"""
    user = message.from_user
    bot_answer = f"Inserisci l'id dell'utente: "

    admin_status = get_admin(user.id)
    if not admin_status:
        permission_denied_procedure(message,denied_messages["admin_only"])
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
    banned_doc = banned_words_table.search(Word_type.type == word_type)
    if banned_doc:
        banned_list = banned_doc[0]["list"]
        if word in banned_list:
            bot_answer = "Parola già bannata"
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
    bot_answer = f"{word} bannata"
    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer)

def get_banned_words(word_type) -> list:
    """Return the list of a specified type of banned world"""
    banned_doc = banned_words_table.search(Word_type.type == word_type)
    if banned_doc: banned_list = banned_doc[0]["list"]
    else: banned_list = []
    return banned_list

bot.set_my_commands(commands)

send_on_off_notification("online")

@bot.message_handler(commands=["start","ciao"])
def send_welcome(message):
    """Greet the user with its name and a special sentence"""
    user = message.from_user
    if get_botname(user.id): viewed_name = get_botname(user.id)
    else: viewed_name = user.first_name

    if get_excl_sentence(user.id): special_reply = get_excl_sentence(user.id)
    else: special_reply = ""
    
    bot_answer = f"Ciao {viewed_name}!"
    try: bot_answer = f"{bot_answer}\n {special_reply}"
    except KeyError: pass

    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["setname"])
def set_name(message):
    user = message.from_user
    bot_answer = "Che nome vuoi usare?"

    current_permission = get_permission(user.id)
    if not current_permission:
        permission_denied_procedure(message,denied_messages["Blocked"])
        return
    
    bot.reply_to(message, bot_answer)
    bot.register_next_step_handler(message,set_botname,user.id)
    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["resetname"])
def reset_name(message):
    user = message.from_user
    current_permission = get_permission(user.id)
    if not current_permission:
        permission_denied_procedure(message,denied_messages["Blocked"])
        return
    
    reset_botname(message,user.id)

@bot.message_handler(commands=["sendtoowner"])
def send_to_owner(message):
    """Send a message to the owner of the bot"""
    user = message.from_user
    if get_botname(OWNER_ID): owner_name = get_botname(OWNER_ID)
    else: 
        owner_doc = users_table.search(User.user_id == OWNER_ID)
        if owner_doc: owner_name = owner_doc[0]["first_name"]
    bot_answer = f"Che messaggio vuoi inviare a {owner_name}?"

    current_permission = get_permission(user.id)
    if not current_permission:
        permission_denied_procedure(message,denied_messages["Blocked"])
        return
    
    bot.reply_to(message, bot_answer)
    bot.register_next_step_handler(message,send_message,OWNER_ID)
    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["sendtoadmin"])
def send_to_admin(message):
    """Send a message to all the admins of the bot"""
    user = message.from_user
    bot_answer = f"Che messaggio vuoi inviare agli admin?"

    current_permission = get_permission(user.id)
    if not current_permission:
        permission_denied_procedure(message, denied_messages["Blocked"])
        return
    
    bot.reply_to(message, bot_answer)
    bot.register_next_step_handler(message,broadcast,True)
    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["eventstoday"])
def events_on_wikipedia(message):
    """send a random event of the day from italian wikipedia"""
    wikipedia.set_lang("it")
    engToIta = {"January": "gennaio", "February" : "febbraio", "March" : "marzo", "April" : "aprile", "May" : "maggio", "June" : "giugno",
                "July" : "luglio", "August" : "agosto", "September" : "settembre", "October" : "ottobre" , "November" : "novembre", "December" : "dicembre"}
    page_title = f"{date.today().day}_{engToIta[date.today().strftime("%B")]}"
    try:
        page = wikipedia.page(page_title)
        content = page.section("Eventi")
        events_list = [line for line in content.split("\n")]
        event = random.choice(events_list)
        bot_answer = f"{event}"
    except wikipedia.exceptions.PageError:
        bot_answer = "pagina non trovata"
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
    current_permission = get_permission(user.id)
    if not current_permission:
        permission_denied_procedure(message, denied_messages["Blocked"])
        return
    
    set_botname(message,user.id,True)

@bot.message_handler(commands=["notifications"])
def set_notifications(message):
    user = message.from_user
    
    if get_notification_status(user.id):
        bot_answer = "Notifiche disattivate"
    else:
        bot_answer = "Notifiche attivate"

    user_data = {"notifications" : not get_notification_status(user.id)}
    users_table.upsert(user_data, User.user_id == user.id)
    bot.reply_to(message,bot_answer)

    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["qrcode"])
def request_qrcode(message):
    user = message.from_user
    chat_id = get_chat_id(user.id)
    current_permission = get_permission(user.id)
    if not current_permission:
        permission_denied_procedure(message, denied_messages["Blocked"])
        return
    
    bot_answer = "Inviami del testo e genererò un QR code"
    bot.reply_to(message,bot_answer)
    bot.register_next_step_handler(message, generate_qrcode,chat_id)
    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["info"])
def info(message):
    user = message.from_user
    get_info(message,user.id)

@bot.message_handler(commands=["about"])
def about(message):
    markup = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton("Github",url="github.com/Giu27/SupergiuToolsBot")
    markup.row(button)
    bot_answer = "IT: Bot sviluppato da @Supergiuchannel, il codice è disponibile su github.\nEN: Bot developed by @Supergiuchannel, the code is available on github."
    bot.reply_to(message,bot_answer, reply_markup=markup)
    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["setpersonname"])
def set_person_name(message):
    choose_target(message, set_botname)

@bot.message_handler(commands=["setpersonpermission"])
def set_person_permission(message):
    choose_target(message, set_permission)

@bot.message_handler(commands=["setpersonadmin"])
def set_person_admin(message):
    user = message.from_user
    if user.id != OWNER_ID:
        permission_denied_procedure(message, denied_messages["owner_only"])
        return
    choose_target(message, set_admin)

@bot.message_handler(commands=["setpersonsentence"])
def set_person_sentence(message):
    choose_target(message, set_excl_sentence)

@bot.message_handler(commands=["resetpersonname"])
def reset_person_name(message):
    choose_target(message, reset_botname)

@bot.message_handler(commands=["getpersoninfo"])
def get_person_info(message):
    choose_target(message,get_info)

@bot.message_handler(commands=["getids"])
def get_ids(message):
    user = message.from_user
    bot_answer = ""

    admin_status = get_admin(user.id)
    if not admin_status:
        permission_denied_procedure(message,denied_messages["admin_only"])
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
    choose_target(message,send_message)

@bot.message_handler(commands=["broadcast"])
def send_in_broadcast(message):
    user = message.from_user
    bot_answer = "Che messaggio vuoi inviare in broadcast"

    admin_status = get_admin(user.id)
    if not admin_status:
        permission_denied_procedure(message, denied_messages["admin_only"])
        return
    
    bot.reply_to(message, bot_answer)
    bot.register_next_step_handler(message,broadcast)
    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["addbanned"])
def add_banned_word(message):
    user = message.from_user
    bot_answer = "Che parola vuoi vietare?"

    admin_status = get_admin(user.id)
    if not admin_status:
        permission_denied_procedure(message, denied_messages["admin_only"])
        return
    
    bot.reply_to(message, bot_answer)
    bot.register_next_step_handler(message,update_banned_words,"banned")
    logging_procedure(message,bot_answer)

@bot.message_handler(commands=["addultrabanned"])
def add_ultra_banned_word(message):
    user = message.from_user
    bot_answer = "Che parola vuoi iper vietare?"

    admin_status = get_admin(user.id)
    if not admin_status:
        permission_denied_procedure(message, denied_messages["admin_only"])
        return
    
    bot.reply_to(message, bot_answer)
    bot.register_next_step_handler(message,update_banned_words,"ultrabanned")
    logging_procedure(message,bot_answer)

@bot.message_handler(content_types=["photo","video","sticker","animation","document","audio","voice"])
def handle_media(message):
    user = message.from_user
    bot_answer = f"Ciao {get_viewed_name(user.id)}, ho perso gli occhiali e non posso visualizzare questo contenuto"
    if (message.voice or message.audio): bot_answer = f"Ciao {get_viewed_name(user.id)}, ho perso le cuffie e non posso ascoltare questo contenuto"
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
    logger.info(f"{user.id}, {user_info}: {message.text}")
    log_file.write(f"{user.id}, {user_info}: {message.text}\n")
    
bot.infinity_polling()

send_on_off_notification("offline")

db.close()