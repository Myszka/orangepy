#!/usr/bin/python
import smbus
import time
import struct
import array
import time
import io, fcntl
import datetime, time
import os
import sys
import socket
import sd_notify
from datetime import datetime,timedelta
import logging
import threading
from orangepisensors import filetowrite, savetofile, date2matlab, server
import uuid
import sqlite3
import requests

datadir='/var/data/htu21'
filenm='htu21'
srv = server('http://mqtt.lio.edu.pl',8000,'pkin')

format = "[%(asctime)s] %(message)s"
logging.basicConfig(format=format, level=logging.INFO ,datefmt="%Y-%m-%d %H:%M:%S")
#logging.root.setLevel(logging.WARNING)

logging.warning("Starting HTU21")

notify = sd_notify.Notifier()
if notify.enabled():
	notify.status("Initialising HTU21 ...")

class i2c(object):
   def __init__(self, device, bus):
      I2C_SLAVE=0x0703
      self.fr = io.open("/dev/i2c-"+str(bus), "rb", buffering=0)
      self.fw = io.open("/dev/i2c-"+str(bus), "wb", buffering=0)
      # set device address
      fcntl.ioctl(self.fr, I2C_SLAVE, device)
      fcntl.ioctl(self.fw, I2C_SLAVE, device)
   def write(self, bytes):
      self.fw.write(bytes)
   def read(self, bytes):
      return self.fr.read(bytes)
   def close(self):
      self.fw.close()
      self.fr.close()

class HTU21D(object):
    def __init__(self):
        HTU21D_ADDR = 0x40
        CMD_READ_TEMP_HOLD = b"\xE3"
        CMD_READ_HUM_HOLD = b"\xE5"
        CMD_WRITE_USER_REG = b"\xE6"
        CMD_READ_USER_REG = b"\xE7"
        CMD_SOFT_RESET = b"\xFE"
        self.dev = i2c(HTU21D_ADDR, 1)  # HTU21D 0x40, bus 1
        self.dev.write(CMD_SOFT_RESET)  # Soft reset
        time.sleep(.1)

    def ctemp(self, sensor_temp):
        t_sensor_temp = sensor_temp / 65536.0
        return -46.85 + (175.72 * t_sensor_temp)

    def chumid(self, sensor_humid):
        t_sensor_humid = sensor_humid / 65536.0
        return -6.0 + (125.0 * t_sensor_humid)

    def temp_coefficient(self, rh_actual, temp_actual, coefficient=-0.15):
        return rh_actual + (25 - temp_actual) * coefficient

    def crc8check(self, value):
        # Ported from Sparkfun Arduino HTU21D Library:
        # https://github.com/sparkfun/HTU21D_Breakout
        remainder = ((value[0] << 8) + value[1]) << 8
        remainder |= value[2]

        # POLYNOMIAL = 0x0131 = x^8 + x^5 + x^4 + 1 divisor =
        # 0x988000 is the 0x0131 polynomial shifted to farthest
        # left of three bytes
        divisor = 0x988000

        for i in range(0, 16):
            if(remainder & 1 << (23 - i)):
                remainder ^= divisor
            divisor = divisor >> 1

        if remainder == 0:
            return True
        else:
            return False

    def read_temperature(self):
        CMD_READ_TEMP_NOHOLD = b"\xF3"
        self.dev.write(CMD_READ_TEMP_NOHOLD)  # Measure temp
        time.sleep(.1)
        data = self.dev.read(3)
        buf = array.array('B', data)
        if self.crc8check(buf):
            temp = (buf[0] << 8 | buf[1]) & 0xFFFC
            return self.ctemp(temp)
        else:
            return -255

    def read_humidity(self):
        CMD_READ_HUM_NOHOLD = b"\xF5"
        temp_actual = self.read_temperature()  # For temperature coefficient compensation
        self.dev.write(CMD_READ_HUM_NOHOLD)  # Measure humidity
        time.sleep(.1)
        data = self.dev.read(3)
        buf = array.array('B', data)

        if self.crc8check(buf):
            humid = (buf[0] << 8 | buf[1]) & 0xFFFC
            rh_actual = self.chumid(humid)

            rh_final = self.temp_coefficient(rh_actual, temp_actual)

            rh_final = 100.0 if rh_final > 100 else rh_final  # Clamp > 100
            rh_final = 0.0 if rh_final < 0 else rh_final  # Clamp < 0

            return rh_final
        else:
            return -255

