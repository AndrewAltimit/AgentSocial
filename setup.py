from setuptools import setup, find_packages

setup(
    name="bulletin_board",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "Flask==3.0.0",
        "Flask-CORS==4.0.0",
        "SQLAlchemy==2.0.23",
        "psycopg2-binary==2.9.9",
        "aiohttp==3.9.1",
        "python-dateutil==2.8.2",
    ],
)