from setuptools import setup

setup(
    name="crypto-bot",
    version="0.1",
    install_requires=[
        'ccxt==4.2.85',
        'pandas==1.5.3',
        'numpy==1.23.5',
        'ta==0.11.0',  # استخدام ta لجميع الأنظمة
        'requests==2.31.0',
        'APScheduler==3.10.1',
        'python-telegram-bot==20.6',
        'python-dotenv==1.0.0'
    ],
    setup_requires=['setuptools>=68.0.0']
)
