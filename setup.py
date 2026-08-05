from setuptools import setup, find_packages

setup(
       # the name must match the folder name 'epygraf'
        name="epygraf", 
        version='0.0.1',
        author="Jakob Jünger and Chantal Gärtner",
        author_email="jakob.juenger@uni-muenster.de",
        description = 'Epygraf - Analyze Epigraf data with Python',
        long_description = 'The Epygraf package aims to make data work with Epigraf easier. It provides functions for data transfer using the Epigraf APIs: preparing data imports, e.g. from social media datasets, and preparing data analyses with Python.',
        packages=find_packages(),
        install_requires=['sqlalchemy>=2.0.0','pymysql>=1.1.0','pandas>=2.0.0','requests>=2.0.0','tqdm>=4.0.0'],
        extras_require={
            'test': ['pytest>=7.0.0']
        },

        keywords=['python', 'epigraf'],
        classifiers= [
            "Development Status :: 2 - Pre-Alpha",
            "Intended Audience :: Science/Research",
            "Programming Language :: Python :: 3"
        ]
)