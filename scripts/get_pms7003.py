#!/usr/bin/python
import serial
import smbus
import time
import struct
import array
import time
import io, fcntl
import subprocess
import socket
from datetime import datetime,timedelta
import sys
import sd_notify
import os
import logging
import threading
from orangepisensors import filetowrite, savetofile, date2matlab, readbit, checkval, blink
import uuid

datadir='/var/data/test'
filenm='pms7003'

format = "[%(asctime)s] %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S")
logging.info("Starting PMS7003")

notify = sd_notify.Notifier()
if notify.enabled():
	notify.status("Initialising PMS7003 ...")

def measurepms7003(port='/dev/ttyS1',timeavg=60,timeint=1):
	try:
		ser = serial.Serial(port, 9600)
		ser.flushInput()
		ser.flushOutput()
	except Exception as e:
		logging.critical("Serial initialization error: {}".format(e))
		return 99

	measurements = []
	t0 = datetime.now()
	tend = t0+timedelta(seconds=timeavg)

	while datetime.now() < tend:
		try:
			dane=bytearray(ser.read(32))
			#concentration of PM1.0, ug/m3
			PM1=readbit(dane,4)
			#concentration of PM2.5, ug/m3
			PM25=readbit(dane,6)
			#concentration of PM10.0, ug/m3
			PM10=readbit(dane,8)
			#the number of particulate of diameter above 0.3um in 0.1 liters of air
			bin1=readbit(dane,16)
			#the number of particulate of diameter above 0.5um in 0.1 liters of air
			bin2=readbit(dane,18)
			#the number of particulate of diameter above 1.0um in 0.1 liters of air
			bin3=readbit(dane,20)
			#the number of particulate of diameter above 2.5um in 0.1 liters of air
			bin4=readbit(dane,22)
			#the number of particulate of diameter above 5.0um in 0.1 liters of air
			bin5=readbit(dane,24)
			#the number of particulate of diameter above 10.0um in 0.1 liters of air
			bin6=readbit(dane,26)
			ser.flushInput()
			ser.flushOutput()
			if checkval(dane)==readbit(dane,30):
				measurements.append([datetime.now(),[PM1,PM25,PM10,bin1,bin2,bin3,bin4,bin5,bin6]])
				logging.info("PM 0: %d, PM 2.5: %d, PM 10: %d, bin 0: %d" % (measurements[-1][1][0],measurements[-1][1][1],measurements[-1][1][2],measurements[-1][1][3]))
				blink()
				if notify.enabled():
					notify.notify()
			else:
				logging.warning("PM checksum error")

		except Exception as e:
			logging.warning("PM data read error: {}".format(e))
			return 55

		time.sleep(timeint)

	return measurements

if notify.enabled():
	notify.ready()
	notify.status("Measuring ...")

<<<<<<< HEAD
logging.info("Main loop of PMS7003 ready")
=======
			if pmy[-1]==1:
				fname=filetowrite()
				with open(fname, 'a') as f:
					f.write(str(IDstacji)+','+str(datetime.utcnow().year)+','+str(datetime.utcnow().month)+','+str(datetime.utcnow().day)+',' \
					+str(datetime.utcnow().hour)+','+str(datetime.utcnow().minute)+','+str(datetime.utcnow().second)+','+str(date2matlab(datetime.now()))+',' \
					+toascii(pmy)[:-1]+'\n')
				f.closed
				blink()
				errcnt = 0
				if notify.enabled():
					notify.notify()
>>>>>>> c7f9b1c736fc5b91bfa28e4b2c718733c455b6a9

while True:
	try:
		measurements = measurepms7003()
		t1 = threading.Thread(target=savetofile, args=(datadir,filenm,uuid.getnode(),['PM1','PM2.5','PM10','Bin0','Bin1','Bin2','Bin3','Bin4','Bin5'],measurements))
		t1.start()
		errcnt = 0
	except Exception as e:
		logging.warning("PMS7003 data read error: {}".format(e))
		errcnt += 1
		time.sleep(1)
		if errcnt > 10:
			logging.critical("PMS7003 failed")
			sys.exit(66)
