from setuptools import setup, find_packages

setup(
    name="trading-bot",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "pandas>=2.0.3",
        "numpy>=1.24.3",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "schedule>=1.2.0",
        "ta>=0.10.2",
        "python-telegram-bot>=20.7",
    ],
    python_requires=">=3.8",
)
