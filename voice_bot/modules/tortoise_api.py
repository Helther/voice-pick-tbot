import tortoise.api
from tortoise.utils import audio
import torchaudio
from torch.cuda import empty_cache
from torch import cat
from typing import List, Tuple
from tortoise.utils.text import split_and_recombine_text
from modules.bot_utils import MODELS_PATH, config, get_emot_string


# init tts models
tts = tortoise.api.TextToSpeech(models_dir=MODELS_PATH, high_vram=config.high_vram, autoregressive_batch_size=config.batch_size, device=config.device)


def run_tts_on_text(filename: str, text: str, voice: str, user_voices_dir: str, candidates: int) -> List[Tuple]:
    """save result into file with filename, returns audio data and filename pairs"""
    result = []
    voice_samples, conditioning_latents = audio.load_voice(voice, [user_voices_dir])  # TODO load from user voice dir
    pcm_audio = tts.tts_with_preset(text, voice_samples=voice_samples, conditioning_latents=conditioning_latents, preset="ultra_fast", k=candidates)
    pcm_audio = pcm_audio if candidates > 1 else [pcm_audio]
    for candidate_ind, sample in enumerate(pcm_audio):
        sample_file = f"{filename}_{candidate_ind}.wav"
        sample = sample.squeeze(0).cpu()
        torchaudio.save(sample_file, sample, 24000)
        result.append(sample)

    return result


def tts_audio_from_text(filename_result: str, text: str, voice: str, user_voices_dir: str, emotion: str, candidates: int) -> None:
    clipname_result = filename_result.replace(".wav", "")
    clips = split_and_recombine_text(text)
    audio_clips = []
    try:
        for clip_ind, clip in enumerate(clips):
            clip_name = f"{clipname_result}_{clip_ind}"
            if emotion:
                clip = "".join([get_emot_string(emotion), clip])
            samples_data = run_tts_on_text(clip_name, clip, voice, user_voices_dir, candidates)
            audio_clips.append(samples_data)

        for cand_ind in range(candidates):
            cand_clips = []
            for clip_ind in range(len(clips)):
                cand_clips.append(audio_clips[clip_ind][cand_ind])

            audio_combined = cat(cand_clips, dim=-1)
            torchaudio.save(f"{clipname_result}_{cand_ind}.wav", audio_combined, 24000)

    finally:
        if not config.keep_cache:
            empty_cache()
