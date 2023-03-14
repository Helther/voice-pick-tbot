from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, CallbackQuery
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    CallbackContext,
    CallbackQueryHandler
)
from modules.bot_utils import user_restricted, answer_query, config, logger, QUERY_PATTERN_RETRY
from modules.bot_handlers import retry_button
from modules.bot_settings import EMOTION_STRINGS, get_emotion_name
from enum import Enum
from modules.bot_db import db_handle
import json
from itertools import zip_longest
import shutil


SETTINGS_MENU_TEXT = "Edit Settings:"
VOICES_MENU_TEXT = "Edit Settings:\nSelect Voice:"
EMOT_MENU_TEXT = "Edit Settings:\nSelect Emotion:"
SAMPLES_MENU_TEXT = "Edit Settings:\nSelect Number of Samples:"
SAMPLES_MENU_COUNT_MAX = 5
QUERY_PATTERN_SETTINGS = "c_set"


class SettingsMenuStates(Enum):
    select_setting = 0
    select_voice = 1
    select_emotion = 2
    select_samples = 3
    close_menu = 4
    back = 5
    remove_voice = 6


"""-----------------------------------Menu constructors-----------------------------------"""


def build_settings_menu() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("Select Voice", callback_data=QUERY_PATTERN_SETTINGS + SettingsMenuStates.select_voice.name)],
        [InlineKeyboardButton("Select Emotion", callback_data=QUERY_PATTERN_SETTINGS + SettingsMenuStates.select_emotion.name)],
        [InlineKeyboardButton("Select Number Of Samples", callback_data=QUERY_PATTERN_SETTINGS + SettingsMenuStates.select_samples.name)],
        [InlineKeyboardButton("Remove Voice", callback_data=QUERY_PATTERN_SETTINGS + SettingsMenuStates.remove_voice.name)],
        [InlineKeyboardButton("Close", callback_data=QUERY_PATTERN_SETTINGS + SettingsMenuStates.close_menu.name)]
    ]
    return InlineKeyboardMarkup(buttons)


def build_emotion_menu() -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(emot_str, callback_data=QUERY_PATTERN_SETTINGS + emot_str)] for emot_str in EMOTION_STRINGS.keys()]
    buttons.append([InlineKeyboardButton("Back", callback_data=QUERY_PATTERN_SETTINGS + SettingsMenuStates.back.name)])
    return InlineKeyboardMarkup(buttons)


def build_samples_menu() -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(str(ind), callback_data=QUERY_PATTERN_SETTINGS + str(ind))] for ind in range(1, SAMPLES_MENU_COUNT_MAX + 1)]
    buttons.append([InlineKeyboardButton("Back", callback_data=QUERY_PATTERN_SETTINGS + SettingsMenuStates.back.name)])
    return InlineKeyboardMarkup(buttons)


SETTINGS_MARKUP = build_settings_menu()
EMOTIONS_MARKUP = build_emotion_menu()
SAMPLES_MARKUP = build_samples_menu()


def build_voices_list(user_id: int, show_default: bool) -> InlineKeyboardMarkup:
    """
    voice btn callback is following json format:
    {
        is_default: False,
        data: '0',
        name: "voice"
    }
    """
    default_voices = config.default_voices if show_default else []
    buttons_default_col = [InlineKeyboardButton(name, callback_data=QUERY_PATTERN_SETTINGS + json.dumps({"is_default": True, "data": name})) for name in default_voices]
    user_voices = db_handle.get_user_voices(user_id)  # tuples of (id, name)
    if user_voices:
        buttons_user_col = [InlineKeyboardButton(name, callback_data=QUERY_PATTERN_SETTINGS + json.dumps({"is_default": False, "data": id})) for id, name in user_voices]
    else:
        buttons_user_col = []
    menu = []
    for default, user in zip_longest(buttons_default_col, buttons_user_col):
        menu.append([])
        if default:
            menu[len(menu) - 1].append(default)
        if user:
            menu[len(menu) - 1].append(user)
    menu.append([InlineKeyboardButton("Back", callback_data=QUERY_PATTERN_SETTINGS + SettingsMenuStates.back.name)])
    return InlineKeyboardMarkup(menu)


