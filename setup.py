from setuptools import setup, find_packages

setup(
    name='lean_client',
    version='0.0.1',
    url='https://github.com/PatrickMassot/lean-client-python',
    author='Patrick Massot',
    author_email='patrickmassot@free.fr',
    description='Python talking to the Lean prover',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=[])
