from setuptools import setup, find_packages

setup(
    name="navaid-sim",
    version="3.0.0",
    packages=find_packages(),
    package_data={
        "navaid_sim": ["data/*"],
    },
    include_package_data=True,
    install_requires=[
        "fastapi>=0.100.0",
        "uvicorn>=0.20.0",
        "websockets>=11.0",
        "pydantic>=2.0",
    ],
    entry_points={
        "console_scripts": [
            "navaid-sim=navaid_sim.cli:main",
        ],
    },
)

