import tortoise.api
from tortoise.utils import audio
import torchaudio
from torch.cuda import empty_cache
from torch import cat
from os import path
from tortoise.utils.text import split_and_recombine_text
from typing import List, Tuple


RESULTS_DIR = "outputs"
SCRIPT_PATH = path.dirname(path.realpath(__file__))
RESULTS_PATH = path.join(SCRIPT_PATH, RESULTS_DIR)
MODELS_PATH = path.join(SCRIPT_PATH, "models")

# TODO add args to config file
# init tts models
tts = tortoise.api.TextToSpeech(models_dir=MODELS_PATH, kv_cache=True, high_vram=True, autoregressive_batch_size=None, device=0)


def run_tts_on_text(filename: str, text: str, voice: str, candidates: int) -> List[Tuple]:
    """save result into file with filename, returns audio data and filename pairs"""
    result = []
    voice_samples, conditioning_latents = audio.load_voice(voice)
    pcm_audio = tts.tts_with_preset(text, voice_samples=voice_samples, conditioning_latents=conditioning_latents, preset="ultra_fast", k=candidates)
    pcm_audio = pcm_audio if candidates > 1 else [pcm_audio]
    for candidate_ind, sample in enumerate(pcm_audio):
        sample_file = f"{filename}_{candidate_ind}.wav"
        sample = sample.squeeze(0).cpu()
        torchaudio.save(sample_file, sample, 24000)
        result.append((sample, sample_file))

    return result


# TODO add multiple samples support
def tts_audio_from_text(filename_result: str, text: str, voice: str) -> None:
    audio_clips = []
    clipname_result = filename_result.replace(".wav", "")
    clips = split_and_recombine_text(text)
    try:
        for clip_ind, clip in enumerate(clips):
            clip_name = f"{clipname_result}_{clip_ind}"
            samples_data = run_tts_on_text(clip_name, clip, voice, 1)
            audio_clips.append(samples_data[0][0])  # audio data of the first candidate

        audio_combined = cat(audio_clips, dim=-1)
        torchaudio.save(filename_result, audio_combined, 24000)

    finally:
        empty_cache()  # TODO add config option to keep cache
