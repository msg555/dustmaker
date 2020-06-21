import setuptools

try:
    with open("README.md", "r") as fh:
        long_description = fh.read()
except FileNotFoundError:
    long_description = ""

setuptools.setup(
    name='dustmaker',
    version="0.3.1",
    author='Mark Gordon',
    author_email='msg555@gmail.com',
    description='Dustforce level scripting framework',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='http://github.com/msg555/dustmaker/',
    packages=['dustmaker'],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
    ],
    install_requires=[],
    test_suite='tests',
    python_requires='>=3.4',
)
