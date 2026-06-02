#!/usr/bin/env python3
# setup.py for Dragon Email Agent
from setuptools import setup, find_packages

setup(
    name="dragon-email-agent",
    version="1.0.0",
    description="Project Dragon - Ultimate Email AI Agent",
    author="Project Dragon Team",
    python_requires=">=3.10",
    packages=find_packages(),
    install_requires=[
        "loguru>=0.7.0",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "sqlalchemy>=2.0.0",
        "fastapi>=0.100.0",
        "uvicorn>=0.23.0",
        "python-dateutil>=2.8.0",
        "beautifulsoup4>=4.12.0",
        "apscheduler>=3.10.0",
    ],
    extras_require={
        "voice": ["SpeechRecognition>=3.10.0", "pyttsx3>=2.90"],
        "chromadb": ["chromadb>=0.4.0"],
        "security": ["cryptography>=41.0.0"],
    },
)