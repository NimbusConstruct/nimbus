from setuptools import setup, find_packages

setup(
    name="nimbus",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[],
    entry_points={
        "console_scripts": [
            "nimbus=nimbus.cli:main",
        ],
    },
    zip_safe=False,
)