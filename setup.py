#!/usr/bin/env python3
"""Setup script for Scribe - KDE Speech-to-Text Utility."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="scribe-stt",
    version="0.1.0",
    description="Fast, local speech-to-text utility for KDE/Debian systems",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Scribe Project",
    author_email="",
    url="https://github.com/Lastofthefirst/scribe",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "faster-whisper>=1.0.0",
        "sounddevice>=0.4.6",
        "numpy>=1.24.0",
        "webrtcvad>=2.0.10",
        "pyperclip>=1.8.2",
        "toml>=0.10.2",
        "click>=8.1.0",
    ],
    entry_points={
        "console_scripts": [
            "scribe=scribe.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Utilities",
    ],
    keywords="speech-to-text whisper kde debian accessibility",
    include_package_data=True,
)
