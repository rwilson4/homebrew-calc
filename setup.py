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
      include_package_data=True,
      package_data={
          'homebrew_calc': ['resources/*']
      },
      entry_points={
          'console_scripts': [
              'abvcalc=homebrew_calc.abvcalc:execute',
              'convert_pH_temp=homebrew_calc.convert_pH_temp:execute',
          ]
      },
      zip_safe=False)
