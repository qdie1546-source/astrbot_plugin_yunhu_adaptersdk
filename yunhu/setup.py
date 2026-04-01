from setuptools import setup, find_packages

setup(
    name="astrbot_plugin_yunhu_adaptersdk",
    version="v2.0.5",
    author="星落云",
    description="云湖IM Python SDK",
    packages=find_packages(),
    install_requires=["aiohttp>=3.8.0", "pydantic>=2.0.0"],
    python_requires=">=3.9",
)