from faster_whisper import WhisperModel, download_model
from voice_bot.modules.bot_utils import logger, MODELS_PATH
import os

# use base size multilang model for ideal performance/quality
WHISPER_MODEL_NAME = "base"
WHISPER_MODEL_PATH = os.path.join(MODELS_PATH, f"faster-whisper-{WHISPER_MODEL_NAME}")
WHISPER_SAMPLE_RATE = 16000

# pre-initialize hisper model at startup
if not os.path.isdir(WHISPER_MODEL_PATH):
    path = download_model(WHISPER_MODEL_NAME, output_dir=WHISPER_MODEL_PATH)
    print(path)

model = WhisperModel(WHISPER_MODEL_PATH, device="cpu", compute_type="int8")


def transcribe_voice(voice_file: str) -> str:
    segments, info = model.transcribe(voice_file)
    logger.debug(f"Detected language {info.language} with probability {info.language_probability}")
    return ''.join([seg.text for seg in segments])
