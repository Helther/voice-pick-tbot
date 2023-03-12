from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, CallbackQuery
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    CallbackContext,
    CallbackQueryHandler
)
from modules.bot_utils import user_restricted, answer_query, config, logger
from enum import Enum
from modules.bot_db import db_handle
import json
from itertools import zip_longest


class Emotions(Enum):
    Neutral = 0
    Sad = 1
    Angry = 2
    Happy = 3
    Scared = 4


SETTINGS_MENU_TEXT = "Edit Settings:"
VOICES_MENU_TEXT = "Edit Settings:\nSelect Voice:"
EMOT_MENU_TEXT = "Edit Settings:\nSelect Emotion:"
SAMPLES_MENU_TEXT = "Edit Settings:\nSelect Number of Samples:"
SAMPLES_MENU_COUNT_MAX = 5
EMOTION_STRINGS = {
    Emotions.Neutral.name: Emotions.Neutral,
    Emotions.Sad.name: Emotions.Sad,
    Emotions.Angry.name: Emotions.Angry,
    Emotions.Happy.name: Emotions.Happy,
    Emotions.Scared.name: Emotions.Scared,
}

EMOTION_VALUES = {
    Emotions.Neutral.value: Emotions.Neutral,
    Emotions.Sad.value: Emotions.Sad,
    Emotions.Angry.value: Emotions.Angry,
    Emotions.Happy.value: Emotions.Happy,
    Emotions.Scared.value: Emotions.Scared
}


class SettingsMenuStates(Enum):
    select_setting = 0
    select_voice = 1
    select_emotion = 2
    select_samples = 3
    close_menu = 4
    back = 5


class UserSettings(object):
    def __init__(self, voice: str, emot: str, samples: int) -> None:
        self.voice = voice
        self.emotion = emot
        self.samples_num = samples


"""-----------------------------------Menu constructors-----------------------------------"""


def build_settings_menu() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("Select Voice", callback_data=SettingsMenuStates.select_voice.name)],
        [InlineKeyboardButton("Select Emotion", callback_data=SettingsMenuStates.select_emotion.name)],
        [InlineKeyboardButton("Select Number Of Samples", callback_data=SettingsMenuStates.select_samples.name)],
        [InlineKeyboardButton("Close", callback_data=SettingsMenuStates.close_menu.name)]
    ]
    return InlineKeyboardMarkup(buttons)


def build_emotion_menu() -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(emot_str, callback_data=emot_str)] for emot_str in EMOTION_STRINGS.keys()]
    buttons.append([InlineKeyboardButton("Back", callback_data=SettingsMenuStates.back.name)])
    return InlineKeyboardMarkup(buttons)


def build_samples_menu() -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(str(ind), callback_data=str(ind))] for ind in range(1, SAMPLES_MENU_COUNT_MAX + 1)]
    buttons.append([InlineKeyboardButton("Back", callback_data=SettingsMenuStates.back.name)])
    return InlineKeyboardMarkup(buttons)


SETTINGS_MARKUP = build_settings_menu()
EMOTIONS_MARKUP = build_emotion_menu()
SAMPLES_MARKUP = build_samples_menu()


def build_voices_list(user_id: int) -> InlineKeyboardMarkup:
    """
    voice btn callback is following json format:
    {
        is_default: False,
        data: '0'
    }
    """
    default_voices = config.default_voices
    buttons_default_col = [InlineKeyboardButton(name, callback_data=json.dumps({"is_default": True, "data": name})) for name in default_voices]
    user_voices = db_handle.get_user_voices(user_id)  # tuples of (id, name)
    if user_voices:
        buttons_user_col = [InlineKeyboardButton(name, callback_data=json.dumps({"is_default": False, "data": id})) for id, name in user_voices]
    else:
        buttons_user_col = []
    menu = []
    for default, user in zip_longest(buttons_default_col, buttons_user_col):
        menu.append([])
        if default:
            menu[len(menu) - 1].append(default)
        if user:
            menu[len(menu) - 1].append(user)
    menu.append([InlineKeyboardButton("Back", callback_data=SettingsMenuStates.back.name)])
    return InlineKeyboardMarkup(menu)


