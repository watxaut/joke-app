import logging

from telegram import Bot, Update
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import src.api as api

logger = logging.getLogger(__name__)

TIMEOUT_MSG = "Oops, something went wrong with the API. Try again later"


def start(bot: Bot, update: Update) -> None:
    logger.info("Command start issued")

    # get user info coming from telegram message
    user_id = str(update.message.chat.id)
    first_name = update.message.chat.first_name

    # add user to DB
    response = api.add_user_telegram(user_id, first_name)
    if not response:
        logger.error("Error while trying to add telegram user!")

    # send telegram message
    bot_message = """
    Hey newcomer! This bot is able to send bad jokes (in spanish for the moment).
    You have 3 options:
    - /send_joke -> which will send a random joke from the DB
    - /rate_joke -> which sends a joke and let's you rate it
    - /validate_joke -> sends a wannabe joke.
    Should it be in the 'curated list' of jokes, it's now your decision

    Have fun!"""
    bot.send_message(chat_id=update.message.chat_id, text=bot_message)


def send_joke(bot: Bot, update: Update) -> None:

    logger.info("Command send_joke issued")

    # query random joke from API
    response = api.get_random_joke()
    if response:
        str_joke = response.json()["joke"]
    else:
        str_joke = "Oops, something went wrong. Try again later"

    bot.send_message(chat_id=update.message.chat_id, text=str_joke)


def rate_joke(bot: Bot, update: Update) -> None:
    logger.info("Command rate_joke issued")

    # query random joke from API
    response = api.get_random_joke()
    if response:
        str_joke = response.json()["joke"]
        id_joke = response.json()["joke_id"]
    else:
        str_joke = TIMEOUT_MSG
        id_joke = -1

    bot.send_message(chat_id=update.message.chat_id, text=str_joke)

    # ratings
    s_ratings = "id: {id_joke} - How would you rate this joke?".format(id_joke=id_joke)

    keyboard = [
        [
            InlineKeyboardButton("0", callback_data=0),
            InlineKeyboardButton("2.5", callback_data=2.5),
            InlineKeyboardButton("5", callback_data=5),
            InlineKeyboardButton("7.5", callback_data=7.5),
            InlineKeyboardButton("10", callback_data=10),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(s_ratings, reply_markup=reply_markup)


def button_rating(bot: Bot, update: Update) -> None:

    chat_id = update.callback_query.message.chat_id
    message_id = update.callback_query.message["message_id"]
    user_id = update.callback_query.from_user.id
    bot_message = update.callback_query.message.text
    user_response = update.callback_query.data

    # TODO: I don't like this approach, there should be another..
    if "rate" in bot_message:

        new_text = "Thanks for rating! :)))"

        f_rating = float(user_response)

        # erase and get id "id: {id} - some-id"
        joke_id = int(bot_message[4:].split(" - ")[0])

        request = api.insert_rating_joke(user_id, joke_id, f_rating)
        if not request:
            logger.error("Something went wrong with 'insert_rating_joke'")

    elif "joke" in bot_message:
        new_text = "Thanks for the feedback! :DD"

        is_joke = "1" == user_response

        # erase and get id "id: {id} - some text"
        validated_joke_id = int(bot_message[4:].split(" - ")[0])

        request = api.update_joke_validation(validated_joke_id, user_id, is_joke)
        if not request:
            logger.error("Something went wrong with 'update_joke_validation'")
    elif "Tag" in bot_message:
        # erase and get id "id: {id} - some text"
        tagged_joke_id = int(bot_message[4:].split(" - ")[0])

        request = api.tag_joke(tagged_joke_id, user_id, user_response)
        if not request:
            logger.error("Something went wrong with 'tag_joke'")
        return None  # we don't want the keyboard to disappear
    else:
        new_text = "Thanks for the feedback brah! :DD"

    bot.editMessageText(new_text, chat_id=chat_id, message_id=message_id)


def validate_joke(bot: Bot, update: Update) -> None:
    logger.info("Command validate_joke issued")

    # query random joke and return only one in a pandas DF
    response = api.get_random_validation_joke()

    if response:
        # unpack joke info and send it to telegram
        str_joke = response.json()["joke"]
        id_joke = response.json()["joke_id"]

        if id_joke == -1:  # API connects but no more jokes to validate

            bot.send_message(chat_id=update.message.chat_id, text="Whoops! No more jokes to validate")
            return None

        # else send message
        bot.send_message(chat_id=update.message.chat_id, text=str_joke)
        # ratings
        s_ratings = "id: {id_joke} - Is this even a joke?".format(id_joke=id_joke)

        keyboard = [[InlineKeyboardButton("Yep", callback_data=1), InlineKeyboardButton("Nope", callback_data=0)]]

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(s_ratings, reply_markup=reply_markup)

    else:  # the table of twitter jokes is already all validated

        bot.send_message(chat_id=update.message.chat_id, text=TIMEOUT_MSG)


def tag_joke(bot: Bot, update: Update) -> None:
    logger.info("Command tag_joke issued")

    r_joke = api.get_untagged_joke()
    if r_joke:
        # unpack joke info and send it to telegram
        str_joke = r_joke.json()["joke"]
        id_joke = r_joke.json()["joke_id"]
        bot.send_message(chat_id=update.message.chat_id, text=str_joke)

        # API connects but no more jokes to tag
        if id_joke == -1:
            return

        # query random joke and return only one in a pandas DF
        r_tags = api.get_tags()

        if r_tags:
            n = 4
            d_tags = r_tags.json()["tags"]
            l_tags = list(d_tags.values())
            l_group = [l_tags[i : i + n] for i in range(0, len(l_tags), n)]
            keyboard = []
            for l_line in l_group:
                l_inline = [InlineKeyboardButton(tag["name"], callback_data=tag["id"]) for tag in l_line]
                keyboard.append(l_inline)

            reply_markup = InlineKeyboardMarkup(keyboard)

            s_tag = "id: {id_joke} - Tag this! (as many tags as you want)".format(id_joke=id_joke)
            update.message.reply_text(s_tag, reply_markup=reply_markup)
