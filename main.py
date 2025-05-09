import telebot, os, logging, json, wikipedia, random, faker, unidecode
from dotenv import load_dotenv
from tinydb import TinyDB, Query
from telebot import types
from datetime import date

load_dotenv()

DEV_MODE = False
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GIU_ID = int(os.environ.get("GIU_ID"))
bot = telebot.TeleBot(BOT_TOKEN)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
log_path = "logs"

db = TinyDB("User_info.JSON")
users_table = db.table("users")
User = Query()

banned_words_str = os.environ.get("banned_words")
ultra_banned_words_str = os.environ.get("ultra_banned_words")
banned_words = []
ultra_banned_words = []

if banned_words_str:
    try:
        banned_words = json.loads(banned_words_str)
    except json.JSONDecodeError: print("ERRORE CARICAMENTO PAROLE VIETATE")

if ultra_banned_words_str:
    try:
        ultra_banned_words = json.loads(ultra_banned_words_str)
    except json.JSONDecodeError: print("ERRORE CARICAMENTO PAROLE ULTRA VIETATE")

commands = [
    types.BotCommand("ciao","Saluta l'utente "),
    types.BotCommand("setname","Modifica il tuo nome"),
    types.BotCommand("resetname","Ripristina il tuo nome originale"),
    types.BotCommand("sendtogiu","Invia un messaggio a Supergiu"),
    types.BotCommand("eventstoday","Restituisce curiosità storiche sulla data di oggi"),
    types.BotCommand("randomnumber","Restituisce un numero casuale tra 0 e 999"),
    types.BotCommand("randomname","Imposta un nome casuale")
]

def store_user_data(user, bot_name, chat_id,cmd_perm,excl_sen):
    user_data = {
        "user_id" : user.id,
        "first_name" : user.first_name,
        "last_name" : user.last_name,
        "username" : user.username,
        "is_bot" : user.is_bot,
        "bot_name" : bot_name,
        "chat_id" : chat_id,
        "can_use_commands" : cmd_perm,
        "exclusive_sentence" : excl_sen
        }
    users_table.upsert(user_data, User.user_id == user.id)

def check_banned_name(name):
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

def logging_procedure(message,bot_answer,log_file):
    """Procedura standard di log in tutte le funzioni"""
    log(message)
    logger.info(f"Bot: {bot_answer}")
    log_file.write(f"Bot: {bot_answer}\n")

def generate_random_name():
    langs = ["it_IT", "en_UK", "fr_Fr","uk_UA","el_GR","ja_JP"]
    lang = random.choice(langs)
    fake = faker.Faker(lang)
    if lang == "ja_JP":
        name = fake.first_romanized_name()
    else:
        name = fake.first_name()
        name = unidecode.unidecode(name)
    return name

def set_botname(message, us_id, randomName=False):
    MAX_CHARS = 200
    user = message.from_user
    name = message.text
    if randomName: name = generate_random_name()
    log_file = open(f"{log_path}/{user.id}.txt","a")
    
    if len(name) > MAX_CHARS:
        bot_answer = f"Riesegui il comando usando meno caratteri. max: {MAX_CHARS}"
        bot.reply_to(message,bot_answer)
        logging_procedure(message,bot_answer,log_file)
        return
    
    if check_banned_name(name):
        bot_answer = f"Riesegui il comando usando un nome consentito"
        bot.reply_to(message,bot_answer)
        logging_procedure(message,bot_answer,log_file)
        return
    
    user_doc = users_table.search(User.user_id == us_id)
    if user_doc:
        if get_botname(us_id): target_viewed_name = get_botname(us_id)
        else: target_viewed_name = user_doc[0]["first_name"]
        user_doc[0]["bot_name"] = name
        if user.id == us_id:
            bot_answer = f"Il tuo nome è ora {name}"
        else:
            bot_answer = f"Il nome di {target_viewed_name} è ora {name}"
            user_data = {
                "bot_name" : name
            }
            users_table.upsert(user_data, User.user_id == us_id)

    else: bot_answer = "Utente non trovato"
    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer,log_file)

def reset_botname(message, us_id, bypass=False):
    user = message.from_user
    log_file = open(f"{log_path}/{user.id}.txt","a")
    current_permission = get_permission(user.id)

    if not current_permission and not bypass:
        bot_answer = "Non hai il permesso di usare questo comando"
        bot.reply_to(message,bot_answer)
        log(message)
        logger.info(f"Bot: {bot_answer}")
        log_file.write(f"Bot: {bot_answer}\n")
        return
    
    user_doc = users_table.search(User.user_id == us_id)
    if user_doc:
        target_name = user_doc[0]["first_name"]
        user_data = {"bot_name" : None}
        users_table.upsert(user_data, User.user_id == us_id)
        bot_answer = f"Nome di {target_name} resettato!"
    else:
        bot_answer = "Utente non trovato"
    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer,log_file)

