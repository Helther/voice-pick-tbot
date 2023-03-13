from enum import Enum
from modules.bot_db import db_handle


class Emotions(Enum):
    Neutral = 0
    Sad = 1
    Angry = 2
    Happy = 3
    Scared = 4


EMOTION_STRINGS = {
    Emotions.Neutral.name: Emotions.Neutral,
    Emotions.Sad.name: Emotions.Sad,
    Emotions.Angry.name: Emotions.Angry,
    Emotions.Happy.name: Emotions.Happy,
    Emotions.Scared.name: Emotions.Scared,
}

EMOTION_VALUES = {
    Emotions.Neutral.value: Emotions.Neutral,
    Emotions.Sad.value: Emotions.Sad,
    Emotions.Angry.value: Emotions.Angry,
    Emotions.Happy.value: Emotions.Happy,
    Emotions.Scared.value: Emotions.Scared
}


class UserSettings(object):
    def __init__(self, voice: str, emot: str, samples: int) -> None:
        self.voice = voice
        self.emotion = emot
        self.samples_num = samples


def get_emotion_name(user_id: int) -> str:
    return EMOTION_VALUES[db_handle.get_user_emotion_setting(user_id)].name


def get_user_settings(user_id: int) -> UserSettings:
    voice = db_handle.get_user_voice_setting(user_id)
    emot = get_emotion_name(user_id)
    samples_num = db_handle.get_user_samples_setting(user_id)
    if emot == Emotions.Neutral.name:  # if Neutral then don't prepend emotion string
        emot = None
    return UserSettings(voice, emot, samples_num)
