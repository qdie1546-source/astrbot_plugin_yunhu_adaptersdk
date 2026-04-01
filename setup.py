from setuptools import setup, find_packages

setup(
    name="astrbot_plugin_yunhu_adaptersdk",
    version="2.0.6",
    author="星落云",
    author_email="your-email@example.com",
    description="云湖IM Python SDK for AstrBot",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/qdie1546-source/astrbot_plugin_yunhu_adaptersdk",
    packages=find_packages(),
    install_requires=[
        "aiohttp>=3.8.0",
        "pydantic>=2.0.0",
        "websockets>=12.0",
        "python-dotenv>=1.0.0",
    ],
    classifiers=[
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
)