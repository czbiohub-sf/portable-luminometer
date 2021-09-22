import setuptools

setuptools.setup(
    name="luminometer",
    version="1.0.0",
    author="Paul Lebel",
    author_email="plebel@alumni.stanford.edu",
    description="Software to control a low-cost, high-sensitivity luminometer.",
    url="https://github.com/czbiohub/ulc-tube-reader",
    install_requires=[
        'Pillow',
        'inky',
        'numpy',
        'pigpio',
        'RPi.GPIO'
    ],
    classifiers=[
        "CZ Biohub :: Bioengineering",
    ],
)
