"""stac_fastapi: eodag module."""

from setuptools import setup, find_packages

with open("README.md") as f:
    desc = f.read()

install_requires = [
    "pydantic[dotenv]<2",
    "stac_pydantic==2.0.*",
    "stac-fastapi.types~=2.4.8",
    "stac-fastapi.api~=2.4.8",
    "stac-fastapi.extensions~=2.4.8",
    "eodag>=2.3.1,<3.0.0",
]

extra_reqs = {
    "server": ["uvicorn[standard]==0.23.2"],
}

setup(
    name="stac_fastapi.eodag",
    version="0.1.0",
    description="A stac-fastapi backend using eodag",
    long_description=desc,
    long_description_content_type="text/markdown",
    python_requires=">=3.11",
    classifiers=[
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: Apache Software License",
    ],
    author="Aubin Lambaré",
    author_email="aubin.lambare@csgroup.eu",
    url="https://github.com/yourusername/stac_fastapi.eodag",
    packages=find_packages(),
    install_requires=install_requires,
    extras_require=extra_reqs,
    entry_points={
        "console_scripts": ["stac-fastapi-eodag=stac_fastapi.eodag.app:run"]
    },
)
