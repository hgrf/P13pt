import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="P13pt",
    version="0.0.2",
    author="Holger Graef",
    author_email="holger.graef@gmail.com",
    description="Instrument drivers, plotting and fitting tools for high frequency electronics",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/green-mercury/P13pt",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 2",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
