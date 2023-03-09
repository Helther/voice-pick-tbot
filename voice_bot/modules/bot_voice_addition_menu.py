from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    CallbackContext,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from telegram.error import BadRequest
from modules.bot_utils import user_restricted, logger, sanitize_filename, get_user_voice_dir, convert_to_wav
from modules.bot_db import db_handle
from enum import Enum
import os
import shutil
from tortoise.utils.audio import read_audio_file
from modules.bot_settings_menu import report_error
from librosa import get_duration, load


VOICE_DURATION_MIN = 20  # seconds
VOICE_DURATION_MAX = 120
VOICE_ADDITION_MENU_TEXT = "Voice Addition Menu:"
VOICE_ADDITION_GET_NAME_TEXT = "Provide a name for your voice:"
VOICE_ADDITION_GET_AUDIO_TEXT = f"Send one or several audio files of intelligible speech\
    \nUse wav, mp3 or voice recording, provide between {VOICE_DURATION_MIN} seconds and {VOICE_DURATION_MAX} seconds of audio\nThen press Accept:"


class VoiceMenuStates(Enum):
    get_audio = 0
    get_name = 1
    accept = 2
    cancel = 3


class AddVoiceUserData(Enum):
    voice_name = 0
    file_names = 1
    audio_duration = 2

    def clear_user_data(data: dict) -> None:
        data.pop(AddVoiceUserData.voice_name.name, None)
        data.pop(AddVoiceUserData.file_names.name, None)
        data.pop(AddVoiceUserData.audio_duration.name, None)


def create_accept_button() -> InlineKeyboardButton:
    return InlineKeyboardButton("Accept", callback_data=VoiceMenuStates.accept.name)


def create_cancel_button() -> InlineKeyboardButton:
    return InlineKeyboardButton("Cancel", callback_data=VoiceMenuStates.cancel.name)


ADD_VOICE_MARKUP = InlineKeyboardMarkup([[create_accept_button()], [create_cancel_button()]])


@user_restricted
async def add_voice_main_cmd(update: Update, context: CallbackContext) -> int:
    # create setting message and provide buttons
    await update.message.reply_text(f"{VOICE_ADDITION_MENU_TEXT}\n{VOICE_ADDITION_GET_NAME_TEXT}",
                                    reply_markup=InlineKeyboardMarkup([[create_cancel_button()]]))
    return VoiceMenuStates.get_name.value


async def get_audio_files(update: Update, context: CallbackContext) -> int:
    # load file, check it's valid audio, update voice audio duration, show accept button if duration correct
    try:
        current_voice_files = context.user_data.get(AddVoiceUserData.file_names.name, [])
        file_name = str(len(current_voice_files))
        voices_dir = get_user_voice_dir(update.effective_user.id)
        voice_name = context.user_data[AddVoiceUserData.voice_name.name]
        new_voice_dir = os.path.join(voices_dir, voice_name)
        file_path = os.path.join(new_voice_dir, file_name)
        filetype = ""

        if not os.path.exists(voices_dir):
            os.makedirs(voices_dir)
        if not os.path.exists(new_voice_dir):
            os.makedirs(new_voice_dir)
        current_duration = context.user_data.get(AddVoiceUserData.audio_duration.name, 0)
        duration = 0
        if update.message.voice:  # validate voice file
            filetype = ".ogg"
            file_path += filetype
            with open(file_path, mode='w'):
                pass
            file = await context.bot.get_file(update.message.voice)
            await file.download_to_drive(file_path)
            audio, lsr = load(file_path, sr=None)
            duration = get_duration(audio, lsr)

            file_path = convert_to_wav(file_path)
        else:  # should be wav or mp3 audio
            filetype = update.message.audio.file_name[-4:]
            file_path += filetype
            with open(file_path, mode='w'):
                pass
            file = await context.bot.get_file(update.message.audio)
            await file.download_to_drive(file_path)
            read_audio_file(file_path)
            duration = update.message.audio.duration

        context.user_data[AddVoiceUserData.audio_duration.name] = current_duration + duration
        current_voice_files.append(file_name + filetype)
        context.user_data[AddVoiceUserData.file_names.name] = current_voice_files

    except BaseException as e:
        logger.error(msg="Exception while get_audio_files in Add voice menu", exc_info=e)
        await update.message.reply_text("Internal Server Error: try again later please")
        return await destroy_add_voice_menu(update, context)

    return VoiceMenuStates.get_audio.value  # continue adding


