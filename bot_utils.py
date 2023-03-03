import logging
import traceback
import sys
import subprocess
from os import remove as rem_file
import configparser


MAX_CHARS_NUM = 280
TOKEN = ""
USER_ID = 0

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("Voice Bot")
logger.setLevel(logging.DEBUG)


def validate_text(text: str) -> bool:
    if not text:
        return False
    if len(text) > MAX_CHARS_NUM:
        return False

    return True


def convert_to_voice(filename: str) -> str:
    result_file = filename.replace('wav', 'ogg')
    try:
        convert_to_voice_cmd = f"ffmpeg -i {filename} -c:a libopus {result_file}"
        subprocess.run(f"{convert_to_voice_cmd}", shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except BaseException:
        traceback.print_exc(file=sys.stdout)
        rem_file(result_file)
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