def get_botname(us_id):
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

def set_permission(message,us_id):
    user = message.from_user
    log_file = open(f"{log_path}/{user.id}.txt","a")
    if get_botname(us_id): viewed_name = get_botname(us_id)
    else: 
        us_doc = users_table.search(User.user_id == us_id)
        if us_doc: viewed_name = us_doc[0]["first_name"]
    if get_permission(us_id) == True:
        bot_answer = f"Permessi di {viewed_name} bloccati!"
    else:
        bot_answer = f"Permessi di {viewed_name} sbloccati!"
    user_data = {
        "can_use_commands" : not get_permission(us_id)
        }
    users_table.upsert(user_data, User.user_id == us_id)
    bot.reply_to(message, bot_answer)
    logging_procedure(message,bot_answer,log_file)

def get_permission(us_id):
    user_doc = users_table.search(User.user_id == us_id)
    if user_doc: 
        try: 
            return user_doc[0]["can_use_commands"]
        except KeyError:
            return None
    return None

def set_excl_sentence(message, us_id):
    MAX_CHARS = 200
    user = message.from_user
    sentence = message.text
    current_permission = get_permission(user.id)
    log_file = open(f"{log_path}/{user.id}.txt","a")

    if not current_permission:
        bot_answer = "Non hai il permesso di usare questo comando"
        bot.reply_to(message,bot_answer)
        log(message)
        logger.info(f"Bot: {bot_answer}")
        log_file.write(f"Bot: {bot_answer}\n")
        return
    
    if len(sentence) > MAX_CHARS:
        bot_answer = f"Riesegui il comando usando meno caratteri. max: {MAX_CHARS}"
        bot.reply_to(message,bot_answer)
        log(message)
        logger.info(f"Bot: {bot_answer}")
        log_file.write(f"Bot: {bot_answer}\n")
        return
    
    if check_banned_name(sentence):
        bot_answer = f"Riesegui il comando usando una frase con termini consentiti"
        bot.reply_to(message,bot_answer)
        log(message)
        logger.info(f"Bot: {bot_answer}")
        log_file.write(f"Bot: {bot_answer}\n")
        return
    
    user_doc = users_table.search(User.user_id == us_id)
    if user_doc:
        if get_botname(us_id): target_viewed_name = get_botname(us_id)
        else: target_viewed_name = user_doc[0]["first_name"]
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
    logging_procedure(message,bot_answer,log_file)

def get_excl_sentence(us_id):
    user_doc = users_table.search(User.user_id == us_id)
    if user_doc: 
        try: 
            return user_doc[0]["exclusive_sentence"]
        except KeyError:
            return None
    return None

def send_message(message, chat_id):
    user = message.from_user
    log_file = open(f"{log_path}/{user.id}.txt","a")
    bot_answer = "Inviato!"
    if get_botname(user.id): viewed_name = get_botname(user.id)
    else: viewed_name = user.first_name
    message_to_send = f"Da: {viewed_name}:\n{message.text}"
    bot.send_message(chat_id,message_to_send)
    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer,log_file)

def broadcast(message):
    user = message.from_user
    log_file = open(f"{log_path}/{user.id}.txt","a")
    if get_botname(GIU_ID): giu_name = get_botname(GIU_ID)
    else: 
        giu_doc = users_table.search(User.user_id == GIU_ID)
        if giu_doc: giu_name = giu_doc[0]["first_name"]
    for user in users_table:
        bot_answer = f"Annuncio di {giu_name}:\n{message.text}"
        try: 
            if user["chat_id"]:
                bot.send_message(user["chat_id"], bot_answer)
        except KeyError: pass
    logging_procedure(message,bot_answer,log_file)

def choose_text(message,command):
    user = message.from_user
    log_file = open(f"{log_path}/{user.id}.txt","a")
    bot_answer = f"Inserisci l'argomento: "
    us_id = int(message.text)

    current_permission = get_permission(user.id)
    if not current_permission or user.id != GIU_ID:
        bot_answer = "Non hai il permesso di usare questo comando"
        bot.reply_to(message,bot_answer)
        log(message)
        logger.info(f"Bot: {bot_answer}")
        log_file.write(f"Bot: {bot_answer}\n")
        return
    
    if command == set_permission or command == reset_botname:
        command(message,int(message.text))
        return

    bot.reply_to(message, bot_answer)
    bot.register_next_step_handler(message, command, us_id)
    logging_procedure(message,bot_answer,log_file)