async def get_voice_name(update: Update, context: CallbackContext) -> int:
    # get and verify voice name
    try:
        name = sanitize_filename(update.message.text)
        user_voices = db_handle.get_user_voices(update.effective_user.id)  # (id, name) pairs or None if no voices
        user_voices = [name for id, name in user_voices]
        assert name and (user_voices is None or name not in user_voices)
        context.user_data[AddVoiceUserData.voice_name.name] = name
        await update.message.reply_text(f"{VOICE_ADDITION_MENU_TEXT}\nVoice name: {name}\n{VOICE_ADDITION_GET_AUDIO_TEXT}",
                                        reply_markup=ADD_VOICE_MARKUP)
    except BaseException as e:
        logger.error(msg="Exception while get_voice_name in Add voice menu", exc_info=e)
        await update.message.reply_text("Invalid voice name provided")
        return VoiceMenuStates.get_name.value  # second chance

    return VoiceMenuStates.get_audio.value


async def accept(update: Update, context: CallbackContext) -> int:
    try:
        query = update.callback_query
        await query.answer()

        current_voice_files = context.user_data.get(AddVoiceUserData.file_names.name, [])
        added_files_str = "\nAdded audio files:"
        for file in current_voice_files:
            added_files_str += f"\n{file}"
        current_duration = context.user_data.get(AddVoiceUserData.audio_duration.name, 0)
        if VOICE_DURATION_MIN > current_duration:
            try:
                await query.edit_message_text(f"{VOICE_ADDITION_MENU_TEXT}\nAudio duration is too short (minimum is {VOICE_DURATION_MIN} seconds), \
add more please (current duration: {current_duration} seconds){added_files_str}", reply_markup=ADD_VOICE_MARKUP)
            except BadRequest:  # ignore telegram.error.BadRequest: Message is not modified
                pass
            return VoiceMenuStates.get_audio.value
        elif current_duration > VOICE_DURATION_MAX:
            try:
                await query.edit_message_text(f"{VOICE_ADDITION_MENU_TEXT}\nAudio duration is too long \
(maximum is {VOICE_DURATION_MAX} seconds (current duration: {current_duration} seconds){added_files_str}", reply_markup=ADD_VOICE_MARKUP)
            except BadRequest:
                pass
            return await destroy_add_voice_menu(update, context)

        name = context.user_data[AddVoiceUserData.voice_name.name]
        db_handle.insert_user_voice(update.effective_user.id, name,
                                    os.path.join(get_user_voice_dir(update.effective_user.id), name))
        await query.edit_message_text(f"{VOICE_ADDITION_MENU_TEXT}\nSuccessfully added new voice: {name}")
        AddVoiceUserData.clear_user_data(context.user_data)
        return ConversationHandler.END

    except BaseException as e:
        logger.error(msg="Exception while accept in Add voice menu", exc_info=e)
        await report_error(query, VOICE_ADDITION_MENU_TEXT, "Failed to create the new voice")
        return await destroy_add_voice_menu(update, context)


async def cancel(update: Update, context: CallbackContext) -> int:
    return await destroy_add_voice_menu(update, context)


async def destroy_add_voice_menu(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    if query:
        await query.answer()
    # Cleanup user_data if exists (voice dir)
    try:
        shutil.rmtree(os.path.join(get_user_voice_dir(update.effective_user.id), context.user_data[AddVoiceUserData.voice_name.name]))
    except BaseException:
        pass
    AddVoiceUserData.clear_user_data(context.user_data)
    if query:
        await query.edit_message_text("Voice addition finished")
    return ConversationHandler.END


def get_add_voice_menu_handler() -> ConversationHandler:
    """create menu state machine"""
    return ConversationHandler(
        entry_points=[CommandHandler("add_voice", add_voice_main_cmd)],
        states={
            VoiceMenuStates.get_audio.value: [MessageHandler(filters.VOICE | filters.AUDIO, get_audio_files),
                                              CallbackQueryHandler(accept, pattern=VoiceMenuStates.accept.name),
                                              CallbackQueryHandler(cancel, pattern=VoiceMenuStates.cancel.name)],
            VoiceMenuStates.get_name.value: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_voice_name),
                                             CallbackQueryHandler(cancel, pattern=VoiceMenuStates.cancel.name)],
        },
        fallbacks=[CallbackQueryHandler(destroy_add_voice_menu)]
    )
