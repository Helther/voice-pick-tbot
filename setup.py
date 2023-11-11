from setuptools import setup, find_packages
from voice_bot.__main__ import programVersion
with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="voice-pick-tbot",
    version=programVersion,
    author="Kael",
    author_email="kaeldevop@gmail.com",
    description="",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Helther/voice-pick-tbot.git",
    packages=find_packages(),
    scripts=[
        "voice_bot/__main__.py"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "LICENSE :: OSI APPROVED :: APACHE SOFTWARE LICENSE",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.10',
)