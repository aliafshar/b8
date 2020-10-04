

from distutils.core import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="neohubby",
    version="0.0.1",
    author="Ali Afshar",
    author_email="aa@virc.how",
    description="Library to control the Heatmiser Neohub",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pypa/sampleproject",
    py_modules='neohubby',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