async def destroy_setings_menu(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    context.application.create_task(answer_query(query), update=update)

    await query.edit_message_reply_markup()
    return ConversationHandler.END


async def report_error(query: CallbackQuery, menu_name: str, err_msg: str) -> None:
    await query.edit_message_text(f"{menu_name}\nError: {err_msg}", reply_markup=None)


def get_emotion_name(user_id: int) -> str:
    return EMOTION_VALUES[db_handle.get_user_emotion_setting(user_id)].name


def get_user_settings(user_id: int) -> UserSettings:
    voice = db_handle.get_user_voice_setting(user_id)
    emot = get_emotion_name(user_id)
    samples_num = db_handle.get_user_samples_setting(user_id)
    if emot == Emotions.Neutral.name:  # if Neutral then don't prepend emotion string
        emot = None
    return UserSettings(voice, emot, samples_num)


@user_restricted
async def settings_main_cmd(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text(SETTINGS_MENU_TEXT, reply_markup=SETTINGS_MARKUP)
    return SettingsMenuStates.select_setting

"""-----------------------------------Menu callbacks-----------------------------------"""


async def choose_setting(update: Update, context: CallbackContext) -> int:
    """Main settings menu"""
    query = update.callback_query
    await query.answer()

    if query.data == SettingsMenuStates.select_emotion.name:
        try:
            active_emot = get_emotion_name(update.effective_user.id)
            await query.edit_message_text(f"{EMOT_MENU_TEXT}\nCurrent: {active_emot}", reply_markup=EMOTIONS_MARKUP)
        except BaseException as e:
            logger.error(msg="Exception while choose_setting: ", exc_info=e)
            await report_error(query, SETTINGS_MENU_TEXT, "Failed to fetch Emotion setting")
            return ConversationHandler.END

        return SettingsMenuStates.select_emotion

    if query.data == SettingsMenuStates.select_voice.name:
        try:
            active_voice = db_handle.get_user_voice_setting(update.effective_user.id)
            await query.edit_message_text(f"{VOICES_MENU_TEXT}\nCurrent: {active_voice}\nDefault voices:\tUser voices:", reply_markup=build_voices_list(update.effective_user.id))
        except BaseException as e:
            logger.error(msg="Exception while choose_setting: ", exc_info=e)
            await report_error(query, SETTINGS_MENU_TEXT, "Failed to fetch Voice setting")
            return ConversationHandler.END

        return SettingsMenuStates.select_voice

    if query.data == SettingsMenuStates.select_samples.name:
        try:
            samples_num = db_handle.get_user_samples_setting(update.effective_user.id)
            await query.edit_message_text(f"{SAMPLES_MENU_TEXT}\nCurrent: {samples_num}", reply_markup=SAMPLES_MARKUP)
        except BaseException as e:
            logger.error(msg="Exception while choose_setting: ", exc_info=e)
            await report_error(query, SETTINGS_MENU_TEXT, "Failed to fetch Number Of Samples setting")
            return ConversationHandler.END

        return SettingsMenuStates.select_samples

    if query.data == SettingsMenuStates.close_menu.name:
        await query.edit_message_reply_markup()
        return ConversationHandler.END


async def choose_voice(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    if query.data != SettingsMenuStates.back.name:
        try:
            data_json = json.loads(query.data)
            if data_json["is_default"]:
                db_handle.update_default_voice_setting(update.effective_user.id, data_json["data"])
            else:
                db_handle.update_user_voice_setting(update.effective_user.id, int(data_json["data"]))
        except BaseException as e:
            logger.error(msg="Exception while choose_voice: ", exc_info=e)
            await report_error(query, SETTINGS_MENU_TEXT, "Failed to set Voice setting")
            return ConversationHandler.END

    await query.edit_message_text(SETTINGS_MENU_TEXT, reply_markup=SETTINGS_MARKUP)
    return SettingsMenuStates.select_setting


async def choose_emotion(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    if query.data != SettingsMenuStates.back.name:
        try:
            db_handle.update_emot_setting(update.effective_user.id, EMOTION_STRINGS[query.data].value)
        except BaseException as e:
            logger.error(msg="Exception while choose_voice: ", exc_info=e)
            await report_error(query, SETTINGS_MENU_TEXT, "Failed to set active Emotion")
            return ConversationHandler.END

    await query.edit_message_text(SETTINGS_MENU_TEXT, reply_markup=SETTINGS_MARKUP)
    return SettingsMenuStates.select_setting


async def choose_samples(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    if query.data != SettingsMenuStates.back.name:
        try:
            db_handle.update_user_samples_setting(update.effective_user.id, int(query.data))
        except BaseException as e:
            logger.error(msg="Exception while choose_samples: ", exc_info=e)
            await report_error(query, SETTINGS_MENU_TEXT, "Failed to set active Number Of Samples")
            return ConversationHandler.END

    await query.edit_message_text(SETTINGS_MENU_TEXT, reply_markup=SETTINGS_MARKUP)
    return SettingsMenuStates.select_setting


def get_settings_menu_handler() -> ConversationHandler:
    """create menu state machine"""
    return ConversationHandler(
        entry_points=[CommandHandler("settings", settings_main_cmd)],
        states={
            SettingsMenuStates.select_setting: [CallbackQueryHandler(choose_setting)],
            SettingsMenuStates.select_voice: [CallbackQueryHandler(choose_voice)],
            SettingsMenuStates.select_emotion: [CallbackQueryHandler(choose_emotion)],
            SettingsMenuStates.select_samples: [CallbackQueryHandler(choose_samples)]
        },
        fallbacks=[CallbackQueryHandler(destroy_setings_menu)]
    )
