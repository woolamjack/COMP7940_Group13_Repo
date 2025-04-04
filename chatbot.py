from telegram import Update
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, CallbackContext)
import configparser
import logging
import redis
from ChatGPT_HKBU import HKBU_ChatGPT

global redis1
def main():
# Load your token and create an Updater for your Bot
    config = configparser.ConfigParser()
    config.read('config.ini')
    updater = Updater(token=(config['TELEGRAM']['ACCESS_TOKEN']), use_context=True)
    dispatcher = updater.dispatcher
    global redis1
    redis1 = redis.Redis(host=(config['REDIS']['HOST']),
    password=(config['REDIS']['PASSWORD']),
    port=(config['REDIS']['REDISPORT']),
    decode_responses=(config['REDIS']['DECODE_RESPONSE']),
    username=(config['REDIS']['USER_NAME']))

    # You can set this logging module, so you will know when
    # and why things do not work as expected Meanwhile, update your config.ini as:
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
    # register a dispatcher to handle message: here we register an echo dispatcher
    ## echo_handler = MessageHandler(Filters.text & (~Filters.command), echo)
    ## dispatcher.add_handler(echo_handler)

    # dispatcher for chatgpt
    global chatgpt
    chatgpt = HKBU_ChatGPT(config)
    chatgpt_handler = MessageHandler(Filters.text & (~Filters.command), equiped_chatgpt)
    dispatcher.add_handler(chatgpt_handler)

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("add", add))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("good", good))
    dispatcher.add_handler(CommandHandler("bad", bad))
    dispatcher.add_handler(CommandHandler("hello", hello))

    # To start the bot:
    updater.start_polling()
    updater.idle()

def echo(update, context):
    reply_message = update.message.text.upper()
    logging.info("Update: " + str(update))
    logging.info("context: " + str(context))
    context.bot.send_message(chat_id=update.effective_chat.id, text= reply_message)

def equiped_chatgpt(update, context):
    global chatgpt
    reply_message = chatgpt.submit(update.message.text)
    logging.info("Update: " + str(update))
    logging.info("context: " + str(context))
    context.bot.send_message(chat_id=update.effective_chat.id, text=reply_message)

# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text('Helping you helping you.')

def add(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /add is issued."""
    try:
        global redis1
        keyword = context.args[0]
        redis1.incr(keyword)
        count = redis1.get(keyword)  # This is already a string
        update.message.reply_text(f'You have said "{keyword}" for {count} times.')
    except IndexError:
        update.message.reply_text('Usage: /add <keyword>')
    except redis.RedisError as e:
        logging.error(f"Redis error: {e}")
        update.message.reply_text('An error occurred while accessing Redis.')

def good(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /good is issued."""
    try:
        global redis1
        keyword = context.args[0]
        redis1.incr(keyword)
        count = redis1.get(keyword)  # This is already a string
        update.message.reply_text(f'Good "{keyword}" x {count} times.')
    except IndexError:
        update.message.reply_text('Usage: /good <keyword>')
    except redis.RedisError as e:
        logging.error(f"Redis error: {e}")
        update.message.reply_text('An error occurred while accessing Redis.')

def bad(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /good is issued."""
    try:
        global redis1
        keyword = context.args[0]
        redis1.incr(keyword)
        count = redis1.get(keyword)  # This is already a string
        update.message.reply_text(f'Bad "{keyword}" x {count} times.')
    except IndexError:
        update.message.reply_text('Usage: /bad <keyword>')
    except redis.RedisError as e:
        logging.error(f"Redis error: {e}")
        update.message.reply_text('An error occurred while accessing Redis.')

def hello(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /hello is issued."""
    try:
        global redis1
        keyword = context.args[0]
        redis1.incr(keyword)
        count = redis1.get(keyword)  # This is already a string
        update.message.reply_text(f'Good Day, {keyword}!')
    except IndexError:
        update.message.reply_text('Usage: /hello <keyword>')
    except redis.RedisError as e:
        logging.error(f"Redis error: {e}")
        update.message.reply_text('An error occurred while accessing Redis.')
    #     logging.info(context.args[0])
    #     msg = context.args[0] # /add keyword <-- this should store the keyword
    #     redis1.incr(msg)
    #     update.message.reply_text('You have said ' + msg + ' for ' +
    #     redis1.get(msg).decode('UTF-8') + ' times.')
    # except (IndexError, ValueError):
    #     update.message.reply_text('Usage: /add <keyword>')


                            
if __name__ == '__main__':
    main()