def choose_target(message,command):
    user = message.from_user
    log_file = open(f"{log_path}/{user.id}.txt","a")
    bot_answer = f"Inserisci l'id dell'utente: "

    current_permission = get_permission(user.id)
    if not current_permission or user.id != GIU_ID:
        bot_answer = "Non hai il permesso di usare questo comando"
        bot.reply_to(message,bot_answer)
        log(message)
        logger.info(f"Bot: {bot_answer}")
        log_file.write(f"Bot: {bot_answer}\n")
        return

    bot.reply_to(message, bot_answer)
    bot.register_next_step_handler(message, choose_text,command)
    logging_procedure(message,bot_answer,log_file)

bot.set_my_commands(commands)

if not DEV_MODE:
    for user in users_table:
        bot_answer = "Il bot è online!"
        try: 
            if user["chat_id"]:
                bot.send_message(user["chat_id"], bot_answer)
                logger.info(f"Bot: {bot_answer}. chat_id: {user["chat_id"]}")
        except KeyError: pass

@bot.message_handler(commands=["start","ciao"])
def send_welcome(message):
    user = message.from_user
    log_file = open(f"{log_path}/{user.id}.txt","a")
    if get_botname(user.id): viewed_name = get_botname(user.id)
    else: viewed_name = user.first_name

    if get_excl_sentence(user.id): special_reply = get_excl_sentence(user.id)
    else: special_reply = ""
    
    bot_answer = f"Ciao {viewed_name}!"
    try: bot_answer = f"{bot_answer}\n {special_reply}"
    except KeyError: pass

    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer,log_file)

@bot.message_handler(commands=["setname"])
def set_name(message):
    user = message.from_user
    log_file = open(f"{log_path}/{user.id}.txt","a")
    bot_answer = "Che nome vuoi usare?"

    current_permission = get_permission(user.id)
    if not current_permission:
        bot_answer = "Non hai il permesso di usare questo comando"
        bot.reply_to(message,bot_answer)
        logging_procedure(message,bot_answer,log_file)
        return
    
    bot.reply_to(message, bot_answer)
    bot.register_next_step_handler(message,set_botname,user.id)
    logging_procedure(message,bot_answer,log_file)

@bot.message_handler(commands=["resetname"])
def reset_name(message):
    user = message.from_user
    reset_botname(message,user.id)

@bot.message_handler(commands=["sendtogiu"])
def send_to_giu(message):
    user = message.from_user
    log_file = open(f"{log_path}/{user.id}.txt","a")
    if get_botname(GIU_ID): giu_name = get_botname(GIU_ID)
    else: 
        giu_doc = users_table.search(User.user_id == GIU_ID)
        if giu_doc: giu_name = giu_doc[0]["first_name"]
    bot_answer = f"Che messaggio vuoi inviare a {giu_name}?"

    current_permission = get_permission(user.id)
    if not current_permission:
        bot_answer = "Non hai il permesso di usare questo comando"
        bot.reply_to(message,bot_answer)
        logging_procedure(message,bot_answer,log_file)
        return
    
    bot.reply_to(message, bot_answer)
    bot.register_next_step_handler(message,send_message,GIU_ID)
    logging_procedure(message,bot_answer,log_file)

@bot.message_handler(commands=["eventstoday"])
def events_on_wikipedia(message):
    user = message.from_user
    log_file = open(f"{log_path}/{user.id}.txt","a")
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
    logging_procedure(message,bot_answer,log_file)

@bot.message_handler(commands=["randomnumber"])
def random_number(message):
    user = message.from_user
    log_file = open(f"{log_path}/{user.id}.txt","a")
    bot_answer = random.randrange(0,999)
    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer,log_file)

@bot.message_handler(commands=["randomname"])
def random_name(message):
    user = message.from_user
    set_botname(message,user.id,True)

@bot.message_handler(commands=["setpersonname"])
def set_person_name(message):
    choose_target(message, set_botname)

@bot.message_handler(commands=["setpersonpermission"])
def set_person_permission(message):
    choose_target(message, set_permission)

@bot.message_handler(commands=["setpersonsentence"])
def set_person_sentence(message):
    choose_target(message, set_excl_sentence)

@bot.message_handler(commands=["resetpersonname"])
def reset_person_name(message):
    choose_target(message, reset_botname)

