from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler
)
from telegram import Bot
import asyncio
import os.path
from os import makedirs
from bot_handlers import start_cmd, gen_audio_cmd, help_cmd, retry_button, QUERY_PATTERN_RETRY
from bot_settings_menu import get_settings_menu_handler
import bot_utils


def initialize_bot_data() -> None:
    if not os.path.exists(bot_utils.RESULTS_PATH):
        makedirs(bot_utils.RESULTS_PATH)
    if not os.path.exists(bot_utils.MODELS_PATH):
        makedirs(bot_utils.MODELS_PATH)
    if not os.path.exists(bot_utils.VOICES_PATH):
        makedirs(bot_utils.VOICES_PATH)

    bot_utils.config.load_config(os.path.join(bot_utils.DATA_PATH, bot_utils.CONFIG_FILE_NAME))


async def init_bot_settings() -> Bot:
    bot = Bot(bot_utils.config.token)
    cmds = [("gen", "Synthesize audio from provided text"),
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
    # TODO add conversation for voice addition
    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("gen", gen_audio_cmd))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(get_settings_menu_handler())
    application.add_handler(CallbackQueryHandler(retry_button, pattern=f"^{QUERY_PATTERN_RETRY}*"))

    application.run_polling()


def main() -> None:
    initialize_bot_data()

    run_application()


if __name__ == "__main__":
    main()