def measurehtu21(termometr,timeavg=60,timeint=1):
	measurements = []
	t0 = datetime.now()
	tend = t0+timedelta(seconds=timeavg)

	while datetime.now() < tend:
		measurements.append([datetime.now(),[round(termometr.read_temperature(),2), round(termometr.read_humidity(),2)]])
		logging.info("Temperature: %f, Humidity: %f" % (measurements[-1][1][0],measurements[-1][1][1]))

		if notify.enabled():
			notify.notify()

		time.sleep(timeint)
	logging.warning("Temperature: %f, Humidity: %f" % (measurements[-1][1][0],measurements[-1][1][1]))
	return measurements

def sendtodb(id,sensor,parameters,measurements):
	try:
		fname = '/home/mich/msmt.sql'
		conn = sqlite3.connect(fname)
		c = conn.cursor()
	except Exception as e:
		logging.critical('SQLite errror: %s' % e)

	if type(measurements) is not list:
		logging.warning("Measurements error, no data")
		return 2

	logging.warning("Saving to database SQLite %s" % fname)

	savevalues=[]
	for ms in measurements:
		dt = ms[0].strftime('%Y-%m-%d %H:%M:%S')
		for v in range(len(ms[1])):
			savevalues.append((id,dt,sensor,parameters[v],ms[1][v]))
	c.executemany('INSERT INTO msmt VALUES (?,?,?,?,?)', savevalues)
	conn.commit()
	conn.close()
	return fname

def sendtosrv(id,sensor,parameters,measurements,srv):
	''' Function to calcaulate mean value and send it to server. Time resolution is minutely.'''
	if type(measurements) is not list:
		logging.warning("Measurements error, no data")
		return 2
	if len(measurements) == 0 or len(parameters) != len(measurements):
		logging.warning("Measurements error, no data. Wrong number of parameters.")
		return 3

	try:
		msmtminute = measurement[int(len(ms)/2)][0].strftime('%Y-%m-%d %H:%M:00')
		lenparams = len(parameters)
		lenmsmt = len(measurements)
		values=[]
		for ms in range(lenmsmt):
			for v in range(lenparams):
				values.insert(ms*lenparams+v,measurements[ms][1][v])

	 	values = ''.join([ str((sum(values[i::lenparams])/lenp))+'|' for i in range(lenparams)])
		parameters = ''.join(s+'|' for s in parameters)
	except Exception as e:
		logging.critical('Measurements parsing error: %s' % e)


	payload = {
	'station' : id,
	'sensor' : sensor,
	'date' : msmtminute,
	'parameters' : parameters,
	'values' : values
	}

	logging.warning("Sending to server: " % str(srv))
	try:
		r = requests.get(str(srv),params=payload)
	except Exception as e:
		logging.critical('Sending error: %s' % e)


	return r.status_code
#payload = {'station': 1500100901, 'date':1591286561.7474, 'sensor':'pms7003', 'parameters':'pm1|pm25|pm100|', 'values':'10|22|33|'}


try:
	term = HTU21D()
except Exception as e:
	logging.critical("HTU21 initialization failed: %s" % e)
	sys.exit(55)

if notify.enabled():
	notify.ready()
	notify.status("Measuring ...")

logging.warning("Main loop of HTU21 ready")
errcnt = 0

while True:
	try:
		measurements = measurehtu21(term,60,1)
		t1 = threading.Thread(target=savetofile, args=(datadir,filenm,uuid.getnode(),['Temperature','Humidity'],measurements))
		t2 = threading.Thread(target=sendtosrv, args=(uuid.getnode(),filenm,['Temperature','Humidity'],measurements,srv))
		t1.start()
		t2.start()
		errcnt = 0
	except Exception as e:
		logging.critical("Temperature data read error: {}".format(e))
		errcnt += 1
		time.sleep(1)
		if errcnt > 10:
			logging.critical("HTU21 failed")
			sys.exit(66)
