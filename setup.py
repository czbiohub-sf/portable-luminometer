import setuptools

setuptools.setup(
    name="ulc_luminometer",
    version="0.0.1",
    author="Paul Lebel",
    author_email="plebel@alumni.stanford.edu",
    description="Software to control a low-cost, high-sensitivity luminometer.",
    url="https://github.com/czbiohub/ulc_luminometer",
    install_requires=[
        'Pillow',
        'RPi.GPIO == 0.7.0',
        'spidev == 3.5',
        'inky'
    ],
    classifiers=[
        "CZ Biohub :: Bioengineering",
    ],
)
