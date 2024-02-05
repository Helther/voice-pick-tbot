from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from telegram import Bot, request
import asyncio
import os.path
from voice_bot.modules.bot_handlers import (
    start_cmd,
    gen_audio_cmd,
    help_cmd,
    gen_audio_inline,
    gen_audio_from_voice,
    retry_button,
    error_handler,
    toggle_inline_cmd,
    QUERY_PATTERN_RETRY,
    tts_work_thread
)
from voice_bot.modules.bot_settings_menu import get_settings_menu_handler
from voice_bot.modules.bot_voice_addition_menu import get_add_voice_menu_handler
import voice_bot.modules.bot_utils as utils


def initialize_bot_data() -> None:
    utils.config.load_config(os.path.join(utils.DATA_PATH, utils.CONFIG_FILE_NAME))
    utils.FOLDER_CHAR_LIMIT = os.statvfs(utils.VOICES_PATH).f_namemax


def init_http_request() -> request.HTTPXRequest:
    return request.HTTPXRequest(http_version="1.1", connection_pool_size=8, read_timeout=30, write_timeout=30)


async def init_bot_settings() -> Bot:
    bot = Bot(utils.config.token, request=init_http_request(),
              get_updates_request=init_http_request())
    cmds = [("gen", "Synthesize audio from provided text"),
            ("add_voice", "Add your custom voice"),
            ("toggle_inline", "Toggle audio generation via text message"),
            ("settings", "Customize audio synthesis parameters"),
            ("help", "Get command usage help")]
    await bot.set_my_commands(commands=cmds, language_code="en")
    return bot


def create_bot() -> Bot:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    task = loop.create_task(init_bot_settings())
    loop.run_until_complete(task)

    return task.result()


def run_application() -> None:

    application = Application.builder().bot(create_bot()).build()

    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("gen", gen_audio_cmd))
    application.add_handler(CommandHandler("toggle_inline", toggle_inline_cmd))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(get_settings_menu_handler())
    application.add_handler(get_add_voice_menu_handler())
    application.add_handler(CallbackQueryHandler(retry_button, pattern=f"^{QUERY_PATTERN_RETRY}*"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gen_audio_inline))
    application.add_handler(MessageHandler(filters.VOICE & ~filters.COMMAND, gen_audio_from_voice))

    application.add_error_handler(error_handler)

    tts_work_thread.start()

    application.run_polling()


def main() -> None:
    initialize_bot_data()

    run_application()
    utils.clear_dir(utils.RESULTS_PATH)


if __name__ == "__main__":
    main()
