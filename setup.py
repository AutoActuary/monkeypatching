import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="monkeypatching",
    author="Auto Actuary",
    description="A Python package designed for temporary recursive monkeypatching.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/autoactuary/monkeypatching",
    packages=setuptools.find_packages(exclude=["test"]),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    use_scm_version={
        "write_to": "monkeypatching/version.py",
    },
    setup_requires=[
        "setuptools_scm",
    ],
    install_requires=[],
    package_data={
        "": [
            "py.typed",
        ],
    },
)
