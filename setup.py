"""
Arynoxtech_AGI - Multi-Domain Adaptive Artificial General Intelligence
A pip-installable Python library for AGI capabilities
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

# Read requirements
with open("requirements.txt", "r") as f:
    requirements = [
        line.strip()
        for line in f
        if line.strip() and not line.startswith("#") and not line.startswith("-")
    ]

setup(
    name="Arynoxtech_AGI",
    version="2.0.1",
    author="Aryan Chavan",
    author_email="aryaanchavan1@gmail.com",
    description="Multi-Domain Adaptive Artificial General Intelligence - Works across 8+ industries. Better than LangChain with native AGI capabilities.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aryaanchavan1-commits/Arynoxtech_AGI",
    project_urls={
        "Bug Tracker": "https://github.com/aryaanchavan1-commits/Arynoxtech_AGI/issues",
        "Documentation": "https://github.com/aryaanchavan1-commits/Arynoxtech_AGI#readme",
        "Source Code": "https://github.com/aryaanchavan1-commits/Arynoxtech_AGI",
    },
    packages=find_packages(include=["arynoxtech_agi", "arynoxtech_agi.*", "core", "core.*"]),
    package_data={
        "": [
            "data/domains/**/*.json",
            "config/*.json",
            "*.json",
        ],
    },
    include_package_data=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: Healthcare Industry",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        "voice": [
            "pyttsx3>=2.90",
            "SpeechRecognition>=3.10",
            "pyaudio>=0.2.13",
        ],
        "api": [
            "fastapi>=0.100.0",
            "uvicorn>=0.23.0",
            "pydantic>=2.0.0",
        ],
        "web": [
            "selenium>=4.15.0",
            "newspaper3k>=0.2.8",
        ],
        "all": [
            "pyttsx3>=2.90",
            "SpeechRecognition>=3.10",
            "pyaudio>=0.2.13",
            "fastapi>=0.100.0",
            "uvicorn>=0.23.0",
            "pydantic>=2.0.0",
            "selenium>=4.15.0",
            "newspaper3k>=0.2.8",
        ],
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.1.0",
            "mypy>=1.5.0",
            "isort>=5.12.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "arynoxtech_agi=arynoxtech_agi.cli:main",
        ],
    },
    keywords=[
        "ai",
        "agi",
        "artificial-intelligence",
        "artificial-general-intelligence",
        "chatbot",
        "nlp",
        "natural-language-processing",
        "machine-learning",
        "deep-learning",
        "rag",
        "retrieval-augmented-generation",
        "customer-support",
        "healthcare",
        "education",
        "coding-assistant",
    ],
)