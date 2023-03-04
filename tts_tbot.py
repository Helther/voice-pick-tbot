from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler
)
import os.path
from os import makedirs
from bot_handlers import start_cmd, gen_audio_cmd, help_cmd, retry_button
import bot_utils


def initialize() -> None:
    if not os.path.exists(bot_utils.RESULTS_PATH):
        makedirs(bot_utils.RESULTS_PATH)
    if not os.path.exists(bot_utils.MODELS_PATH):
        makedirs(bot_utils.MODELS_PATH)
    if not os.path.exists(bot_utils.VOICES_PATH):
        makedirs(bot_utils.VOICES_PATH)

    bot_utils.load_config(os.path.join(bot_utils.DATA_PATH, bot_utils.CONFIG_FILE_NAME))


def run_application() -> None:
    application = Application.builder().token(bot_utils.TOKEN).build()
    # TODO add conversation for voice addition
    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("gen", gen_audio_cmd))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CallbackQueryHandler(retry_button))

    application.run_polling()


def main() -> None:
    initialize()

    run_application()


if __name__ == "__main__":
    main()
