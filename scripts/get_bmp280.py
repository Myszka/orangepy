#!/usr/bin/python
import os
import smbus
import time
import sys
import socket
import sd_notify
from datetime import datetime,timedelta
from bmp280 import BMP280

datadir='/var/data/bmp280'
filenm='bmp280'
hostname = socket.gethostname()
IDstacji = 30100+int(hostname[-2:])

notify = sd_notify.Notifier()

if notify.enabled():
	notify.status("Initialising BMP280 ...")

if not os.path.exists(datadir):
    os.makedirs(datadir)

DEVICE = 0x76 # Default device I2C address
bus = smbus.SMBus(0)
bmp280 = BMP280(i2c_dev=bus)
presentTime=datetime.utcnow()

def date2matlab(dt):
   ord = dt.toordinal()
   mdn = dt + timedelta(days = 366)
   frac = (dt-datetime(dt.year,dt.month,dt.day,0,0,0)).seconds / (24.0 * 60.0 * 60.0)
   return mdn.toordinal() + frac

def filetowrite():
    directory=datadir+'/' + datetime.utcnow().strftime("%Y%m")
    if not os.path.exists(directory):
     os.makedirs(directory)
    name="/"+filenm+'_'+datetime.utcnow().isoformat()[:10]+".csv"
    fname=directory + name
    if os.path.isfile(fname)==False:
        f = open(fname,'w')
        f.write("'STATIONID','YEAR','MONTH','DAY','HOUR','MINUTE','SECOND','TIME','Pressure','Temperature'\n")
        f.close()
    return fname

inittime=datetime.now().second
errcnt = 0

if notify.enabled():
	notify.ready()
	notify.status("Starting measurements ...")


while True:
	if inittime!=datetime.now().second:
		inittime=datetime.now().second
		try:
			temperature = bmp280.get_temperature()
			pressure =  bmp280.get_pressure()
			fname=filetowrite()
			with open(fname, 'a') as f:
				f.write(str(IDstacji)+','+str(datetime.utcnow().year)+','+str(datetime.utcnow().month)+','+str(datetime.utcnow().day)+','+str(datetime.utcnow().hour)+','+str(datetime.utcnow().minute)+','+str(datetime.utcnow().second)+','+str(date2matlab(datetime.now()))+','+str(pressure)+','+str(temperature)+'\n')
				print(pressure)
				f.closed
			time.sleep(0.8)
			errcnt = 0
			if notify.enabled():
				notify.notify()

		except:
			print("ERROR")
			errcnt+=1
			if errcnt > 10:
				sys.exit(66)
