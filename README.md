# Voice Synthesis Telegram Bot
This bot provides the ability to synthesize voice samples using tts-tortoise API from local host. It has multilanguage support and voice-to-voice conversion via whisper model.

There should be a running instance of the bot, if you would like to check it out at https://t.me/tts_tbot

Here's the preview:
![synthesis demo](rsc/demo.gif)

## Notable features
 * all of the features of tts-tortoise, including voice cloning, emotion steering, multisampling
 * user-settings database
 * custom voice adding
 * voice-to-voice conversion via mic recording
 
### Prerequisites
 * NVIDIA GPU (between 4 and 10Gb of VRAM required for inference, depending on tortoise settings)
 * python 3.10.6
 * pip or anaconda env with python 3.10.6
 * ffmpeg
 
Tested on Linux only, written with cross-platform in mind, should work on Windows. Although tortoise-tts environment may fail to resolve.
### install
cd to repo directory and execute:
```
git clone https://github.com/152334H/tortoise-tts-fast.git
git clone https://github.com/guillaumekln/faster-whisper.git
python -m pip install -r ./requirements.txt
```

### Usage
Create configuration file named "config" inside bota_data directory
and set user parameters. Use this [example](bot_data/config_example) as reference.

Run module package voice_bot from the required environment

### Notes on text promts (how to get desired results)
Use punctuation (ellipses, exclamation points, CAPS, semicolons, commas) to add emphasis and shape the speech.
You can also try to add different emotions to sentences by prepending parts of texts with "[describe emotion]" 
notations (For more info please visit [the original model source page](https://github.com/neonbjb/tortoise-tts)).

### TODO
 * restructure external git dependencies
 * add synthensis from audio files

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
