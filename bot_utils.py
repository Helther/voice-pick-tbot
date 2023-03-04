import logging
import traceback
import sys
import subprocess
import os
import configparser
from functools import wraps


MAX_CHARS_NUM = 300
TOKEN = ""
USER_ID = 0
CONFIG_FILE_NAME = "config"
SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.path.join(SCRIPT_PATH, "bot_data")
RESULTS_PATH = os.path.join(DATA_PATH, "outputs")
MODELS_PATH = os.path.join(DATA_PATH, "models")
VOICES_PATH = os.path.join(DATA_PATH, "user_voices")

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("Voice Bot")
logger.setLevel(logging.DEBUG)


def validate_text(text: str) -> bool:
    return text


def convert_to_voice(filename: str) -> str:
    result_file = filename.replace('wav', 'ogg')
    convert_to_voice_cmd = f"ffmpeg -i {filename} -c:a libopus {result_file}"
    try:
        subprocess.run(f"{convert_to_voice_cmd}", shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except BaseException:
        traceback.print_exc(file=sys.stdout)
        os.remove(result_file)
        result_file = None

    return result_file


def is_user_specified() -> bool:
    return USER_ID != 0


def load_config(filepath: str) -> None:
    config = configparser.ConfigParser()
    config_section_name = "Main"
    with open(filepath, 'r') as config_file:
        config.read_file(config_file)
        global TOKEN, USER_ID
        TOKEN = config[config_section_name]["TOKEN"]
        USER_ID = config.getint(config_section_name, "USER_ID", fallback=0)


def clear_results_dir(dir_name: str) -> None:
    for filename in os.listdir(dir_name):
        file_path = os.path.join(dir_name, filename)
        if os.path.isfile(file_path) or os.path.islink(file_path):
            os.unlink(file_path)


def user_restricted(func):
    """Restrict usage of func to allowed users only and replies if necessary"""
    @wraps(func)
    async def inner(update, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id != USER_ID and is_user_specified():
            logger.debug(f"Unauthorized call of {func.__name__} by user: {update.effective_user.full_name}, with id: {user_id}")
            if update.effective_message:
                await update.effective_message.reply_html(f"Sorry, {update.effective_user.mention_html()}, it's a private bot, access denied")
            return  # quit function
        return await func(update, *args, **kwargs)
    return inner
