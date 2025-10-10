#File containing the various bot localization strings
from telebot import types

commands_it = [
    types.BotCommand("hello","Saluta l'utente"),
    types.BotCommand("lang","Cambia la lingua del bot"),
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
commands_en = [
    types.BotCommand("hello","Greets the user"),
    types.BotCommand("lang","Changes the bot language"),
    types.BotCommand("setname","Set your name"),
    types.BotCommand("resetname","Reset to your original name"),
    types.BotCommand("sendtoowner","Send a message to the bot's owner"),
    types.BotCommand("sendtoadmin","Send a message to the bot's admins"),
    types.BotCommand("eventstoday","Return a fun fact about this day in history"),
    types.BotCommand("randomnumber","Return a random number in the 0 to 999 range"),
    types.BotCommand("randomname","Set a random name"),
    types.BotCommand("qrcode", "Let the user creates a QR Code from text"),
    types.BotCommand("notifications","Turn on/off the notifications"),
    types.BotCommand("info","Return the infos the bot has about you"),
    types.BotCommand("about","Return infos about the bot")
]

localizations = {
    "not_found" : {
        "en" : "Reply not found.",
        "it" : "Risposta non trovata."
    },
    "permission_denied" : {
        "en" : {
            "default" : "You don't have the right to use this command!",
            "target_admin" : "You can't target an admin.",
            "owner_only" : "You must be owner.",
            "admin_only" : "You must be admin.",
            "Blocked" : "Your account is subject to restrictions."
        },
        "it" : {
            "default" : "Non hai il permesso di usare questo comando!",
            "target_admin" : "Non puoi bloccare un admin.",
            "owner_only" : "Devi essere owner.",
            "admin_only" : "Devi essere admin.",
            "Blocked" : "Il tuo account è soggetto a restrizioni."
        },
    },
    "notifications" : {
        "en" : {
            "bot" : "The bot is",
            "on" : "Notifications turned on.",
            "off" : "Notifications turned off."
        },
        "it" : {
            "bot" : "Il bot è",
            "on" : "Notifiche attivate.",
            "off" : "Notifiche disattivate."
        }
    },
    "greet" : {
        "en" : "Hi",
        "it" : "Ciao"
    },
    "wikipedia" : {
        "en" : {
            "page404" : "Page not found!"
        },
        "it" : {
            "page404" : "Pagina non trovata!"
        }
    },
    "about" : {
        "en" : "Bot developed by @Supergiuchannel, the code is available on Github.",
        "it" : "Bot sviluppato da @Supergiuchannel, il codice è disponibile su Github."
    },
    "choose_target" : {
        "en" : "Write the user's id:",
        "it" : "Inserisci l'id dell'utente:"
    },
    "choose_text" : {
        "en" : {
            "not_found" : "User not found.",
            "selected" : "User selected:",
            "argument" : "Write the argument:"
        },
        "it" : {
            "not_found" : "Utente non trovato.",
            "selected" : "Utente selezionato:",
            "argument" : "Inserisci l'argomento:"
        }
    },
    "set_lang" : {
        "en" : "will now receive messages in english",
        "it" : "riceverà i messaggi in italiano."
    },
    "handle_media" : {
        "en" : {
            "audio" : "I lost my earbuds and I can't listen to what you sent",
            "image" : "I lost my glasses and I can't see what you sent"
        },
        "it" : {
            "audio" : "ho perso le cuffie e non posso ascoltare ciò che hai inviato.",
            "image" : "ho perso gli occhiali e non posso visualizzare ciò che hai inviato"
        },
    },
    "banned_words" : {
        "en" : {
            "banned" : "banned.",
            "already_banned" : "The word was already banned.",
            "add_banned" : "Which word do you want to ban?",
            "add_ultrabanned" : "Which word do you want to hyperban?"
        },
        "it" : {
            "banned" : "bannata.",
            "already_banned" : "Parola già bannata.",
            "add_banned" : "Che parola vuoi vietare?",
            "add_ultrabanned" : "Che parola vuoi iper vietare?"
        },
    },
    "sent" : {
        "en" : "Sent!",
        "it" : "inviato!"
    },
    "qrcode" : {
        "en" : {
            "error" : "Error, please send this message to",
            "msg_to_send" : "Send some text and I'll generate a QR code"
        },
        "it" : {
            "error" : "errore, per favore invia questo messaggio a",
            "msg_to_send" : "Inviami del testo e genererò un QR code"
        }
    },
    "broadcast" : {
        "en" : {
            "msg_to_send" : "What do you want to send in broadcast?",
            "from" : "Announcement by",
            "admin_from" : "Message to admin from"
        },
        "it" : {
            "msg_to_send" : "Che messaggio vuoi inviare in broadcast?",
            "from" : "Annuncio di",
            "admin_from" : "Messaggio per gli admin di"
        }
    },
    "send_to" : {
        "en" : {
            "admins" : "What do you want to send to bot admins?",
            "user" : "What do you want to send to",
            "from" : "From",
            "blocked" : "Error, the user blocked the bot."
        },
        "it" : {
            "admins" : "Che messaggio vuoi inviare agli admin?",
            "user" : "Che messaggio vuoi inviare a",
            "from" : "Da",
            "blocked" : "Errore, l'utente ha bloccato il bot"
        },
    },
    "set_name" : {
        "en" : {
            "prompt" : "Which name do you want to use?",
            "max_chars" : "Redo the command using less characters.",
            "name_banned" : "Redo the command using a not banned name.",
            "personal_name" : "Your name is now",
            "name_of" : "The name of",
            "is_now" : "is now",
            "resetted" : "has been resetted!"
        },
        "it" : {
            "prompt" : "Che nome vuoi usare?",
            "max_chars" : "Riesegui il comando usando meno caratteri.",
            "name_banned" : "Riesegui il comando usando un nome consentito.",
            "personal_name" : "Il tuo nome è ora",
            "name_of" : "Il nome di",
            "is_now" : "è ora",
            "resetted" : "è stato resettato!"
        },
    },
    "permission" : {
        "en" : {
            "permission_of" : "Rights of",
            "locked" : "locked!",
            "unlocked" : "disabled!"
        },
        "it" : {
            "permission_of" : "Permessi di",
            "locked" : "bloccati!",
            "unlocked" : "enabled!"
        }
    },
    "set_admin" : {
        "en" : {
            "add" : "is now admin!",
            "remove" : "is no longer an admin!"
        },
        "it" : {
            "add" : "è ora admin!",
            "remove" : "non è più admin!"
        },
    },
    "set_sentence" : {
        "en" : {
            "sentence_banned" : "Redo the command and don't use banned words in the sentence.",
            "personal_sentence" : "Your sentence is now",
            "sentence_of" : "The personal sentence of",
        },
        "it" : {
            "sentence_banned" : "Riesegui il comando usando solo termini consentiti.",
            "personal_sentence" : "La tua frase è ora",
            "sentence_of" : "La frase di",
        },
    },
    "info" : {
        "en" : {
            "name" : "First name:",
            "last_name" : "Last name:",
            "user_id" : "User ID:",
            "bot_name" : "Name in the bot:",
            "sentence" : "Personal sentence:",
            "language" : "Language:",
            "notification" : "Notifications on:",
            "blocked" : "Restricted account:",
            "admin" : "Admin account:"
        },
        "it" : {
            "name" : "Nome:",
            "last_name" : "Cognome:",
            "user_id" : "ID Utente:",
            "bot_name" : "Nome nel bot:",
            "sentence" : "Frase personale:",
            "language" : "Lingua:",
            "notification" : "Notifiche attive:",
            "blocked" : "Account bloccato:",
            "admin" : "Account admin:"
        },
    }
}