async def destroy_setings_menu(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    context.application.create_task(answer_query(query), update=update)

    await query.edit_message_text(SETTINGS_MENU_TEXT + "\nExited")
    return ConversationHandler.END


async def report_error(query: CallbackQuery, menu_name: str, err_msg: str) -> None:
    await query.edit_message_text(f"{menu_name}\nError: {err_msg}", reply_markup=None)


async def get_query_data(query: CallbackQuery) -> str:
    # and answer it
    await query.answer()
    return query.data[len(QUERY_PATTERN_SETTINGS):]


@user_restricted
async def settings_main_cmd(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text(SETTINGS_MENU_TEXT, reply_markup=SETTINGS_MARKUP)
    return SettingsMenuStates.select_setting

"""-----------------------------------Menu callbacks-----------------------------------"""


async def choose_setting(update: Update, context: CallbackContext) -> int:
    """Main settings menu"""
    query = update.callback_query
    data = await get_query_data(query)
    if data == SettingsMenuStates.select_emotion.name:
        try:
            active_emot = get_emotion_name(update.effective_user.id)
            await query.edit_message_text(f"{EMOT_MENU_TEXT}\nCurrent: {active_emot}", reply_markup=EMOTIONS_MARKUP)
        except Exception as e:
            logger.error(msg="Exception while choose_setting: ", exc_info=e)
            await report_error(query, SETTINGS_MENU_TEXT, "Failed to fetch Emotion setting")
            return ConversationHandler.END

        return SettingsMenuStates.select_emotion

    if data == SettingsMenuStates.select_voice.name:
        try:
            active_voice = db_handle.get_user_voice_setting(update.effective_user.id)
            await query.edit_message_text(f"{VOICES_MENU_TEXT}\nCurrent: {active_voice}\nDefault voices:\tUser voices:", reply_markup=build_voices_list(update.effective_user.id, True))
        except Exception as e:
            logger.error(msg="Exception while choose_setting: ", exc_info=e)
            await report_error(query, SETTINGS_MENU_TEXT, "Failed to fetch Voice setting")
            return ConversationHandler.END

        return SettingsMenuStates.select_voice

    if data == SettingsMenuStates.select_samples.name:
        try:
            samples_num = db_handle.get_user_samples_setting(update.effective_user.id)
            await query.edit_message_text(f"{SAMPLES_MENU_TEXT}\nCurrent: {samples_num}", reply_markup=SAMPLES_MARKUP)
        except Exception as e:
            logger.error(msg="Exception while choose_setting: ", exc_info=e)
            await report_error(query, SETTINGS_MENU_TEXT, "Failed to fetch Number Of Samples setting")
            return ConversationHandler.END

        return SettingsMenuStates.select_samples

    if data == SettingsMenuStates.remove_voice.name:
        try:
            await query.edit_message_text(f"{VOICES_MENU_TEXT} (to remove)", reply_markup=build_voices_list(update.effective_user.id, False))
        except Exception as e:
            logger.error(msg="Exception while choose_setting: ", exc_info=e)
            await report_error(query, SETTINGS_MENU_TEXT, "Failed to fetch User Voices")
            return ConversationHandler.END

        return SettingsMenuStates.remove_voice

    if data == SettingsMenuStates.close_menu.name:
        await query.edit_message_reply_markup()
        return ConversationHandler.END


async def choose_voice(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    data = data = await get_query_data(query)
    if data != SettingsMenuStates.back.name:
        try:
            data_json = json.loads(data)
            if data_json["is_default"]:
                db_handle.update_default_voice_setting(update.effective_user.id, data_json["data"])
            else:
                db_handle.update_user_voice_setting(update.effective_user.id, int(data_json["data"]))
        except Exception as e:
            logger.error(msg="Exception while choose_voice: ", exc_info=e)
            await report_error(query, SETTINGS_MENU_TEXT, "Failed to set Voice setting")
            return ConversationHandler.END

    await query.edit_message_text(SETTINGS_MENU_TEXT, reply_markup=SETTINGS_MARKUP)
    return SettingsMenuStates.select_setting


async def choose_emotion(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    data = await get_query_data(query)
    if data != SettingsMenuStates.back.name:
        try:
            db_handle.update_emot_setting(update.effective_user.id, EMOTION_STRINGS[data].value)
        except Exception as e:
            logger.error(msg="Exception while choose_voice: ", exc_info=e)
            await report_error(query, SETTINGS_MENU_TEXT, "Failed to set active Emotion")
            return ConversationHandler.END

    await query.edit_message_text(SETTINGS_MENU_TEXT, reply_markup=SETTINGS_MARKUP)
    return SettingsMenuStates.select_setting


async def choose_samples(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    data = await get_query_data(query)
    if data != SettingsMenuStates.back.name:
        try:
            db_handle.update_user_samples_setting(update.effective_user.id, int(data))
        except Exception as e:
            logger.error(msg="Exception while choose_samples: ", exc_info=e)
            await report_error(query, SETTINGS_MENU_TEXT, "Failed to set active Number Of Samples")
            return ConversationHandler.END

    await query.edit_message_text(SETTINGS_MENU_TEXT, reply_markup=SETTINGS_MARKUP)
    return SettingsMenuStates.select_setting


async def rem_voice(update: Update, context: CallbackContext) -> int:
    # remove selected voice form db and delete voice folder
    query = update.callback_query
    data = await get_query_data(query)
    if data != SettingsMenuStates.back.name:
        try:
            data_json = json.loads(data)
            voice_dir = db_handle.remove_user_voice(update.effective_user.id, int(data_json["data"]))
            shutil.rmtree(voice_dir)
        except Exception as e:
            logger.error(msg="Exception while rem_voice: ", exc_info=e)
            await report_error(query, SETTINGS_MENU_TEXT, "Failed to remove the Voice")
            return ConversationHandler.END

    await query.edit_message_text(SETTINGS_MENU_TEXT, reply_markup=SETTINGS_MARKUP)
    return SettingsMenuStates.select_setting


async def fallback(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    await update.effective_message.reply_text("Unexpected action performed during settings editing, please try again later")
    return ConversationHandler.END


def get_settings_menu_handler() -> ConversationHandler:
    """
    create menu state machine
    ignore non menu keyboard presses, unless it's retry, anything else is valid outside of the menu
    """
    return ConversationHandler(
        entry_points=[CommandHandler("settings", settings_main_cmd)],
        states={
            SettingsMenuStates.select_setting: [CallbackQueryHandler(choose_setting, pattern=f"^{QUERY_PATTERN_SETTINGS}*")],
            SettingsMenuStates.select_voice: [CallbackQueryHandler(choose_voice, pattern=f"^{QUERY_PATTERN_SETTINGS}*")],
            SettingsMenuStates.select_emotion: [CallbackQueryHandler(choose_emotion, pattern=f"^{QUERY_PATTERN_SETTINGS}*")],
            SettingsMenuStates.select_samples: [CallbackQueryHandler(choose_samples, pattern=f"^{QUERY_PATTERN_SETTINGS}*")],
            SettingsMenuStates.remove_voice: [CallbackQueryHandler(rem_voice, pattern=f"^{QUERY_PATTERN_SETTINGS}*")]
        },
        fallbacks=[CallbackQueryHandler(retry_button, pattern=f"^{QUERY_PATTERN_RETRY}*"), CallbackQueryHandler(fallback)],
        allow_reentry=True
    )
