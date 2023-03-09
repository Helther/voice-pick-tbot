# Voice Synthesis Telegram Bot
This bot provides the ability to synthesize voice samples using tts-tortoise API.
### Prerequisites
 * NVIDIA GPU
 * python 3.10.6
 * pip or anaconda env with python 3.10.6
 * ffmpeg
 
Tested on Linux only, writtem with cross-platform in mind, should work on Windows
### install
```
git clone https://github.com/152334H/tortoise-tts-fast.git
python -m pip install -r ./requirements.txt
python -m pip install -e ./tortoise-tts-fast
```

### Usage
Create configuration file named "config" inside bota_data directory
and set user parameters. Use this [example](bot_data/config_example) as reference.

Run tts_tbot.py script from the required environment

### Notes on text promts (how to get desired results)
Use punctuation (ellipses, exclamation points, CAPS, semicolons, commas) to add emphasis and shape the speech.
You can also try to add different emotions to sentences by prepending parts of texts with "[describe emotion]" 
notations (For more info please visit [the original model source page](https://github.com/neonbjb/tortoise-tts)).

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
