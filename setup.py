# setup.py

from setuptools import setup

with open("README", 'r') as f:
    long_description = f.read()

setup(
   name='pgdbpy',
   version='1.0.8',
   description='A simple PostgreSQL database connection manager that exploits the power of cfgpy',
   license="Mozilla Public License 2.0 (MPL 2.0)",
   long_description='A simple PostgreSQL database connection manager that exploits the power of cfgpy.',
   author='Phenicle',
   author_email='pheniclebeefheart@gmail.com',
   url="https://github.com/phenicle/pgdbpy",
   packages=['pgdbpy',],  #same as name
   install_requires=['cfgpy', 'psycopg2'], #external packages as dependencies
)
