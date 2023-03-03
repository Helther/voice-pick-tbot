from telegram.ext import Application, CommandHandler, CallbackQueryHandler
import os.path
from os import makedirs
from tortoise_api import RESULTS_PATH, SCRIPT_PATH
from bot_handlers import start_cmd, gen_audio_cmd, help_cmd, retry_button
import bot_utils


def initialize() -> None:
    if not os.path.exists(RESULTS_PATH):
        makedirs(RESULTS_PATH)
    bot_utils.load_config(os.path.join(SCRIPT_PATH, "config"))




def run_application() -> None:
    application = Application.builder().token(bot_utils.TOKEN).build()

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
