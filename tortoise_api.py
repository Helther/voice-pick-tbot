import tortoise.api
from tortoise.utils import audio
import torchaudio
import torch.cuda
from os import path


RESULTS_DIR = "outputs"
SCRIPT_PATH = path.dirname(path.realpath(__file__))
RESULTS_PATH = path.join(SCRIPT_PATH, RESULTS_DIR)
MODELS_PATH = path.join(SCRIPT_PATH, "models")

tts = tortoise.api.TextToSpeech(models_dir=MODELS_PATH, kv_cache=True, high_vram=True)


def gen_tortoise(filename: str, text: str, voice: str):
    voice_samples, conditioning_latents = audio.load_voice(voice)
    pcm_audio = tts.tts_with_preset(text, voice_samples=voice_samples, preset="ultra_fast", k=1)
    torchaudio.save(filename, pcm_audio.squeeze(0).cpu(), 24000)
    torch.cuda.empty_cache()
