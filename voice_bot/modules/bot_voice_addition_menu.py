from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, User
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    CallbackContext,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from telegram.error import BadRequest
from modules.bot_utils import (
    user_restricted,
    logger,
    sanitize_filename,
    get_user_voice_dir,
    convert_to_wav,
    get_text_locale,
    get_cis_locale_dict
)
from modules.bot_db import db_handle
from modules.bot_settings import MAX_USER_VOICES_COUNT
from enum import Enum
import os
import shutil
from tortoise.utils.audio import read_audio_file
from modules.bot_settings_menu import report_error
from librosa import get_duration, load


VOICE_DURATION_MIN = 15  # seconds
VOICE_DURATION_MAX = 120
VOICE_ADDITION_MENU_TEXT = "Voice Addition Menu:"
VOICE_ADDITION_GET_NAME_TEXT = "Provide a text message with a name for the new voice (use latin):"
VOICE_ADDITION_GET_AUDIO_TEXT = f"""Send one or several audio files of intelligible, clear speech
    \nUse wav, mp3 or voice recordingthough quality wil likely be subpar), provide between {VOICE_DURATION_MIN}s and
     {VOICE_DURATION_MAX}s of audio\nThen press 'Accept':"""
VOICE_ADDITION_MENU_TEXT_RU = "Меню добавления голоса:"
VOICE_ADDITION_GET_NAME_TEXT_RU = "Отправьте текстовое сообщение с именем нового голоса (используйте латиницу):"
VOICE_ADDITION_GET_AUDIO_TEXT_RU = (f"Отправьте один или множество аудио файлов разборчивой чистой речи "
                                    f"в формате wav, mp3 или голосовую запись(чем хуже качество записи - тем хуже точность голоса), предоставьте от {VOICE_DURATION_MIN}сек. до "
                                    f"{VOICE_DURATION_MAX}сек. аудио\nПосле чего нажмите 'Принять':")


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


def create_accept_button(user: User) -> InlineKeyboardButton:
    acc_str = get_text_locale(user, get_cis_locale_dict("Принять"), "Accept")
    return InlineKeyboardButton(acc_str, callback_data=VoiceMenuStates.accept.name)


def create_cancel_button(user: User) -> InlineKeyboardButton:
    cancel_str = get_text_locale(user, get_cis_locale_dict("Отмена"), "Cancel")
    return InlineKeyboardButton(cancel_str, callback_data=VoiceMenuStates.cancel.name)


def create_markup(user: User) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[create_accept_button(user)], [create_cancel_button(user)]])


@user_restricted
async def add_voice_main_cmd(update: Update, context: CallbackContext) -> int:
    # create setting message and provide buttons if addition is possible
    voices = db_handle.get_user_voices(update.effective_user.id)
    if len(voices) >= MAX_USER_VOICES_COUNT:
        reply = get_text_locale(update.effective_user, get_cis_locale_dict((f"{VOICE_ADDITION_MENU_TEXT_RU}\nОшибка: вы превысили максимальное число пользовательских голосов: {MAX_USER_VOICES_COUNT}\n"
                                                                            "Пожалуйста удалите лишний голос через меню /settings и попробуйте снова")),
                                (f"{VOICE_ADDITION_MENU_TEXT}\nError: you have exceeded maximum number of custom voices: {MAX_USER_VOICES_COUNT}\n"
                                "Please remove any custom voice via /settings and try again"))
        await update.message.reply_html(reply)
        return ConversationHandler.END
    reply = get_text_locale(update.effective_user, get_cis_locale_dict(f"{VOICE_ADDITION_MENU_TEXT_RU}\n{VOICE_ADDITION_GET_NAME_TEXT_RU}"), f"{VOICE_ADDITION_MENU_TEXT}\n{VOICE_ADDITION_GET_NAME_TEXT}")
    await update.message.reply_text(reply, reply_markup=InlineKeyboardMarkup([[create_cancel_button(update.effective_user)]]))
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

    except Exception as e:
        logger.error(msg="Exception while get_audio_files in Add voice menu", exc_info=e)
        reply = get_text_locale(update.effective_user, get_cis_locale_dict("Внутренняя ошибка сервера: пожалуйста повторите попытку"), "Internal Server Error: try again later please")
        await update.message.reply_text(reply)
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
        reply = get_text_locale(update.effective_user, get_cis_locale_dict(f"{VOICE_ADDITION_MENU_TEXT_RU}\nИмя голоса: {name}\n{VOICE_ADDITION_GET_AUDIO_TEXT_RU}"),
                                f"{VOICE_ADDITION_MENU_TEXT}\nVoice name: {name}\n{VOICE_ADDITION_GET_AUDIO_TEXT}")
        await update.message.reply_text(reply, reply_markup=create_markup(update.effective_user))
    except Exception as e:
        logger.error(msg="Exception while get_voice_name in Add voice menu", exc_info=e)
        reply = get_text_locale(update.effective_user, get_cis_locale_dict("Ошибка: предоставлено недоступное имя, попробуйте еще раз"),
                                "Error: invalid voice name provided, please try again")
        await update.message.reply_text(reply)
        return VoiceMenuStates.get_name.value  # second chance

    return VoiceMenuStates.get_audio.value


