import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()
NEWS = open(os.path.join(here, 'NEWS.txt')).read()

version = '0.1'

install_requires = [
    'invoke==0.15.0',
    'gitpython==2.1.3',
    'pygithub==1.34'
]

setup(
    name='invoke-github-flow',
    version=version,
    description="Invoke collections for automatic github flow",
    long_description=README + '\n\n' + NEWS,
    classifiers=[
    ],
    keywords='invoke github automation',
    author='Sergey Cheparev',
    author_email='sergey.cheparev@moberries.com',
    url='https://github.com/scheparev-moberries/invoke-github-flow',
    license='MIT License',
    packages=find_packages('src'),
    package_dir={'': 'src'}, include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
)
