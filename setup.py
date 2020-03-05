import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="drain-persistent"
    version="0.1",
    author="Moshik Hershcovitch",
    author_email="moshikh@il.ibm.com",
    description="persistent log parser",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.ibm.com/MOSHIKH/drain-persistent",
    packages=setuptools.find_packages(),
    py_modules=['drain-persistent'],
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries",
    ],
)
