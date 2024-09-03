from setuptools import setup, find_packages
import sys

sys.path.append("./app")

setup(
    name="picar_x_racer",
    description="Library for Picar-x",
    url="https://github.com/KarimAziev/picar-x-racer",
    version="1.0",
    packages=find_packages(),
    author="Karim Aziiev",
    author_email="karim.aziiev@gmail.com",
    license="GNU",
    keywords="python raspberry pi GPIO picar-x sunfounder",
)
