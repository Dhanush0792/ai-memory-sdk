"""
Secure AI Memory SDK
Version: 1.0.0
"""

from setuptools import setup, find_packages

with open("QUICKSTART.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="secure-ai-memory",
    version="1.0.0",
    author="AI Memory Team",
    description="Enterprise-grade memory for LLM applications",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/secure-ai-memory",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "fastapi==0.109.0",
        "uvicorn==0.27.0",
        "psycopg[binary]==3.1.18",
        "pydantic==2.5.3",
        "python-dotenv==1.0.0",
        "requests==2.31.0",
        "tiktoken==0.5.2",
    ],
    extras_require={
        "demo": ["openai==1.10.0"],
        "dev": ["pytest", "black", "flake8"],
    },
)