async def accept(update: Update, context: CallbackContext) -> int:
    try:
        query = update.callback_query
        await query.answer()

        current_voice_files = context.user_data.get(AddVoiceUserData.file_names.name, [])
        added_files_str = get_text_locale(update.effective_user, get_cis_locale_dict("\nДобавленные файлы:"), "\nAdded audio files:")
        for file in current_voice_files:
            added_files_str += f"\n{file}"
        current_duration = context.user_data.get(AddVoiceUserData.audio_duration.name, 0)
        if VOICE_DURATION_MIN > current_duration:
            try:
                reply = get_text_locale(update.effective_user, get_cis_locale_dict((f"{VOICE_ADDITION_MENU_TEXT_RU}\nНедостаточная длительность аудио (минимум {VOICE_DURATION_MIN} сек.), "
                                                                                    f"добавьте больше файлов пожалуйста (текущая длительность: {current_duration} сек.){added_files_str}")),
                                        (f"{VOICE_ADDITION_MENU_TEXT}\nAudio duration is too short (minimum is {VOICE_DURATION_MIN}s), "
                                        f"add more please (current duration: {current_duration}s){added_files_str}"))
                await query.edit_message_text(reply, reply_markup=create_markup(update.effective_user))
            except BadRequest:  # ignore telegram.error.BadRequest: Message is not modified
                pass
            return VoiceMenuStates.get_audio.value
        elif current_duration > VOICE_DURATION_MAX:
            try:
                reply = get_text_locale(update.effective_user, get_cis_locale_dict((f"{VOICE_ADDITION_MENU_TEXT_RU}\nИзбыточная длительность аудио "
                                                                                    f"(максимум {VOICE_DURATION_MAX} сек. (текущая длительность: {current_duration} сек.){added_files_str}")),
                                        (f"{VOICE_ADDITION_MENU_TEXT}\nAudio duration is too long "
                                        f"(maximum is {VOICE_DURATION_MAX}s (current duration: {current_duration}s){added_files_str}"))
                await query.edit_message_text(reply, reply_markup=create_markup(update.effective_user))
            except BadRequest:
                pass
            return await destroy_add_voice_menu(update, context)

        name = context.user_data[AddVoiceUserData.voice_name.name]
        db_handle.insert_user_voice(update.effective_user.id, name,
                                    os.path.join(get_user_voice_dir(update.effective_user.id), name))
        reply = get_text_locale(update.effective_user, get_cis_locale_dict(f"{VOICE_ADDITION_MENU_TEXT_RU}\nНовый голос был успешно добавлен: {name}"),
                                f"{VOICE_ADDITION_MENU_TEXT}\nSuccessfully added new voice: {name}")
        await query.edit_message_text(reply)
        AddVoiceUserData.clear_user_data(context.user_data)
        return ConversationHandler.END

    except Exception as e:
        logger.error(msg="Exception while accept in Add voice menu", exc_info=e)
        menu_name = get_text_locale(update.effective_user, get_cis_locale_dict(VOICE_ADDITION_MENU_TEXT_RU), VOICE_ADDITION_MENU_TEXT)
        msg = get_text_locale(update.effective_user, get_cis_locale_dict("Ошибка: не удалось добавить новый голос"), "Error: Failed to create the new voice")
        await report_error(query, menu_name, msg)
        return await destroy_add_voice_menu(update, context)


def cleanup_data(user_id: int, voice_dir: str, user_data) -> None:
    # Cleanup user_data if exists (and voice dir),
    try:
        shutil.rmtree(os.path.join(get_user_voice_dir(user_id), voice_dir))
    except Exception:
        pass
    AddVoiceUserData.clear_user_data(user_data)


async def cancel(update: Update, context: CallbackContext) -> int:
    return await destroy_add_voice_menu(update, context)


async def destroy_add_voice_menu(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    if query:
        await query.answer()
    cleanup_data(update.effective_user.id, context.user_data.get(AddVoiceUserData.voice_name.name, None), context.user_data)
    if query:
        reply = get_text_locale(update.effective_user, get_cis_locale_dict("Добавление нового голоса было отменено"), "Voice addition exited")
        await query.edit_message_text(reply)
    return ConversationHandler.END


async def fallback(update: Update, context: CallbackContext) -> int:
    cleanup_data(update.effective_user.id, context.user_data.get(AddVoiceUserData.voice_name.name, None), context.user_data)
    reply = get_text_locale(update.effective_user, get_cis_locale_dict("Добавление нового голоса было не завершено, отмена... пожалуйста повторите позже"),
                            "Voice addition left unfinished, cancelling... please try again later")
    await update.effective_message.reply_text(reply)
    return ConversationHandler.END


def get_add_voice_menu_handler() -> ConversationHandler:
    """
    create menu state machine
    handle all non menu button presses and messages as cancellation
    """
    return ConversationHandler(
        entry_points=[CommandHandler("add_voice", add_voice_main_cmd)],
        states={
            VoiceMenuStates.get_audio.value: [MessageHandler(filters.VOICE | filters.AUDIO, get_audio_files),
                                              CallbackQueryHandler(accept, pattern=VoiceMenuStates.accept.name),
                                              CallbackQueryHandler(cancel, pattern=VoiceMenuStates.cancel.name)],
            VoiceMenuStates.get_name.value: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_voice_name),
                                             CallbackQueryHandler(cancel, pattern=VoiceMenuStates.cancel.name)]
        },
        fallbacks=[CallbackQueryHandler(fallback)]
    )
