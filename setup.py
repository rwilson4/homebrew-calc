from setuptools import setup

setup(name='homebrew_calc',
      version='0.1',
      description='Homebrew Calculators',
      long_description=open('README.md').read(),
      keywords=['homebrew', 'beer'],
      url='https://github.com/rwilson4/homebrew-calc',
      author='Bob Wilson',
      author_email='bob@convexanalytics.com',
      licence='Apache 2.0',
      packages=['homebrew_calc'],
      classifiers=[
          "Development Status :: 3 - Alpha",
          "Environment :: Console",
          "Topic :: Utilities",
          "License :: OSI Approved :: Apache Software License"
      ],
      install_requires=[
          "unit_parser",
          "numpy",
          "scipy",
          "cvxpy"
      ],
      include_package_data=True,
      package_data={
          'homebrew_calc': ['resources/*']
      },
      entry_points={
          'console_scripts': [
              'malt_composition=homebrew_calc.malt_composition:main',
              'water_composition=homebrew_calc.water_composition:main',
              'hop_composition=homebrew_calc.hop_composition:main',
              'yeast_composition=homebrew_calc.yeast_composition:main',
              'abvcalc=homebrew_calc.yeast_composition:abvcalc_main',
              'convert_ph_temp=homebrew_calc.water_composition:convert_pH_temp_main'
          ]
      },
      zip_safe=False)
