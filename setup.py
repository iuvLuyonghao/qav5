import re
try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup
with open("qav5/__init__.py", 'r') as f:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        f.read(), re.MULTILINE).group(1)
setup(
    name="qav5",
    version=version,
    url="http://git.rccchina.com/qa/qav5",
    license="MIT",
    author="QA Team",
    author_email="tim.qu@rccchina.com",
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Software Development :: Libraries :: Python Modules"
    ],
    install_requires=[
        "simplejson>=3.16.0",
        "python-json-logger>=0.1.9",
        "requests>=2.18.4",
        "paramiko>=2.4.1",
        "pymongo>=3.6.1",
        "pymysql>=0.9.1",
        "redis>=2.10.6",
        "pycryptodomex>=3.6.3",
        "sqlparse==0.3.0",
        "cx-Oracle>=7.2.3"
    ],
    description="API Test Framework Toolkit",
    long_description=open("README.md", 'r', encoding='utf-8').read(),
)
