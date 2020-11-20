#!/usr/bin/python
import os
import time
import sys
import sd_notify
from datetime import datetime,timedelta
import logging
import threading
from orangepisensors import filetowrite, savetofile, date2matlab, server, sendtosrv, checkntp, i2c
import uuid
import array
import io, fcntl

datadir='/var/data/hyt939'
filenm='hyt939'
srv = server('http://mqtt.lio.edu.pl',8291,'pkin')

format = "[%(asctime)s] %(message)s"
logging.basicConfig(format=format, level=logging.INFO ,datefmt="%Y-%m-%d %H:%M:%S")

checkntp()

logging.root.setLevel(logging.WARNING)
logging.warning("Starting HYT939")

notify = sd_notify.Notifier()
if notify.enabled():
	notify.status("Initialising HYT939 ...")

def measurehyt939(timeavg=60,timeint=15):
	measurements = []
	t0 = datetime.now()
	tend = t0+timedelta(seconds=timeavg)


	try:
		NORM = b"\x80"
		dev = i2c(0x28, 1)  # HTU21D 0x40, bus 1
		dev.write(NORM)  # Soft reset
		time.sleep(0.5)
	except Exception as e:
		logging.critical("HYT939 initialization failed: %s" % e)
		sys.exit(55)

	while datetime.now() < tend:
		data = dev.read(4)
		buf = array.array('B', data)
		data = buf
		humidity = ((data[0] & 0x3F) * 256 + data[1]) * (100 / 16383.0)
		cTemp = ((data[2] * 256 + (data[3] & 0xFC)) / 4) * (165 / 16383.0) - 40
		measurements.append([datetime.now(),[round(cTemp,2), round(humidity(),2)]])
		logging.info("Temperature: %f, Humidity: %f" % (measurements[-1][1][0],measurements[-1][1][1]))

		if notify.enabled():
			notify.notify()

		time.sleep(timeint)
	logging.warning("Pressure: %f, Temperature: %f" % (measurements[-1][1][0],measurements[-1][1][1]))
	#print("Temperature in Celsius is : %.2f C" %cTemp)
	#print("Relative Humidity is : %.2f %%RH" %humidity)
	return (measurements)

logging.warning("Main loop of HYT939 ready, synchronizing to full minutes.")
t = datetime.now()
time.sleep(59-t.second+(1e6-t.microsecond)/1e6)

if notify.enabled():
	notify.ready()
	notify.status("Measuring ...")

errcnt = 0

while True:
	try:
		measurements = measurehyt939()
		t1 = threading.Thread(target=savetofile, args=(datadir,filenm,uuid.getnode(),['Temperature','Humidity'],measurements))
		t2 = threading.Thread(target=sendtosrv, args=(srv,uuid.getnode(),filenm,['Temperature','Humidity'],measurements))
		t1.start()
		t2.start()
		errcnt = 0
	except Exception as e:
		logging.critical("Temp/humidity data read error: {}".format(e))
		errcnt += 1
		time.sleep(1)
		if errcnt > 10:
			logging.critical("HYT939 failed")
			sys.exit(66)
