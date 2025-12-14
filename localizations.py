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
    types.BotCommand("gender","Permette all'utente di cambiare il genere utilizzato da randomname"),
    types.BotCommand("randomnumber","Restituisce un numero casuale tra 0 e 999"),
    types.BotCommand("randomname","Imposta un nome casuale"),
    types.BotCommand("qrcode", "Crea un QR Code di un contenuto testuale inviato"),
    types.BotCommand("notifications","Attiva/Disattiva le notifiche"),
    types.BotCommand("info","Restituisce le informazioni memorizzate dal bot"),
    types.BotCommand("permissionlist","Restituisce lo stato attuale dei permessi per i vari comandi"),
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
    types.BotCommand("gender","Let user change the gender used by randomname"),
    types.BotCommand("randomnumber","Return a random number in the 0 to 999 range"),
    types.BotCommand("randomname","Set a random name"),
    types.BotCommand("qrcode", "Let the user creates a QR Code from text"),
    types.BotCommand("notifications","Turn on/off the notifications"),
    types.BotCommand("info","Return the infos the bot has about you"),
    types.BotCommand("permissionlist","Return current permissions status for the various commands"),
    types.BotCommand("about","Return infos about the bot")
]

localizations = {
    "not_found" : {
        "en" : "Reply not found for the selected language.",
        "it" : "Risposta non trovata per la lingua selezionata."
    },
    "permission_denied" : {
        "en" : {
            "default" : "You don't have the right to use this command!",
            "target_admin" : "You can't target an admin.",
            "owner_only" : "You must be owner.",
            "admin_only" : "You must be admin with the right permissions.",
            "False" : "Your use of the command is subject to restrictions.",
            "not_found" : "You weren't in the database, try again."
        },
        "it" : {
            "default" : "Non hai il permesso di usare questo comando!",
            "target_admin" : "Non puoi bloccare un admin.",
            "owner_only" : "Devi essere owner.",
            "admin_only" : "Devi essere admin con i giusti permessi.",
            "False" : "Il tuo uso del comando è soggetto a restrizioni.",
            "not_found" : "Non eri nel database, prova di nuovo."
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
        "en" : "Write the user's name:",
        "it" : "Inserisci il nome dell'utente:"
    },
    "choose_argument" : {
        "en" : {
            "not_found" : "User not found.",
            "selected" : "User selected:",
            "argument" : "Write the argument:",
            "multiple_found" : "Multiple users found! Select the user's id."
        },
        "it" : {
            "not_found" : "Utente non trovato.",
            "selected" : "Utente selezionato:",
            "argument" : "Inserisci l'argomento:",
            "multiple_found" : "Sono stati trovati più utenti! Seleziona l'id dell'utente."
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
            "already_banned" : "The word is already banned.",
            "already_unbanned" : "The word wasn't already banned.",
            "add_banned" : "Which word do you want to ban?",
            "remove_banned" : "Which word do you want to unban from this category?",
            "add_ultrabanned" : "Which word do you want to hyperban?",
            "unbanned" : "unbanned"
        },
        "it" : {
            "banned" : "bannata.",
            "already_banned" : "Parola già bannata.",
            "already_unbanned" : "la parola non era bannata.",
            "add_banned" : "Che parola vuoi vietare?",
            "remove_banned" : "Che parola vuoi sbannare da questa categoria?",
            "add_ultrabanned" : "Che parola vuoi iper vietare?",
            "unbanned" : "sbannata"
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
            "blocked" : "Error, the user blocked the bot.",
            "unsupported" : "Error, the file type isn't supported"
        },
        "it" : {
            "admins" : "Che messaggio vuoi inviare agli admin?",
            "user" : "Che messaggio vuoi inviare a",
            "from" : "Da",
            "blocked" : "Errore, l'utente ha bloccato il bot",
            "unsupported" : "Errore, il tipo di file non è supportato."
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
            "permission_of" : "Use of command by",
            "locked" : "disabled!",
            "unlocked" : "enabled!",
            "list" : "Commands permission list for"
        },
        "it" : {
            "permission_of" : "Uso del comando di",
            "locked" : "bloccato!",
            "unlocked" : "sbloccato!",
            "list" : "Lista dei permessi per i comandi di"
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
    "set_gender" : {
        "en" : {
            "m" : "will now be considered male.",
            "f" : "will now be considered female.",
        },
        "it" : {
            "m" : "sarà ora considerato maschio.",
            "f" : "sarà ora considerata femmina.",
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
            "admin" : "Admin account:",
            "gender" : "Gender:"
        },
        "it" : {
            "name" : "Nome:",
            "last_name" : "Cognome:",
            "user_id" : "ID Utente:",
            "bot_name" : "Nome nel bot:",
            "sentence" : "Frase personale:",
            "language" : "Lingua:",
            "notification" : "Notifiche attive:",
            "admin" : "Account admin:",
            "gender" : "Genere:"
        },
    },
    "custom_commands" : {
        "en" : {
            "add_command" : "What's the name of the command to creat / update?",
            "add_command_content" : "Send the message to save!",
            "added" : "added / updated!",
            "removed" : "deleted!",
            "remove_command" : "Which command do you want to delete?",
            "not_found" : "Command not found!",
            "list" : "List of custom commands:"
        },
        "it" : {
            "add_command" : "Qual è il nome del comando da creare / aggiornare?",
            "add_command_content" : "Invia il messaggio da salvare!",
            "added" : "aggiunto / aggiornato!",
            "removed" : "rimosso!",
            "remove_command" : "Quale comando vuoi rimuovere?",
            "not_found" : "Comando non trovato!",
            "list" : "Lista dei comandi personalizzati:"
        }
    }
}