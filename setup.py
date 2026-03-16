import os
from setuptools import setup, find_packages

setup(
    name="sentinel",
    version="0.1.0",
    description="The modular robot control framework — the n8n of robotics.",
    long_description=open(os.path.join(os.path.dirname(__file__), "README.md"), encoding="utf-8").read() if os.path.exists(os.path.join(os.path.dirname(__file__), "README.md")) else "",
    long_description_content_type="text/markdown",
    author="Sentinel Contributors",
    packages=find_packages(),
    install_requires=[],  # Pure Python, no mandatory dependencies
    extras_require={
        "hardware": [
            "adafruit-circuitpython-pca9685",
            "RPi.GPIO"
        ]
    },
    entry_points={
        'console_scripts': [
            'sentinel=sentinel.cli:main',
        ],
    },
    python_requires=">=3.8",
)
