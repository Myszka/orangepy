from distutils.core import setup
import sys
from glob import glob
import os
#from shutil import copy

sys.prefix='/usr/local/'
# User-friendly description from README.md
current_directory = os.path.dirname(os.path.abspath(__file__))
try:
    with open(os.path.join(current_directory, 'README.md'), encoding='utf-8') as f:
        long_description = f.read()
except Exception:
    long_description = ''

services = glob('services/*')
script = glob('scripts/*')
conf = glob('conf/*')

setup(
    name="orangepy",

    version='0.2.0',
    license='GPLv3',

    description='PolandAOD set of scripts for environmental measurements based on Orange Pi with armbian',
    long_description = long_description,
    long_description_context_type = 'text/markdown',
    author='MiCh',
    author_email='mich@igf.fuw.edu.pl',
    url='https://github.com/Myszka/orangepy',
    keywords=['pms7003','HTU21','bmp280','PolandAOD','sensors','measurements','environmental'],
	py_modules =['orangepisensors']
    scripts=script,
    data_files=[('share/orangepy', services),('etc', conf)],
    install_requires=['smbus','bmp280','pyserial', 'spidev', 'sd-notify'],
)

# copy unit files to /etc/ folder
#for file in glob(sys.prefix+'share/orangepy/*.service'):
#    copy(file, '/etc/systemd/system')
