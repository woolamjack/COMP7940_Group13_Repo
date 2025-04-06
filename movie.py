from telegram import Update, ParseMode
from telegram.ext import CallbackContext, CommandHandler, MessageHandler, Filters, ConversationHandler, Updater
from ChatGPT_HKBU_Copy import HKBU_ChatGPT
from pymongo import MongoClient
import datetime
import logging
import os
import re
import configparser

# Initialize config
# config = configparser.ConfigParser()
# config.read('../config.ini')
DB_url=os.getenv('MONGODB_DB_URL')

# MongoDB setup
client = MongoClient(DB_url)
db = client['database']
movie_list = db['movie'].distinct("name")

# Define states for the conversation
START, SELECT_MOVIE, QACTION, ADD_COMMENT, SEARCH_MOVIE = range(5)  # Added SELECT_MOVIE

def escape_markdown(text: str) -> str:
    """Escape all reserved MarkdownV2 characters."""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def search_movies(partial_name: str) -> list:
    """Search for movies with partial name matching (case-insensitive)."""
    regex = {'$regex': f'.*{partial_name}.*', '$options': 'i'}
    movies = db['movie'].find({'name': regex}, {'name': 1, '_id': 0}).limit(10)
    return [movie['name'] for movie in movies]

def recommend_movies(update: Update, context: CallbackContext) -> int:
    """Use ChatGPT to recommend 5 similar movies."""
    movie_name = context.user_data.get('movie_name', None)

    if not movie_name:
        update.message.reply_text(
            "❌ No movie selected. Please select a movie first or type a movie name.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return START

    global chatgpt
    # Ask ChatGPT to recommend similar movies
    prompt = f"Based on the movie '{movie_name}', recommend 5 similar movies with a brief description for each."
    reply_message = chatgpt.submit(prompt)

    # Send the response back to the user
    update.message.reply_text(
        f"🎥 Recommendations based on *{escape_markdown(movie_name)}*:\n\n{reply_message}",
        parse_mode=None
    )

def start(update: Update, context: CallbackContext) -> int:
    """Start the conversation."""
    update.message.reply_text(
        '👋👱🏼‍♀️ **Hello, nice to meet you\!**\nI am your 🎬🍿 *movie advisor* \n\nWhich *movie* you would like to know more about\?',
        parse_mode=ParseMode.MARKDOWN_V2
    )
    return START

def user_selection(update: Update, context: CallbackContext) -> int:
    movie_name = ' '.join(update.message.text.strip().split()).title()
    
    if movie_name in movie_list:
        context.user_data['movie_name'] = movie_name
        return show_movie_details(update, context, movie_name)
    
    matched_movies = search_movies(movie_name)
    if not matched_movies:
        update.message.reply_text("❌ No matches found. Try again or /end.")
        return START
    
    if len(matched_movies) == 1:
        context.user_data['movie_name'] = matched_movies[0]
        return show_movie_details(update, context, matched_movies[0])
    
    # Escape all movie names to avoid Markdown V2 parsing issues
    escaped_movies = [escape_markdown(m) for m in matched_movies]
    update.message.reply_text(
        f"🔍 Found {len(matched_movies)} matches:\n\n" +
        "\n".join([f"• {movie}" for movie in escaped_movies]) +
        "\n\nReply with the *exact* name or /end.",
        parse_mode=None
    )
    return SELECT_MOVIE

def select_movie(update: Update, context: CallbackContext) -> int:
    """Handle movie selection from wildcard search results."""
    movie_name = ' '.join(update.message.text.strip().split()).title()
    if movie_name in movie_list:
        context.user_data['movie_name'] = movie_name
        return show_movie_details(update, context, movie_name)
    else:
        update.message.reply_text("❌ Invalid selection. Please choose from the list or /end.")
        return SELECT_MOVIE


def show_movie_details(update: Update, context: CallbackContext, movie_name: str) -> int:
    """Display movie details with proper escaping."""
    document = db['movie'].find_one({'name': movie_name})
    if not document:
        update.message.reply_text("❌ Movie not found in database.")
        return START
    
    # Escape ALL dynamic text including movie name and description
    escaped_name = escape_markdown(movie_name)
    escaped_desc = escape_markdown(document["description"])
    escaped_date = escape_markdown(str(document["movie_date"]))
    escaped_duration = escape_markdown(str(document["duration"]))
    
    update.message.reply_text(
        f'🎬 *Movie*: {escaped_name}\n'
        f'📜 *Description*: {escaped_desc}\n'
        f'📅 *Release Date*: {escaped_date}\n'
        f'⏳ *Duration*: {escaped_duration}',
        parse_mode=ParseMode.MARKDOWN_V2
    )
    
    # Return to the QACTION state for further actions
    update.message.reply_text(
        escape_markdown("💬 More actions (Chat directly with AI on this movie, or options below):\n"
                        "/comment - Share your thoughts\n"
                        "/query - View reviews\n"
                        "/recommend - Get similar movie recommendations\n"
                        "/end - Exit"),
        parse_mode=ParseMode.MARKDOWN_V2
    )
    return QACTION

# Function to query movie comments
def user_search(update: Update, context: CallbackContext) -> int:
    """Query comments of a movie."""
    msg = update.message.text
    movie_name = context.user_data.get('movie_name')
    
    global chatgpt

    reply_message = chatgpt.submit(f'If {movie_name} is a movie, answer the following question: \n\n {update.message.text}.\n\n Otherwise, say there are no related movie information.')
    logging.info("Update: " + str(update))
    logging.info("context: " + str(context))
    context.bot.send_message(chat_id=update.effective_chat.id, text=reply_message)

    if(movie_name in movie_list):

        update.message.reply_text(f'🔍 Anything you want to ask about *{movie_name}*?', parse_mode=ParseMode.MARKDOWN_V2)
        update.message.reply_text(
        f'💬 More actions  (Chat directly with AI on this movie, or options below)\:\n'
        '/comment \- Share your thoughts or feedback\n'
        '/query \- View comments from others\n'
        '/recommend - Get similar movie recommendations\n'
        '/end \- End the conversation at any time',
        parse_mode=ParseMode.MARKDOWN_V2
        )
        return QACTION
    else:
        update.message.reply_text(f'🔍 Anything you want to ask about *{movie_name}*?\n\n/end \- End the conversation at any time', parse_mode=ParseMode.MARKDOWN_V2)
        return SEARCH_MOVIE

def ask_comment(update: Update, context: CallbackContext) -> int:

    logging.info("ask comment")
    update.message.reply_text('Please give us some comments')
    return ADD_COMMENT

# Function to add comments
def add_comment(update: Update, context: CallbackContext) -> int:

    movie_name = context.user_data.get('movie_name')
    comment = update.message.text

    logging.info("movie_name: " + str(movie_name))

    if movie_name in movie_list:
        # Insert the record
        record={'name':movie_name,'comment':comment, 'datetime':datetime.datetime.now()}
        db['comment'].insert_one(record)
        update.message.reply_text(f'Thanks for your comment\! 😊', parse_mode=ParseMode.MARKDOWN_V2)

        
        update.message.reply_text(f'🔍 Anything you want to ask about *{movie_name}*?', parse_mode=ParseMode.MARKDOWN_V2)
        update.message.reply_text(
        f'💬 More actions (Chat directly with AI on this movie, or options below)\:\n'
        '/comment \- Share your thoughts or feedback\n'
        '/query \- View comments from others\n'
        '/recommend - Get similar movie recommendations\n'
        '/end \- End the conversation at any time',
        parse_mode=ParseMode.MARKDOWN_V2
        )
        return QACTION
    else:
        update.message.reply_text('Sorry this movie does not exist, please try again.(1)')
        return START



def query_movie(update: Update, context: CallbackContext) -> int:
    """List comments for the queried movie."""
    movie_name = context.user_data.get('movie_name')

    #logging.info("msg: " + str(msg))
    logging.info("movie_name: " + str(movie_name))

    if movie_name in movie_list:
        comments_summary =  getMovieSummary(movie_name)
        update.message.reply_text(
        f'🎬 Movie: {movie_name}\n'
        f'💬 Reivew: \n{comments_summary}'
        )


        update.message.reply_text(f'🔍 Anything you want to ask about *{movie_name}*?', parse_mode=ParseMode.MARKDOWN_V2)
        update.message.reply_text(
        f'💬 More actions (Chat directly with AI on this movie, or options below)\:\n'
        '/comment \- Share your thoughts or feedback\n'
        '/query \- View comments from others\n'
        '/recommend - Get similar movie recommendations\n'
        '/end \- End the conversation at any time',
        parse_mode=ParseMode.MARKDOWN_V2
        )
        return QACTION
    else:
        update.message.reply_text('Sorry this movie does not exist, please try again(2)')
    
    return START

def getMovieSummary(movie_name):
    
    comments_summary =''
    
    if movie_name in movie_list:

        # Retrieve and display the latest 100 comments summary
        documents = db['comment'].find({'name':movie_name},{"comment": 1,"datetime":1,"_id": 0}).sort("datetime", -1).limit(100)  # Sort by datetime descending, limit to 10
        latest_comments=list(document['comment'] for document in documents)

        if latest_comments:
            comments_summary = "\n".join(latest_comments)
            global chatgpt
            reply_message = chatgpt.submit(f'Here are movie comments: {latest_comments}\. Please generate a concise movie review summary, ensuring no additional details are included\.')
            return reply_message
        else: return "No comments yet"
    
    return "No comments yet"
    
    

def end_conversation(update: Update, context: CallbackContext) -> int:
    
    update.message.reply_text('Goodbye 👋🏻', parse_mode=ParseMode.MARKDOWN_V2)
    return ConversationHandler.END  # Ends the conversation

# Added by jack to avoid no response before /start >
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
# < Added by jack to avoid no response before /start

# Main function to set up the bot and handlers
def main() -> None:
    # updater = Updater(token=(config['TELEGRAM']['ACCESS_TOKEN']), use_context=True)
    updater = Updater(token=(os.getenv('TELEGRAM_ACCESS_TOKEN')), use_context=True)
    dispatcher = updater.dispatcher
    
    global chatgpt
    #chatgpt = HKBU_ChatGPT(config)
    chatgpt = HKBU_ChatGPT()

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            START: [
                MessageHandler(Filters.text & ~Filters.command, user_selection),
                CommandHandler('end', end_conversation)
            ],
            SELECT_MOVIE: [  # Added this state
                MessageHandler(Filters.text & ~Filters.command, select_movie),
                CommandHandler('end', end_conversation)
            ],
            QACTION: [
                CommandHandler('comment', ask_comment),
                CommandHandler('query', query_movie),
                CommandHandler('recommend', recommend_movies),  # Add the /recommend command here
                CommandHandler('end', end_conversation),
                MessageHandler(Filters.text & ~Filters.command, user_search),
            ],
            ADD_COMMENT: [
                MessageHandler(Filters.text & ~Filters.command, add_comment),
                CommandHandler('end', end_conversation)
            ],
            SEARCH_MOVIE: [
                MessageHandler(Filters.text & ~Filters.command, user_search),
                CommandHandler('end', end_conversation)
            ]
        },
        fallbacks=[]
    )

    dispatcher.add_handler(conv_handler)
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()