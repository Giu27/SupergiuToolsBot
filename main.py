#Copyright (C) 2025  Giuseppe Caruso
import telebot, os, logging, qrcode, wikipedia, random, faker, unidecode, asyncio, aiofiles
from telebot.async_telebot import AsyncTeleBot
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
        doc = await self.tables[table].get(condition)
        if doc:
            if attribute: 
                try: return doc[attribute]
                except KeyError: return None
        return doc

    async def get_docs(self, table : str, condition) -> list:
        "Returns a list of all documents in  table matching a conditions"
        docs = await self.tables[table].search(condition)
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

class Bot(AsyncTeleBot):
    def __init__(self, token, owner_id, db_path, log_path="logs", log=False, dev_mode=False, commands=commands, languages={"en" : "English", "it" : "Italiano"}, localizations=localizations):
        super().__init__(token)
        self.OWNER_ID = owner_id
        self.db = Bot_DB_Manager(db_path, "users", "banned_words", "custom_commands")
        self.log_path = log_path
        os.makedirs(self.log_path, exist_ok=True)
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        self.LOG = log
        self.DEV_MODE = dev_mode

        self.languages = languages
        self.commands = commands
        self.localizations = localizations
        self.functions = {"validate_target" : self.validate_target, "set_botname" : self.set_botname, "send_message_to" : self.send_message_to, "broadcast" : self.broadcast, "generate_qrcode" : self.generate_qrcode, "reset_botname" : self.reset_botname,
                    "ask_custom_command_content" : self.ask_custom_command_content, "add_custom_command" : self.add_custom_command, "remove_custom_command" : self.remove_custom_command, "set_excl_sentence" : self.set_excl_sentence,
                    "set_permission" : self.set_permission, "set_user_lang" : self.set_user_lang, "set_gender" : self.set_gender, "get_info" : self.get_info, "get_permissions_list" : self.get_permissions_list, "set_admin" : self.set_admin,
                    "add_banned_words" : self.add_banned_words, "remove_banned_words" : self.remove_banned_words, "handle_multiple_users" : self.handle_multiple_users}
        
        self.register_message_handler(self.send_greets, commands=["start", "hello"])
        self.register_message_handler(self.set_user_lang, commands=["lang"])
        self.register_message_handler(self.set_name, commands=["setname"])
        self.register_message_handler(self.reset_name, commands=["resetname"])
        self.register_message_handler(self.send_to_owner, commands=["sendtoowner"])
        self.register_message_handler(self.send_to_admin, commands=["sendtoadmin"])
        self.register_message_handler(self.events_on_wikipedia, commands=["eventstoday"])
        self.register_message_handler(self.set_user_gender, commands=["gender"])
        self.register_message_handler(self.random_number, commands=["randomnumber"])
        self.register_message_handler(self.random_name, commands=["randomname"])
        self.register_message_handler(self.request_qrcode, commands=["qrcode"])
        self.register_message_handler(self.set_notifications, commands=["notifications"])
        self.register_message_handler(self.info, commands=["info"])
        self.register_message_handler(self.permissions_list, commands=["permissionlist"])
        self.register_message_handler(self.cancel_command, commands=["cancel"])
        self.register_message_handler(self.about, commands=["about"])
        self.register_message_handler(self.get_person_info, commands=["getpersoninfo"])
        self.register_message_handler(self.set_person_name, commands=["setpersonname"])
        self.register_message_handler(self.reset_person_name, commands=["resetpersonname"])
        self.register_message_handler(self.set_person_permission, commands=["setpersonpermission"])
        self.register_message_handler(self.get_person_permissions, commands=["getpersonpermission"])
        self.register_message_handler(self.set_person_admin, commands=["setpersonadmin"])
        self.register_message_handler(self.set_person_admin, commands=["setpersonsentence"])
        self.register_message_handler(self.set_person_lang, commands=["setpersonlang"])
        self.register_message_handler(self.set_person_gender, commands=["setpersongender"])
        self.register_message_handler(self.get_ids, commands=["getids"])
        self.register_message_handler(self.send_to_target, commands=["sendto"])
        self.register_message_handler(self.send_in_broadcast, commands=["broadcast"])
        self.register_message_handler(self.add_banned, commands=["addbanned"])
        self.register_message_handler(self.remove_banned, commands=["removebanned"])
        self.register_message_handler(self.add_ultra_banned, commands=["addultrabanned"])
        self.register_message_handler(self.remove_ultra_banned, commands=["removeultrabanned"])
        self.register_message_handler(self.get_command_list, commands=["getcommandslist"])
        self.register_message_handler(self.add_command, commands=["addcommand"])
        self.register_message_handler(self.remove_command, commands=["removecommand"])
        self.register_message_handler(self.handle_custom_commands, func= lambda message: message.text.startswith('/'))
        self.register_message_handler(self.handle_events, content_types=["text","photo", "video", "sticker", "animation", "document", "audio", "voice"],func= lambda commands:True)
        self.register_callback_query_handler(self.handle_lang_buttons, func=lambda call: call.data.startswith("lang_"))

    async def store_user_data(self, user, chat_id : int):
        """Creates and updates the user data in the database"""
        user_data = {
            "user_id" : user.id,
            "first_name" : user.first_name,
            "last_name" : user.last_name,
            "username" : user.username,
            "is_bot" : user.is_bot,
            "bot_name" : await self.get_botname(user.id),
            "chat_id" : chat_id,
            "commands" : await self.get_permission(user.id),
            "admin_status" : await self.get_admin(user.id),
            "exclusive_sentence" : await self.get_excl_sentence(user.id),
            "notifications" : await self.get_notification_status(user.id),
            "localization" : await self.get_lang(user.id),
            "gender" : await self.get_gender(user.id),
            "event" : await self.get_event(user.id)
            }
        await self.db.upsert_values("users", user_data, self.db.query.user_id == user.id)

    async def check_banned_name(self, name : str) -> bool:
        """Return true if name is banned, false otherwise"""
        banned_words = await self.get_banned_words("banned")
        ultra_banned_words = await self.get_banned_words("ultrabanned")
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

    async def logging_procedure(self, message, bot_answer : str):
        """Standard logging, to a file and console, of the user and bot messages not registered by log function automatically"""
        if self.LOG:
            await self.log_and_update(message)
            self.logger.info(f"Bot: {bot_answer}")
            async with aiofiles.open(f"{self.log_path}/{message.from_user.id}.txt", "a") as log_file:
                await log_file.write(f"Bot: {bot_answer}\n")

    def get_localized_string(self, source : str, lang : str, element : str = None) -> str:
        """Returns the string from localizations.py in localizations[source][lang] and optionally elements"""
        try:
            if element: return self.localizations[source][lang][element]
            return self.localizations[source][lang]
        except KeyError:
            try: return self.localizations["not_found"][lang]
            except KeyError: return self.localizations["not_found"]["en"]

    async def permission_denied_procedure(self, message, error_msg : str = ""):
        """Standard procedure, whenever a user doesn't have the permission to do a certain action"""
        user = message.from_user
        lang = await self.get_lang(user.id)
        bot_answer = f"{self.get_localized_string("permission_denied", lang, "default")}\n{self.get_localized_string("permission_denied", lang, str(error_msg))}"
        await self.reply_to(message, bot_answer)
        await self.logging_procedure(message, bot_answer)

    async def send_on_off_notification(self, status : str):
        """Sends a notification whenever the bot turns on or off"""
        if not self.DEV_MODE:
            async for user in self.db.tables["users"]:
                bot_answer = f"{self.get_localized_string("notifications", await self.get_lang(user["user_id"]), "bot")} {status}!"
                try: 
                    if user["chat_id"] and await self.get_notification_status(user["user_id"]):
                        await self.send_message(user["chat_id"], bot_answer)
                        if self.LOG: self.logger.info(f"Bot: {bot_answer}. chat_id: {user["chat_id"]}")
                except (KeyError, telebot.apihelper.ApiTelegramException): pass

    def generate_random_name(self, gender : str) -> str:
        """Return a random name between names from Italian, english, French, Ukranian, greek and japanese names"""
        langs = ["it_IT", "en_UK", "fr_Fr", "uk_UA", "el_GR", "ja_JP"]
        lang = random.choice(langs)
        fake = faker.Faker(lang)

        if lang == "ja_JP":
            if gender == 'f': name = fake.first_romanized_name_female()
            elif gender == 'm': name = fake.first_romanized_name_male()
            else: name = random.choice([fake.first_romanized_name_male(), fake.first_romanized_name_female()])
        else:
            if gender == 'f': name = fake.first_name_female()
            elif gender == 'm': name = fake.first_name_male()
            else: name = fake.first_name_nonbinary()
            name = unidecode.unidecode(name)
        return name

    async def generate_qrcode(self, message, chat_id : int):
        """Generates a qr code from a string of text"""
        user = message.from_user
        lang = await self.get_lang(user.id)
        bot_answer = self.get_localized_string("sent", lang)
        img_path = f"qr_{user.id}.png"

        img = qrcode.make(message.text)
        img.save(img_path)
        try:
            with open(img_path, "rb") as code:
                await self.send_photo(chat_id, code)
            os.remove(img_path)
        except Exception as e: bot_answer = f"{self.get_localized_string("qrcode", lang, "error")} {await self.get_viewed_name(self.OWNER_ID)}: \n{e}"
        await self.reply_to(message, bot_answer)
        await self.logging_procedure(message, bot_answer)

    async def validate_name(self, message, name : str, type : str = "name", max_chars : int = 200) -> bool:
        """Validates a name (or a sentence), return True if the name is valid"""
        user = message.from_user
        lang = await self.get_lang(user.id)

        if len(name) > max_chars:
            bot_answer = f"{self.get_localized_string("set_name", lang, "max_chars")} Max: {max_chars}"
            await self.reply_to(message, bot_answer)
            await self.logging_procedure(message, bot_answer)
            return False
        
        if await self.check_banned_name(name):
            bot_answer = self.get_localized_string("set_name", lang, "name_banned") if type == "name" else self.get_localized_string("set_sentence", lang, "sentence_banned")
            await self.reply_to(message, bot_answer)
            await self.logging_procedure(message, bot_answer)
            return False
        
        return True

    async def get_botname(self, us_id : int) -> str | None:
        """Returns the botname of the user identified by us_id"""
        botname = await self.db.get_single_doc("users", self.db.query.user_id == us_id, "bot_name")
        if botname: 
            if await self.check_banned_name(botname):
                botname = None
                await self.db.upsert_values("users", {"bot_name" : botname}, self.db.query.user_id == us_id)
        return botname

    async def set_botname(self, message, us_id : int, randomName=False):
        """Updates the botname of the user identified by us_id"""
        user = message.from_user
        name = message.text
        lang = await self.get_lang(user.id)
        if randomName or name == "-r": name = self.generate_random_name(await self.get_gender(us_id))
        
        if not await self.validate_name(message, name): return
        
        target_viewed_name = await self.get_viewed_name(us_id)
        if user.id == us_id: bot_answer = f"{self.get_localized_string("set_name", lang, "personal_name")} {name}"
        else: bot_answer = f"{self.get_localized_string("set_name", lang, "name_of")} {target_viewed_name} {self.get_localized_string("set_name", lang, "is_now")} {name}"
        await self.db.upsert_values("users", {"bot_name" : name}, self.db.query.user_id == us_id)

        await self.reply_to(message, bot_answer)
        await self.logging_procedure(message, bot_answer)

    async def reset_botname(self, message, us_id : int):
        """Reset the name of a user identified by us_id"""
        target_name = await self.db.get_single_doc("users", self.db.query.user_id == us_id, "first_name")
        user = message.from_user
        lang = await self.get_lang(user.id)

        await self.db.upsert_values("users", {"bot_name" : None}, self.db.query.user_id == us_id)
        bot_answer = f"{self.get_localized_string("set_name", lang, "name_of")} {target_name} {self.get_localized_string("set_name", lang, "resetted")}"

        await self.reply_to(message, bot_answer)
        await self.logging_procedure(message, bot_answer)

    async def get_viewed_name(self, us_id : int) -> str | None:
        """Returns the currently visualized name in the bot"""
        if await self.get_botname(us_id): user_name = await self.get_botname(us_id)
        else: user_name = await self.db.get_single_doc("users", self.db.query.user_id == us_id, "first_name")
        return user_name

    async def get_chat_id(self, us_id : int) -> int | None:
        """Return the chat id stored in the database"""
        return await self.db.get_single_doc("users", self.db.query.user_id == us_id, "chat_id")

    async def get_permission(self, us_id : int, command : str = None) -> bool | dict | str:
        """Returns true if the user can use a command, false if restricted. If no command is specified returns a dict"""
        if not await self.db.contains("users", self.db.query.user_id == us_id): return "not_found"
        commands = await self.db.get_single_doc("users", self.db.query.user_id == us_id, "commands")
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
            await self.db.upsert_values("users", {"commands" : data}, self.db.query.user_id == us_id)
            return True
        except TypeError:
            await self.db.upsert_values("users", {"commands" : {}}, self.db.query.user_id == us_id)
            return await self.get_permission(us_id, command)

    async def set_permission(self, message, us_id : int):
        """Updates the status of a command for the user identified by us_id"""
        user = message.from_user
        if await self.get_admin(us_id) and us_id != user.id and user.id != self.OWNER_ID:
            await self.permission_denied_procedure(message, "target_admin")
            return
        
        viewed_name = await self.get_viewed_name(us_id)
        user = message.from_user
        lang = await self.get_lang(user.id)
        if await self.get_permission(us_id, message.text) == True: bot_answer = f"{self.get_localized_string("permission", lang, "permission_of")} {viewed_name} {self.get_localized_string("permission", lang, "locked")}"
        else: bot_answer = f"{self.get_localized_string("permission", lang, "permission_of")} {viewed_name} {self.get_localized_string("permission", lang, "unlocked")}"

        permissions = await self.get_permission(us_id)

        if us_id == user.id and not permissions[message.text] and us_id != self.OWNER_ID:
            await self.permission_denied_procedure(message, "admin_only")
            return

        permissions[message.text] = not await self.get_permission(us_id, message.text)
        await self.db.upsert_values("users", {"commands" : permissions}, self.db.query.user_id == us_id)

        await self.reply_to(message, bot_answer, reply_markup=types.ReplyKeyboardRemove())
        await self.logging_procedure(message, bot_answer)

    async def get_permissions_list(self, message, us_id : int):
        """Shows the status of all the commands that can be restricted for the user identified by us_id"""
        user = message.from_user
        lang = await self.get_lang(user.id)

        if await self.get_permission(us_id):
            bot_answer = f"{self.get_localized_string("permission", lang, "list")} {await self.get_viewed_name(us_id)}: \n"
            for command, permission in (await self.get_permission(us_id)).items():
                bot_answer += f"{command}: {permission};\n"
        else: bot_answer = self.get_localized_string("choose_argument", lang, "not_found")

        await self.reply_to(message, bot_answer)
        await self.logging_procedure(message, bot_answer)

    async def handle_lang_buttons(self, call):
        user = call.from_user
        await self.answer_callback_query(call.id)
        data = call.data.split("_")
        us_id = int(data[1])
        await self.set_lang(us_id, data[2])
        await self.edit_message_text(f"{await self.get_viewed_name(us_id)} {self.get_localized_string("set_lang", await self.get_lang(user.id), "confirmation")} {self.languages[data[2]]}.", call.message.chat.id, call.message.id)

    async def get_lang(self, us_id : int) -> str:
        """Returns the user language code, if not found defaults to en"""
        localization = await self.db.get_single_doc("users", self.db.query.user_id == us_id, "localization")
        if localization: return localization
        else: return self.languages[0]

    async def set_lang(self, us_id : int, lang : str):
        """Change the bot language, for the user identified by us_id"""
        await self.db.upsert_values("users", {"localization" : lang}, self.db.query.user_id == us_id)

    async def get_gender(self, us_id : int) -> str:
        """Returns the user gender, if not found defaults to m(ale)"""
        gender = await self.db.get_single_doc("users", self.db.query.user_id == us_id, "gender")
        if gender: return gender
        else: return 'm'

    async def set_gender(self, message, us_id : int):
        """Change the gender of the name chosen by randomname, for the user identified by us_id"""
        viewed_name = await self.get_viewed_name(us_id)
        user = message.from_user
        lang = await self.get_lang(user.id)
        if await self.get_gender(us_id) == 'm':
            bot_answer = f"{viewed_name} {self.get_localized_string("set_gender", lang, 'f')}"
            gender = 'f'
        elif await self.get_gender(us_id) == 'f':
            bot_answer = f"{viewed_name} {self.get_localized_string("set_gender", lang, 'nb')}"
            gender = 'nb'
        else:
            bot_answer = f"{viewed_name} {self.get_localized_string("set_gender", lang, 'm')}"
            gender = 'm'
    
        await self.db.upsert_values("users", {"gender" : gender}, self.db.query.user_id == us_id)
        await self.reply_to(message, bot_answer)
        await self.logging_procedure(message, bot_answer)

    async def get_admin(self, us_id : int) -> bool:
        """Return true if the user identified by us_id is admin, false otherwise"""
        admin = await self.db.get_single_doc("users", self.db.query.user_id == us_id, "admin_status")
        if us_id == self.OWNER_ID and admin == None: return True
        if admin == None: return False
        return admin

    async def set_admin(self, message, us_id : int):
        """Turn the user identified by us_id into an admin or vice versa"""
        viewed_name = await self.get_viewed_name(us_id)
        user = message.from_user
        lang = await self.get_lang(user.id)

        if await self.get_admin(us_id) == True: bot_answer = f"{viewed_name} {self.get_localized_string("set_admin", lang, "remove")}"
        else: bot_answer = f"{viewed_name} {self.get_localized_string("set_admin", lang, "add")}"
        
        await self.db.upsert_values("users", {"admin_status" : not await self.get_admin(us_id)}, self.db.query.user_id == us_id)

        await self.reply_to(message, bot_answer)
        await self.logging_procedure(message, bot_answer)

    async def get_notification_status(self, us_id : int) -> bool:
        """Returns true if the user has on/off notifications active, false otherwise"""
        notifications = await self.db.get_single_doc("users", self.db.query.user_id == us_id, "notifications")
        if notifications == None: return True
        else: return notifications

    async def get_excl_sentence(self, us_id : int) -> str | None:
        """Returns the special sentence of the user us_id"""
        return await self.db.get_single_doc("users", self.db.query.user_id == us_id, "exclusive_sentence")

    async def set_excl_sentence(self, message, us_id : int): 
        """Set a special sentence the user identified by us_id receives when greeted by the bot"""
        user = message.from_user
        lang = await self.get_lang(user.id)
        sentence = message.text
        
        if not await self.validate_name(message, sentence, "sentence"): return
        
        target_viewed_name = await self.get_viewed_name(us_id)
        if sentence.lower() == "none": sentence = None
            
        if user.id == us_id: bot_answer = f"{self.get_localized_string("set_sentence", lang, "personal_sentence")} {sentence}"
        else: bot_answer = f"{self.get_localized_string("set_sentence", lang, "sentence_of")} {target_viewed_name} {self.get_localized_string("set_name", lang, "is_now")} {sentence}"
                
        await self.db.upsert_values("users", {"exclusive_sentence" : sentence}, self.db.query.user_id == us_id)

        await self.reply_to(message, bot_answer)
        await self.logging_procedure(message, bot_answer)

    async def get_info(self, message, us_id : int):
        """The bot sends a message with basic user informations"""
        user_doc = await self.db.get_single_doc("users", self.db.query.user_id == us_id)
        user = message.from_user
        lang = await self.get_lang(user.id)

        if user_doc:
            bot_answer = f"{self.get_localized_string("info", lang, "name")} {user_doc["first_name"]}\n{self.get_localized_string("info", lang, "last_name")} {user_doc["last_name"]}\nUsername: {user_doc["username"]}\n{self.get_localized_string("info", lang, "user_id")} {user_doc["user_id"]}\n{self.get_localized_string("info", lang, "bot_name")} {await self.get_botname(us_id)}\n{self.get_localized_string("info", lang, "sentence")} {await self.get_excl_sentence(us_id)}\n{self.get_localized_string("info", lang, "language")} {await self.get_lang(us_id)}\n{self.get_localized_string("info", lang, "gender")} {await self.get_gender(us_id)}\n{self.get_localized_string("info", lang, "notification")} {await self.get_notification_status(us_id)}\n{self.get_localized_string("info", lang, "admin")} {await self.get_admin(us_id)}"
        else: bot_answer = self.get_localized_string("choose_argument", lang, "not_found")

        await self.reply_to(message, bot_answer)
        await self.logging_procedure(message, bot_answer)

    async def get_event(self, us_id : int):
        """Return the current pending event to handle for that user"""
        return await self.db.get_single_doc("users", self.db.query.user_id == us_id, "event")

    async def set_event(self, message, next_step : callable , content = None, command : callable = None, second_arg : bool = None):
        """Creates an event packet to handle multimessage commands"""
        user = message.from_user

        next_step = next_step.__name__ if not isinstance(next_step, str) else next_step
        if command:
            if not isinstance(command, str): command_name = command.__name__
            else: command_name = command
        else: command_name = None
        
        await self.db.upsert_values("users", {"event" : {"next" : next_step, "content" : content, "command" : command_name, "second_arg" : second_arg}}, self.db.query.user_id == user.id)

    async def send_message_to(self, message, chat_id : int, scope : str = None, acknowledge : bool = True):
        """Send a message to the chat identified by chat_id"""
        user = message.from_user
        lang = await self.get_lang(user.id)
        bot_answer = self.get_localized_string("sent", lang)
        viewed_name = await self.get_viewed_name(user.id)

        from_text = f"{self.get_localized_string("send_to", await self.get_lang(chat_id), "from")} {viewed_name}({user.id}):"
        if scope == 'B': from_text = f"{self.get_localized_string("broadcast", await self.get_lang(chat_id), "from")} {viewed_name}:"
        if scope == 'A': from_text = f"{self.get_localized_string("broadcast", await self.get_lang(chat_id), "admin_from")} {viewed_name}:"

        if message.content_type in ("text", "photo", "audio", "voice", "sticker", "document"):
            try:
                await self.send_message(chat_id, from_text)
                if message.content_type == "text":
                    await self.send_message(chat_id, message.text)
                elif message.content_type == "photo":
                    file_id = message.photo[-1].file_id
                    caption = message.caption if message.caption else None
                    await self.send_photo(chat_id, file_id, caption)
                elif message.content_type == "audio":
                    file_id = message.audio.file_id
                    caption = message.caption if message.caption else None
                    await self.send_audio(chat_id, file_id, caption)
                elif message.content_type == "voice":
                    file_id = message.voice.file_id
                    caption = message.caption if message.caption else None
                    await self.send_voice(chat_id, file_id, caption) 
                elif message.content_type == "sticker":
                    file_id = message.sticker.file_id
                    await self.send_sticker(chat_id, file_id)
                elif message.content_type == "document":
                    file_id = message.document.file_id
                    caption = message.caption if message.caption else None
                    await self.send_document(chat_id, file_id, caption=caption)         
            except telebot.apihelper.ApiTelegramException: bot_answer = self.get_localized_string("send_to", lang, "blocked")
        else: bot_answer = self.get_localized_string("send_to", lang, "unsupported")
            
        if acknowledge: 
            await self.reply_to(message, bot_answer)
            await self.logging_procedure(message, bot_answer)

    async def broadcast(self, message, admin_only=False):
        """Send a message to all the users of the bot, or if admin only to just the admins"""
        acknowledge = True
        async for user in self.db.tables["users"]:
            try: 
                if user["chat_id"]:
                    if admin_only and user["admin_status"]:
                        await self.send_message_to(message, user["chat_id"], 'A', acknowledge)
                        acknowledge = False
                    if not admin_only:
                        await self.send_message_to(message, user["chat_id"], 'B', acknowledge)
                        acknowledge = False
            except (KeyError, telebot.apihelper.ApiTelegramException): pass

    async def ask_target(self, message, command : callable, second_arg : bool = True):
        """First step of the admin framework, it prompts the admin to specify the user who they're targeting with their command. The admin framework let the admins reuse the functions written for normal use in a specific admin mode"""
        user = message.from_user
        bot_answer = self.get_localized_string("choose_target", await self.get_lang(user.id))

        is_admin = await self.get_admin(user.id)
        if not is_admin:
            await self.permission_denied_procedure(message, "admin_only")
            return
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, selective=True)
        async for user_data in self.db.tables["users"]:
            if user_data["username"]: button = types.KeyboardButton(user_data["username"])
            else: button = types.KeyboardButton(user_data["first_name"])
            markup.add(button)

        await self.reply_to(message, bot_answer, reply_markup=markup)
        await self.set_event(message, self.validate_target, command=command, second_arg=second_arg)
        await self.logging_procedure(message, bot_answer)

    async def validate_target(self, message, command : callable, second_arg : bool = True):
        """Checks is the name is unique, it it isn't prompts the admin to specify the id"""
        admin_user = message.from_user
        lang = await self.get_lang(admin_user.id)

        us_id = await self.db.get_single_doc("users", self.db.query.username == message.text, "user_id")
        if not us_id:
            user_docs = await self.db.get_docs("users", self.db.query.first_name == message.text)
            if len(user_docs) == 1: us_id = user_docs[0]["user_id"] #One user found, everything is fine
            elif len(user_docs) > 1: #Multiple users found, specify which one is the correct one!
                bot_answer = f"{self.get_localized_string("choose_argument", lang, "multiple_found")}"

                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, selective=True)
                for user in user_docs:
                    us_id = user["user_id"]
                    button = types.KeyboardButton(us_id)
                    markup.add(button)
                    bot_answer += f"\n{us_id}:\nBotname: {await self.get_viewed_name(us_id)}\n"
                
                await self.reply_to(message, bot_answer, reply_markup=markup)
                await self.logging_procedure(message, bot_answer)
                await self.set_event(message, self.handle_multiple_users, command=command, second_arg=second_arg)
                return
            else: #No users found
                bot_answer = self.get_localized_string("choose_argument", lang, "not_found")
                await self.reply_to(message, bot_answer, reply_markup=types.ReplyKeyboardRemove())
                await self.logging_procedure(message, bot_answer)
                return 
            
        await self.ask_argument(message, command, us_id, second_arg)

    async def handle_multiple_users(self, message, command : callable, second_arg : bool = True):
        admin_user = message.from_user
        lang = await self.get_lang(admin_user.id)

        us_id = await self.db.get_single_doc("users", self.db.query.user_id == int(message.text), "user_id")
        if not us_id:
            bot_answer = self.get_localized_string("choose_argument", lang, "not_found")
            await self.reply_to(message, bot_answer, reply_markup=types.ReplyKeyboardRemove())
            return
        
        await self.ask_argument(message, command, us_id, second_arg)

    async def ask_argument(self, message, command : callable, us_id : int, second_arg : bool = True):
        """Second step of the admin framework, right after user selection. it prompts for the required text argument of certain commands"""
        admin_user = message.from_user
        lang = await self.get_lang(admin_user.id)
        markup = types.ReplyKeyboardRemove()

        bot_answer = f"{self.get_localized_string("choose_argument", lang, "selected")} {await self.get_viewed_name(us_id)} ({us_id}). \n{self.get_localized_string("choose_argument", lang, "argument")}"

        if not second_arg:
            bot_answer = f"{self.get_localized_string("choose_argument", lang, "selected")} {await self.get_viewed_name(us_id)} ({us_id})."
            await self.reply_to(message, bot_answer, reply_markup=types.ReplyKeyboardRemove())
            await self.set_event(message, command, us_id)
            await self.handle_events(message)
            return
        
        if command == self.set_permission.__name__:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, selective=True)
            commands = await self.db.get_single_doc("users", self.db.query.user_id == us_id, "commands")
            if commands:
                for command_name in commands:
                    button = types.KeyboardButton(command_name)
                    markup.add(button)

        await self.reply_to(message, bot_answer, reply_markup=markup)
        await self.set_event(message, command, content=us_id)
        await self.logging_procedure(message, bot_answer)

    async def get_banned_words(self, word_type) -> list[str]:
        """Return the list of a specified type of banned world"""
        banned_list = await self.db.get_single_doc("banned_words", self.db.query.type == word_type, "list")
        if banned_list == None: banned_list = []
        return banned_list

    async def add_banned_words(self, message, word_type : str):
        """Add a word to the banned words list"""
        word = (message.text).lower()
        user = message.from_user
        lang = await self.get_lang(user.id)
        banned_list = await self.get_banned_words(word_type)

        if word in banned_list:
            bot_answer = self.get_localized_string("banned_words", lang, "already_banned")
            await self.reply_to(message, bot_answer)
            await self.logging_procedure(message, bot_answer)
            return
        
        banned_list.append(word)
        list_data = {"list":banned_list, "type" : word_type}
        await self.db.upsert_values("banned_words", list_data, self.db.query.type == word_type)

        bot_answer = f"{word} {self.get_localized_string("banned_words", lang, "banned")}"
        await self.reply_to(message, bot_answer)
        await self.logging_procedure(message, bot_answer)

    async def remove_banned_words(self, message, word_type : str):
        """Remove a word from the banned words list"""
        word = (message.text).lower()
        user = message.from_user
        lang = await self.get_lang(user.id)
        banned_list = await self.get_banned_words(word_type)

        if word in banned_list:
            banned_list.remove(word)
            bot_answer = f"{word} {self.get_localized_string("banned_words", lang, "unbanned")}"
            list_data = {"list":banned_list, "type" : word_type}
            await self.db.upsert_values("banned_words", list_data, self.db.query.type == word_type)

            await self.reply_to(message, bot_answer)
            await self.logging_procedure(message, bot_answer)
            return
            
        bot_answer = self.get_localized_string("banned_words", lang, "already_unbanned")
        await self.reply_to(message, bot_answer)
        await self.logging_procedure(message, bot_answer)

    async def get_custom_commands_names(self) -> list[str]:
        """Returns a list of the dynamically created commands"""
        commands = []
        async for command in self.db.tables["custom_commands"]:
            commands.append(command["name"])
        return commands

    async def ask_custom_command_content(self, message):
        """Asks the content needed to create the commands"""
        user = message.from_user
        bot_answer = self.get_localized_string("custom_commands", await self.get_lang(user.id), "add_command_content")
        markup = types.ReplyKeyboardRemove()
        
        await self.reply_to(message, bot_answer, reply_markup=markup)
        await self.set_event(message, self.add_custom_command, content=message.text)
        await self.logging_procedure(message, bot_answer)

    async def add_custom_command(self, message, name : str):
        user = message.from_user
        if message.content_type == "photo": file_id = message.photo[-1].file_id
        elif message.content_type == "audio": file_id = message.audio.file_id
        elif message.content_type == "voice": file_id = message.voice.file_id
        elif message.content_type == "sticker": file_id = message.sticker.file_id
        elif message.content_type == "document": file_id = message.document.file_id
        elif message.content_type == "text": file_id = None
        else: 
            await self.reply_to(message, self.get_localized_string("send_to", await self.get_lang(user.id), "unsupported"))
            return

        command_data = {"content" : {"type" : message.content_type, "text" : message.text, "file_id" : file_id, "caption" : message.caption}, "name" : name.lower()}
        await self.db.upsert_values("custom_commands", command_data, self.db.query.name == name.lower())

        bot_answer = f"{name} {self.get_localized_string("custom_commands", await self.get_lang(user.id), "added")}"
        await self.reply_to(message, bot_answer)
        await self.logging_procedure(message, bot_answer)

    async def remove_custom_command(self, message):
        user = message.from_user
        markup = types.ReplyKeyboardRemove()

        if not(message.text in await self.get_custom_commands_names()):
            bot_answer = f"{self.get_localized_string("custom_commands", await self.get_lang(user.id), "not_found")}"
            await self.reply_to(message, bot_answer, reply_markup=markup)
            await self.logging_procedure(message, bot_answer)
            return

        await self.db.remove_values("custom_commands", self.db.query.name == message.text.lower())

        bot_answer = f"{message.text} {self.get_localized_string("custom_commands", await self.get_lang(user.id), "removed")}"
        await self.reply_to(message, bot_answer, reply_markup=markup)
        await self.logging_procedure(message, bot_answer)

    def generate_wikipedia_event(self, lang):
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
            bot_answer = self.get_localized_string("wikipedia", lang, "page404")
        return bot_answer

    #commands
    async def send_greets(self, message):
        """Greet the user with its name and a special sentence"""
        user = message.from_user
        lang = await self.get_lang(user.id)
        await self.store_user_data(user, message.chat.id) #Create or update the user's table when starting
        viewed_name = await self.get_viewed_name(user.id)

        if await self.get_excl_sentence(user.id): special_reply = f"\n{await self.get_excl_sentence(user.id)}"
        else: special_reply = ""
        
        bot_answer = f"{self.get_localized_string("greet", lang)} {viewed_name}!{special_reply}"

        await self.reply_to(message, bot_answer)
        await self.logging_procedure(message, bot_answer)
    
    async def set_user_lang(self, message, us_id=None):
        user = message.from_user
        if not us_id: us_id = user.id
        bot_answer = self.get_localized_string("set_lang",await self.get_lang(user.id), "choice")
        markup = types.InlineKeyboardMarkup()
        for lang, label in self.languages.items():
            button = types.InlineKeyboardButton(label, callback_data="lang_"+str(us_id)+"_"+lang)
            markup.add(button)

        has_permission = await self.get_permission(user.id, "lang")
        if has_permission != True:
            await self.permission_denied_procedure(message, has_permission)
            return
        
        await self.reply_to(message, bot_answer, reply_markup=markup)
        await self.logging_procedure(message, bot_answer)
    
    async def set_name(self, message):
        """Start the event chain to set the user's botname"""
        user = message.from_user
        bot_answer = self.get_localized_string("set_name", await self.get_lang(user.id), "prompt")

        has_permission = await self.get_permission(user.id, "setname")
        if has_permission != True:
            await self.permission_denied_procedure(message, has_permission)
            return
        
        await self.reply_to(message, bot_answer)
        await self.set_event(message, self.set_botname, content=user.id)
        await self.logging_procedure(message, bot_answer)
    
    async def reset_name(self, message):
        """Call function to reset the user's botname."""
        user = message.from_user
        has_permission = await self.get_permission(user.id, "resetname")
        if has_permission != True:
            await self.permission_denied_procedure(message, has_permission)
            return
        
        await self.reset_botname(message, user.id)
    
    async def send_to_owner(self, message):
        """Send a message to the owner of the bot"""
        user = message.from_user
        owner_name = await self.get_viewed_name(self.OWNER_ID)
        bot_answer = f"{self.get_localized_string("send_to", await self.get_lang(user.id), "user")} {owner_name}?"

        has_permission = await self.get_permission(user.id, "sendtoowner")
        if has_permission != True:
            await self.permission_denied_procedure(message, has_permission)
            return
        
        await self.reply_to(message, bot_answer)
        await self.set_event(message, self.send_message_to, content=self.OWNER_ID)
        await self.logging_procedure(message, bot_answer)
    
    async def send_to_admin(self, message):
        """Send a message to all the admins of the bot"""
        user = message.from_user
        bot_answer = self.get_localized_string("send_to", await self.get_lang(user.id), "admins")

        has_permission = await self.get_permission(user.id, "sendtoadmin")
        if has_permission != True:
            await self.permission_denied_procedure(message, has_permission)
            return
        
        await self.reply_to(message, bot_answer)
        await self.set_event(message, self.broadcast, content=True)
        await self.logging_procedure(message, bot_answer)
    
    async def events_on_wikipedia(self, message):
        """send a random event of the day from italian wikipedia"""
        user = message.from_user
        lang = await self.get_lang(user.id)
        loop = asyncio.get_running_loop()
        bot_answer = await loop.run_in_executor(None, self.generate_wikipedia_event, lang)
        await self.reply_to(message, bot_answer)
        await self.logging_procedure(message, bot_answer)
    
    async def set_user_gender(self, message):
        """Call function to set the user's gender"""
        user = message.from_user

        has_permission = await self.get_permission(user.id, "gender")
        if has_permission != True:
            await self.permission_denied_procedure(message, has_permission)
            return
        
        await self.set_gender(message, user.id)
    
    async def random_number(self, message):
        """Return the user a random number"""
        bot_answer = random.randrange(0, 999)
        await self.reply_to(message, bot_answer)
        await self.logging_procedure(message, bot_answer)
    
    async def random_name(self, message):
        """Set the user a random name, also doable by using -r as argument for setname"""
        user = message.from_user
        has_permission = await self.get_permission(user.id, "randomname")
        if has_permission != True:
            await self.permission_denied_procedure(message, has_permission)
            return
        
        await self.set_botname(message, user.id, True)
    
    async def request_qrcode(self, message):
        user = message.from_user
        chat_id = await self.get_chat_id(user.id)
        has_permission = await self.get_permission(user.id, "qrcode")
        if has_permission != True:
            await self.permission_denied_procedure(message, has_permission)
            return
        
        bot_answer = self.get_localized_string("qrcode", await self.get_lang(user.id), "msg_to_send")
        await self.reply_to(message, bot_answer)
        await self.set_event(message, self.generate_qrcode, content=chat_id)
        await self.logging_procedure(message, bot_answer)
    
    async def set_notifications(self, message):
        user = message.from_user
        lang = await self.get_lang(user.id)
        
        if not await self.db.contains("users", self.db.query.user_id == user.id):
            await self.permission_denied_procedure(message, "not_found")
            return

        if await self.get_notification_status(user.id): bot_answer = self.get_localized_string("notifications", lang, "off")
        else: bot_answer = self.get_localized_string("notifications", lang, "on")

        await self.db.upsert_values("users", {"notifications" : not await self.get_notification_status(user.id)}, self.db.query.user_id == user.id)
        await self.reply_to(message, bot_answer)

        await self.logging_procedure(message, bot_answer)
    
    async def info(self, message):
        user = message.from_user
        await self.get_info(message, user.id)
    
    async def permissions_list(self, message):
        """Return the user a list with all the commands they can and can't use"""
        user = message.from_user
        await self.get_permissions_list(message, user.id)
    
    async def cancel_command(self, message, reply : bool = True):
        user = message.from_user
        markup = types.ReplyKeyboardRemove()
        await self.db.upsert_values("users", {"event" : None}, self.db.query.user_id == user.id)

        if reply:
            bot_answer = self.get_localized_string("cancel", await self.get_lang(user.id))
            await self.reply_to(message, bot_answer, reply_markup=markup)
            await self.logging_procedure(message, bot_answer)
    
    async def about(self, message):
        """Return a sponsor to myself, really"""
        user = message.from_user
        markup = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton("Github", url="github.com/Giu27/SupergiuToolsBot")
        markup.row(button)
        bot_answer = self.get_localized_string("about", await self.get_lang(user.id))
        await self.reply_to(message, bot_answer, reply_markup=markup)
        await self.logging_procedure(message, bot_answer)

    #Admin version of the commands above + extra    
    async def get_person_info(self, message):
        await self.ask_target(message, self.get_info, False)
    
    async def set_person_name(self, message):
        user = message.from_user
        has_permission = await self.get_permission(user.id, "setpersonname")
        if not has_permission:
            await self.permission_denied_procedure(message, "admin_only")
            return
        
        await self.ask_target(message, self.set_botname)
    
    async def reset_person_name(self, message):
        user = message.from_user
        has_permission = await self.get_permission(user.id, "resetpersonname")
        if not has_permission:
            await self.permission_denied_procedure(message, "admin_only")
            return
        
        await self.ask_target(message, self.reset_botname, False)
    
    async def set_person_permission(self, message):
        user = message.from_user
        has_permission = await self.get_permission(user.id, "setpersonpermission")
        if not has_permission:
            await self.permission_denied_procedure(message, "admin_only")
            return
        
        await self.ask_target(message, self.set_permission)
    
    async def get_person_permissions(self, message):
        user = message.from_user
        has_permission = await self.get_permission(user.id, "getpersonpermission")
        if not has_permission:
            await self.permission_denied_procedure(message, "admin_only")
            return
        await self.ask_target(message, self.get_permissions_list, False)
    
    async def set_person_admin(self, message):
        """Adds an admin to the bot"""
        user = message.from_user
        if user.id != self.OWNER_ID:
            await self.permission_denied_procedure(message, "owner_only")
            return
        await self.ask_target(message, self.set_admin, False)
    
    async def set_person_sentence(self, message):
        """Gives a personal sentence easter egg to a user"""
        user = message.from_user
        has_permission = await self.get_permission(user.id, "setpersonsentence")
        if not has_permission:
            await self.permission_denied_procedure(message, "admin_only")
            return
        
        await self.ask_target(message, self.set_excl_sentence)
    
    async def set_person_lang(self, message):
        user = message.from_user
        has_permission = await self.get_permission(user.id, "setpersonlang")
        if not has_permission:
            await self.permission_denied_procedure(message, "admin_only")
            return
        
        await self.ask_target(message, self.set_user_lang, False)
    
    async def set_person_gender(self, message):
        user = message.from_user
        has_permission = await self.get_permission(user.id, "setpersongender")
        if not has_permission:
            await self.permission_denied_procedure(message, "admin_only")
            return
        
        await self.ask_target(message, self.set_gender, False)
    
    async def get_ids(self, message):
        """Returns a list with all the bot users"""
        user = message.from_user
        bot_answer = ""

        is_admin = await self.get_admin(user.id)
        if not is_admin:
            await self.permission_denied_procedure(message, "admin_only")
            return
        
        async for user in self.db.tables["users"]:
            try: 
                if user["user_id"]: bot_answer += f"\n\n{user["user_id"]}: {user["first_name"]} {user["last_name"]}\nBotname: {await self.get_botname(user["user_id"])}"
            except KeyError: pass

        await self.reply_to(message, bot_answer)
        await self.logging_procedure(message, bot_answer.lstrip())
    
    async def send_to_target(self, message):
        user = message.from_user
        has_permission = await self.get_permission(user.id, "sendto")
        if not has_permission:
            await self.permission_denied_procedure(message, "admin_only")
            return
        
        await self.ask_target(message, self.send_message_to)
    
    async def send_in_broadcast(self, message):
        """Event chain to send a message in broadcast"""
        user = message.from_user
        bot_answer = self.get_localized_string("broadcast", await self.get_lang(user.id), "msg_to_send")

        is_admin = await self.get_admin(user.id)
        has_permission = await self.get_permission(user.id, "broadcast")
        if not is_admin or not has_permission:
            await self.permission_denied_procedure(message, "admin_only")
            return
        
        await self.reply_to(message, bot_answer)
        await self.set_event(message, self.broadcast)
        await self.logging_procedure(message, bot_answer)

    #banned words events    
    async def add_banned(self, message):
        user = message.from_user
        bot_answer = self.get_localized_string("banned_words", await self.get_lang(user.id), "add_banned")

        is_admin = await self.get_admin(user.id)
        has_permission = await self.get_permission(user.id, "addbanned")
        if not is_admin or not has_permission:
            await self.permission_denied_procedure(message, "admin_only")
            return
        
        await self.reply_to(message, bot_answer)
        await self.set_event(message, self.add_banned_words, content="banned")
        await self.logging_procedure(message, bot_answer)
    
    async def remove_banned(self, message):
        user = message.from_user
        bot_answer = self.get_localized_string("banned_words", await self.get_lang(user.id), "remove_banned")

        is_admin = await self.get_admin(user.id)
        has_permission = await self.get_permission(user.id, "removebanned")
        if not is_admin or not has_permission:
            await self.permission_denied_procedure(message, "admin_only")
            return
        
        await self.reply_to(message, bot_answer)
        await self.set_event(message, self.remove_banned_words, content="banned")
        await self.logging_procedure(message, bot_answer)
    
    async def add_ultra_banned(self, message):
        user = message.from_user
        bot_answer = self.get_localized_string("banned_words", await self.get_lang(user.id), "add_ultrabanned")

        is_admin = await self.get_admin(user.id)
        has_permission = await self.get_permission(user.id, "addbanned")
        if not is_admin or not has_permission:
            await self.permission_denied_procedure(message, "admin_only")
            return
        
        await self.reply_to(message, bot_answer)
        await self.set_event(message, self.add_banned_words, content="ultrabanned")
        await self.logging_procedure(message, bot_answer)
    
    async def remove_ultra_banned(self, message):
        user = message.from_user
        bot_answer = self.get_localized_string("banned_words", await self.get_lang(user.id), "remove_banned")

        is_admin = await self.get_admin(user.id)
        has_permission = await self.get_permission(user.id, "removebanned")
        if not is_admin or not has_permission:
            await self.permission_denied_procedure(message, "admin_only")
            return
        
        await self.reply_to(message, bot_answer)
        await self.set_event(message, self.remove_banned_words, content="ultrabanned")
        await self.logging_procedure(message, bot_answer)

    #custom commands events
    async def get_command_list(self, message):
        """Get a list of currently existing custom commands"""
        user = message.from_user
        is_admin = await self.get_admin(user.id)

        if not is_admin:
            await self.permission_denied_procedure(message, "admin_only")
            return

        bot_answer = self.get_localized_string("custom_commands", await self.get_lang(user.id), "list")
        for command in await self.get_custom_commands_names():
            bot_answer += (f"\n{command}")

        await self.reply_to(message, bot_answer)
        await self.logging_procedure(message, bot_answer)
    
    async def add_command(self, message):
        """Adds an admin custom command"""
        user = message.from_user
        bot_answer = self.get_localized_string("custom_commands", await self.get_lang(user.id), "add_command")

        is_admin = await self.get_admin(user.id)
        has_permission = await self.get_permission(user.id, "addcommand")
        if not is_admin or not has_permission:
            await self.permission_denied_procedure(message, "admin_only")
            return
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, selective=True)
        for command in await self.get_custom_commands_names():
            button = types.KeyboardButton(command)
            markup.add(button)
        
        await self.reply_to(message, bot_answer, reply_markup=markup)
        await self.set_event(message, self.ask_custom_command_content)
        await self.logging_procedure(message, bot_answer)
    
    async def remove_command(self, message):
        """Removes a admin defined command"""
        user = message.from_user
        bot_answer = self.get_localized_string("custom_commands", await self.get_lang(user.id), "remove_command")

        is_admin = await self.get_admin(user.id)
        has_permission = await self.get_permission(user.id, "addcommand")
        if not is_admin or not has_permission:
            await self.permission_denied_procedure(message, "admin_only")
            return
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, selective=True)
        for command in await self.get_custom_commands_names():
            button = types.KeyboardButton(command)
            markup.add(button)
        
        await self.reply_to(message, bot_answer, reply_markup=markup)
        await self.set_event(message, self.remove_custom_command)
        await self.logging_procedure(message, bot_answer)
    
    async def handle_custom_commands(self, message):
        """Handle dynamically generated commands"""
        user = message.from_user
        command = message.text[1:]
        if command in await self.get_custom_commands_names():
            has_permission = await self.get_permission(user.id, command)
            if not has_permission:
                await self.permission_denied_procedure(message, has_permission)
                return
            
            message_data = await self.db.get_single_doc("custom_commands", self.db.query.name == command, "content")
            if message_data["type"] == "text": await self.send_message(message.chat.id, message_data["text"])
            elif message_data["type"] == "photo": await self.send_photo(message.chat.id, message_data["file_id"], message_data["caption"])
            elif message_data["type"] == "audio": await self.send_audio(message.chat.id, message_data["file_id"], message_data["caption"])
            elif message_data["type"] == "voice": await self.send_voice(message.chat.id, message_data["file_id"], message_data["caption"])
            elif message_data["type"] == "sticker": await self.send_sticker(message.chat.id, message_data["file_id"])
            elif message_data["type"] == "document": await self.send_document(message.chat.id, message_data["file_id"], caption=message_data["caption"])
            else: await self.reply_to(message, self.get_localized_string("send_to", self.get_lang(user.id), "unsupported"))

            if message_data["type"] == "text": content = message_data["text"]
            else: content = message_data["type"]
            await self.logging_procedure(message, content)
        else: await self.log_and_update(message)

    #General handlers
    async def handle_events(self, message):
        user = message.from_user
        await self.store_user_data(user, message.chat.id)

        event = await self.get_event(user.id)

        if event:
            await self.cancel_command(message, False)
            if event["command"]:
                await self.functions[event["next"]](message, event["command"], event["second_arg"])
            elif event["content"]:
                await self.functions[event["next"]](message, event["content"]) 
            else: await self.functions[event["next"]](message)
        
        else: 
            if message.text == None: await self.handle_media(message)
            else: await self.log_and_update(message)

    async def handle_media(self,message):
        user = message.from_user
        lang = await self.get_lang(user.id)

        bot_answer = f"{self.get_localized_string("greet", lang)} {await self.get_viewed_name(user.id)}, {self.get_localized_string("handle_media", lang, "image")}"
        if (message.voice or message.audio): bot_answer = f"{self.get_localized_string("greet", lang)} {await self.get_viewed_name(user.id)}, {self.get_localized_string("handle_media", lang, "audio")}"

        await self.reply_to(message, bot_answer)
        await self.logging_procedure(message, bot_answer)

    async def log_and_update(self, message):
        """Logs messages and updates the database"""
        user = message.from_user
        await self.store_user_data(user, message.chat.id)

        if self.LOG:
            if user.username: user_info = user.username
            else: user_info = f"{user.first_name} {user.last_name}"

            if message.content_type == "text": content = message.text
            else: content = message.content_type

            self.logger.info(f"{user.id}, {user_info}: {content}")
            async with aiofiles.open(f"{self.log_path}/{user.id}.txt", "a") as log_file:
                await log_file.write(f"{user.id}, {user_info}: {content}\n")

    async def main(self):
        await self.set_my_commands(self.commands["en"]) #default
        for code, commands_list in self.commands.items():
            await self.set_my_commands(commands_list, language_code=code)

        await self.send_on_off_notification("online")

        await self.polling()

        await self.send_on_off_notification("offline")

        await self.db.close()
        await self.close_session()

if __name__ == "__main__":
    load_dotenv()

    DEV_MODE = True #switches on/off the online/offline notification if testing on a database with multiple users is needed
    LOG = True #switches on/off the logging of messages received by the bot

    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    OWNER_ID = int(os.environ.get("OWNER_ID"))

    bot = Bot(BOT_TOKEN, OWNER_ID, "BOT_DB.JSON", log=LOG, dev_mode=DEV_MODE)
    asyncio.run(bot.main())