@bot.message_handler(commands=["getids"])
def get_ids(message):
    user = message.from_user
    log_file = open(f"{log_path}/{user.id}.txt","a")
    bot_answer = ""

    current_permission = get_permission(user.id)
    if not current_permission or user.id != GIU_ID:
        bot_answer = "Non hai il permesso di usare questo comando"
        bot.reply_to(message,bot_answer)
        logging_procedure(message,bot_answer,log_file)
        return
    
    for user in users_table:
        try: 
            if user["user_id"]:
                bot_answer += f"{user["user_id"]}: {user["first_name"]} {user["last_name"]}\nBotname: {get_botname(user["user_id"])}\n\n"
        except KeyError: pass

    bot.reply_to(message,bot_answer)
    logging_procedure(message,bot_answer,log_file)

@bot.message_handler(commands=["sendto"])
def send_to_target(message):
    choose_target(message,send_message)

@bot.message_handler(commands=["broadcast"])
def send_in_broadcast(message):
    user = message.from_user
    log_file = open(f"{log_path}/{user.id}.txt","a")
    bot_answer = "Che messaggio vuoi inviare in broadcast"

    current_permission = get_permission(user.id)
    if not current_permission or user.id != GIU_ID:
        bot_answer = "Non hai il permesso di usare questo comando"
        bot.reply_to(message,bot_answer)
        logging_procedure(message,bot_answer,log_file)
        return
    
    bot.reply_to(message, bot_answer)
    bot.register_next_step_handler(message,broadcast)
    logging_procedure(message,bot_answer,log_file)
    
@bot.message_handler(commands=["francescosegreto"])
def set_owner_name(message):
    user = message.from_user
    log_file = open(f"{log_path}/{user.id}.txt","a")
    if get_botname(GIU_ID): giu_name = get_botname(GIU_ID)
    else: 
        giu_doc = users_table.search(User.user_id == GIU_ID)
        if giu_doc: giu_name = giu_doc[0]["first_name"]
    bot_answer = f"Che nome vuoi dare a {giu_name}?"

    current_permission = get_permission(user.id)
    if not current_permission:
        bot_answer = "Non hai il permesso di usare questo comando"
        bot.reply_to(message,bot_answer)
        logging_procedure(message,bot_answer,log_file)
        return
    
    bot.reply_to(message, bot_answer)
    bot.register_next_step_handler(message,set_botname,GIU_ID)
    logging_procedure(message,bot_answer,log_file)

@bot.message_handler(commands=["francescovieri"])
def set_owner_permission(message):
    user = message.from_user
    log_file = open(f"{log_path}/{user.id}.txt","a")

    current_permission = get_permission(user.id)
    if not current_permission:
        bot_answer = "Non hai il permesso di usare questo comando"
        bot.reply_to(message,bot_answer)
        logging_procedure(message,bot_answer,log_file)
        return
    
    set_permission(message,GIU_ID)

@bot.message_handler(commands=["francescosupergiu"])
def set_owner_sentence(message):
    user = message.from_user
    log_file = open(f"{log_path}/{user.id}.txt","a")
    if get_botname(GIU_ID): giu_name = get_botname(GIU_ID)
    else: 
        giu_doc = users_table.search(User.user_id == GIU_ID)
        if giu_doc: giu_name = giu_doc[0]["first_name"]
    bot_answer = f"Che frase vuoi dare a {giu_name} durante il saluto?"

    current_permission = get_permission(user.id)
    if not current_permission:
        bot_answer = "Non hai il permesso di usare questo comando"
        bot.reply_to(message,bot_answer)
        logging_procedure(message,bot_answer,log_file)
        return
    
    bot.reply_to(message, bot_answer)
    bot.register_next_step_handler(message,set_excl_sentence,GIU_ID)
    logging_procedure(message,bot_answer,log_file)

@bot.message_handler(func= lambda commands:True)
def log(message):
    user = message.from_user
    log_file = open(f"{log_path}/{user.id}.txt","a")
    current_permission = get_permission(user.id)
    current_sentence = get_excl_sentence(user.id)
    if current_permission == None: current_permission = True
    botname = get_botname(user.id)
    store_user_data(user,botname,message.chat.id,current_permission,current_sentence)
    if user.username: user_info = user.username
    else: user_info = f"{user.first_name} {user.last_name}"
    logger.info(f"{user.id}, {user_info}: {message.text}")
    log_file.write(f"{user.id}, {user_info}: {message.text}\n")
    
bot.infinity_polling()

if not DEV_MODE:
    for user in users_table:
        bot_answer = "Il bot è offline!"
        try: 
            if user["chat_id"]:
                bot.send_message(user["chat_id"], bot_answer)
                logger.info(f"Bot: {bot_answer}. chat_id: {user["chat_id"]}")
        except KeyError: pass