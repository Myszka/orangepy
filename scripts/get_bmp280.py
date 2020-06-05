#!/usr/bin/python
import os
import smbus
import time
import sys
import socket
import sd_notify
from datetime import datetime,timedelta
from bmp280 import BMP280
import logging
import threading
from orangepisensors import filetowrite, savetofile, date2matlab, server, sendtosrv
import uuid

datadir='/var/data/bmp280'
filenm='bmp280'
srv = server('http://mqtt.lio.edu.pl',8291,'pkin')

format = "[%(asctime)s] %(message)s"
logging.basicConfig(format=format, level=logging.INFO ,datefmt="%Y-%m-%d %H:%M:%S")
logging.root.setLevel(logging.WARNING)
logging.warning("Starting BMP280")

notify = sd_notify.Notifier()
if notify.enabled():
	notify.status("Initialising BMP280 ...")

def measurebmp280(baro,timeavg=60,timeint=1):
	measurements = []
	t0 = datetime.now()
	tend = t0+timedelta(seconds=timeavg)

	while datetime.now() < tend:
		measurements.append([datetime.now(),[round(baro.get_pressure(),2), round(baro.get_temperature(),2)]])
		logging.info("Pressure: %f, Temperature: %f" % (measurements[-1][1][0],measurements[-1][1][1]))

		if notify.enabled():
			notify.notify()

		time.sleep(timeint)
	logging.warning("Pressure: %f, Temperature: %f" % (measurements[-1][1][0],measurements[-1][1][1]))
	return measurements

try:
	DEVICE = 0x76 # Default device I2C address
	bus = smbus.SMBus(0)
	bmp280 = BMP280(i2c_dev=bus)

except Exception as e:
	logging.critical("BMP280 initialization failed: %s" % e)
	sys.exit(55)



logging.warning("Main loop of BMP280 ready, synchronizing to full minutes.")
t = datetime.now()
time.sleep(59-t.second+(1e6-t.microsecond)/1e6)

if notify.enabled():
	notify.ready()
	notify.status("Measuring ...")

errcnt = 0

while True:
	try:
		measurements = measurebmp280(bmp280)
		t1 = threading.Thread(target=savetofile, args=(datadir,filenm,uuid.getnode(),['Pressure','Temperature'],measurements))
		t2 = threading.Thread(target=sendtosrv, args=(srv,uuid.getnode(),filenm,['Pressure','Temperature'],measurements))
		t1.start()
		t2.start()
		errcnt = 0
	except Exception as e:
		logging.critical("Pressure data read error: {}".format(e))
		errcnt += 1
		time.sleep(1)
		if errcnt > 10:
			logging.critical("BMP280 failed")
			sys.exit(66)
