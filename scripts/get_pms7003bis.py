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

batcmd="cat /sys/class/leds/orangepi\:green\:pwr/brightness"

datadir='/var/data/PMS7003bis'
filenm='pms7003'
hostname = socket.gethostname()
IDstacji = 30100+int(hostname[-2:])

notify = sd_notify.Notifier()

if notify.enabled():
	notify.status("Initialising PMS7003 bis ...")

if not os.path.exists(datadir):
    os.makedirs(datadir)

def initsen177(port='/dev/ttyS2'):
	'''
	Initialize serial port for SEN0177
	'''
	try:
		ser = serial.Serial(port, 9600)
		ser.flushInput()
		ser.flushOutput()
		return ser
	except Exception as e:
		print ("Serial initialization error: {}".format(e))
		return 99


def blink():
	batcmd="cat /sys/class/leds/orangepi\:green\:pwr/brightness"
	result = subprocess.check_output(batcmd, shell=True)
	if (int(result)>0):
		os.system("echo 0 > /sys/class/leds/orangepi\:green\:pwr/brightness")
	elif (int(result)==0):
		os.system("echo 1 > /sys/class/leds/orangepi\:green\:pwr/brightness")


def readbit(inp,bit):
	'''
	Read bit data from SEN0177 (16-bytes)
	'''
	return (inp[bit] << 8) + inp[bit+1]

def checkval(inp):
	'''
	Calcaulate checksum for SEN0177 data
	'''
	val=0
	for i in range(30):
		val=val + inp[i]
	return val

def readsen177(serial):
	'''
	Read data from SEN0177 by serial port and return list of all measured values
	'''
	try:
		dane=bytearray(serial.read(32))
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
		return [PM1,PM25,PM10,bin1,bin2,bin3,bin4,bin5,bin6,int(checkval(dane)==readbit(dane,30))]

	except Exception as e:
		print ("PM data read error: {}".format(e))
		return 1

def toascii(inp):
	'''
	Function to convert tables to ascii string lines
	'''
	out=''
	for i in inp:
		out=out+str(i)+','
	return out

def timestr():
	'''
	Return time string formated for the project
	'''
	return time.strftime('%Y,%m,%d,%H,%M,%S,', time.gmtime())


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
        f.write("'STATIONID','YEAR','MONTH','DAY','HOUR','MINUTE','SECOND','TIME','PM1','PM2.5','PM10','Bin0','Bin1','Bin2','Bin3','Bin4','Bin5','Checksum'\n")
        f.close()
    return fname



ser=initsen177()
inittime=datetime.now().second
errcnt = 0

if notify.enabled():
	notify.ready()
	notify.status("Starting measurements ...")

while True:
	if inittime!=datetime.now().second:
		inittime=datetime.now().second
		print(datetime.now().isoformat())
		try:
			pmy=readsen177(ser)
			print(pmy)
			time.sleep(0.7)

			if pmy[-1]==1:
				fname=filetowrite()
				with open(fname, 'a') as f:
					f.write(str(IDstacji)+','+str(datetime.utcnow().year)+','+str(datetime.utcnow().month)+','+str(datetime.utcnow().day)+',' \
					+str(datetime.utcnow().hour)+','+str(datetime.utcnow().minute)+','+str(datetime.utcnow().second)+','+str(date2matlab(datetime.now()))+',' \
					+toascii(pmy)+'\n')
				f.closed
				blink()
				if notify.enabled():
					notify.notify()

			else:
				ser.close()
				ser=initsen177()
		except Exception as e:
				ser.close()
				ser=initsen177()
				print("ERROR")
				errcnt+=1
				if errcnt > 10:
					sys.exit(66)
