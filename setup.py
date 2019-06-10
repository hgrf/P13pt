import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

install_requires = ['scikit-rf', 'lmfit', 'matplotlib', 'numpy']

setuptools.setup(
    name="P13pt",
    version="0.0.2",
    author="Holger Graef",
    author_email="holger.graef@gmail.com",
    description="Instrument drivers, plotting and fitting tools for high frequency electronics",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/green-mercury/P13pt",
    packages=setuptools.find_packages(),
    package_data={
        '': ['icons/*.png',
             'spectrumfitter/*.png',
             'spectrumfitter/*.ico',
             'mascril/*.png',
             'mascril/*.ico',
             'graphulator/*.png',
             'graphulator/*.ico',
             'mdb/*.png',
             'mdb/*.ico',
             'spectrumfitter/models/*.py',
             'mascril/modules/*.py']
    },
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 2.7"
        "Programming Language :: Python :: 3.6"
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=install_requires,
    entry_points={'gui_scripts': ['p13pt = P13pt.launcher:main',
                                  'spectrumfitter = P13pt.spectrumfitter.spectrumfitter:main',
                                  'mascril = P13pt.mascril.mascril:main',
                                  'graphulator = P13pt.graphulator.graphulator:main',
                                  'mdb = P13pt.mdb.mdb:main',
                                  'sscalign = P13pt.sscalign.sscalign:main',
                                  'p13pt-makelinks = P13pt.make_links:main'
                                  ]}
)
