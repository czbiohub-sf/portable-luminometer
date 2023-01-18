import setuptools

setuptools.setup(
    name="luminometer",
    version="1.0.0",
    python_requires='>=3.7',
    author="Paul Lebel",
    author_email="plebel@alumni.stanford.edu",
    description="Software to control a low-cost, high-sensitivity luminometer.",
    url="https://github.com/czbiohub/ulc-tube-reader",
    install_requires=[
        'Pillow>=8.3.1',
        'inky>=1.2.2',
        'numpy>=1.21.1',
        'pigpio>=1.78'
    ],
    classifiers=[
        "CZ Biohub :: Bioengineering",
    ],
)
