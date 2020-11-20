from datetime import datetime, timedelta
import os
import logging
import subprocess
import sqlite3
import requests
import ntplib
import logging

class server(object):
	"""Simple server connection class."""

	def __init__(self, addr, port, subsite='', method='POST'):
		super(server, self).__init__()
		self.addr = addr
		self.port = port
		self.subsite = subsite
		self.method = method

	def __repr__(self):
		return self.addr+":"+str(self.port)+'/'+self.subsite

	def __str__(self):
		return self.addr+":"+str(self.port)+'/'+self.subsite

def blink(led=0):
	red = "red\:status"
	green = "green\:pwr"

	if led == 0:
		colour = red
	else:
		colour = green

	batcmd="cat /sys/class/leds/orangepi\:"+colour+"/brightness"
	result = subprocess.check_output(batcmd, shell=True)
	if (int(result) > 0):
		os.system("echo 0 > /sys/class/leds/orangepi\:"+colour+"/brightness")
	elif (int(result)==0):
		os.system("echo 1 > /sys/class/leds/orangepi\:"+colour+"/brightness")

def checkntp(url='localhost'):

	cnt = ntplib.NTPClient()
	offs = 999
	while offs**2>10:
		try:
			logging.info('NTP works fine')
			response = cnt.request('localhost', version=3)
			offs = response.offset
		except:
			logging.warning('NTP error restarting ...')
			os.system('systemctl restart ntp')
			time.sleep(10)
	return response.offset

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

def date2matlab(dt):
   ord = dt.toordinal()
   mdn = dt + timedelta(days = 366)
   frac = (dt-datetime(dt.year,dt.month,dt.day,0,0,0)).seconds / (24.0 * 60.0 * 60.0)
   return mdn.toordinal() + frac

def filetowrite(datadir,filenm,parameters):
	directory = datadir+'/' + datetime.utcnow().strftime("%Y%m")
	if not os.path.exists(directory):
		os.makedirs(directory)
	name = "/"+filenm+'_'+datetime.utcnow().isoformat()[:10]+".csv"
	fname = directory + name
	if os.path.isfile(fname) == False:
		f = open(fname,'w')
		f.write("'STATIONID','YEAR','MONTH','DAY','HOUR','MINUTE','SECOND','TIME',"+''.join(["'"+x+"'," for x in parameters])[:-1]+'\n')
		f.close()
	return fname

def savetofile(datadir,filenm,id,parameters,measurements):
	fname=filetowrite(datadir,filenm,parameters)
	if type(measurements) is not list:
		logging.warning("Measurements error, no data")
		return 2
	logging.warning("Writing to file %s" % fname)
	with open(fname, 'a') as f:
		for ms in measurements:
			f.write(str(id)+','+str(ms[0].year)+','+str(ms[0].month)+','+str(ms[0].day)+','+str(ms[0].hour)+','+str(ms[0].minute)+','+str(ms[0].second)+','+str(date2matlab(ms[0]))+','+''.join([str(x)+',' for x in ms[1]])[:-1]+'\n')

	return fname

def sendtodb(dbname,id,sensor,parameters,measurements):
	try:
		conn = sqlite3.connect(dbname)
		c = conn.cursor()
	except Exception as e:
		logging.critical('SQLite errror: %s' % e)

	if type(measurements) is not list:
		logging.warning("Measurements error, no data")
		return 2

	logging.warning("Saving to database SQLite %s" % dbname)

	savevalues=[]
	for ms in measurements:
		dt = ms[0].strftime('%Y-%m-%d %H:%M:%S')
		for v in range(len(ms[1])):
			savevalues.append((id,dt,sensor,parameters[v],ms[1][v]))
	c.executemany('INSERT INTO msmt VALUES (?,?,?,?,?)', savevalues)
	conn.commit()
	conn.close()
	return dbname

def sendtosrv(srv,id,sensor,parameters,measurements):
	''' Function to calcaulate mean value and send it to server. Time resolution is minutely.'''
	if type(measurements) is not list:
		logging.warning("Measurements error, wrond datatype")
		return 2
	if len(measurements) == 0:
		logging.warning("Measurements error, empty table.")
		return 3

	try:
		msmtminute = datetime.strptime(measurements[int(len(measurements)/2)][0].strftime('%Y-%m-%d %H:%M:00'),'%Y-%m-%d %H:%M:%S').timestamp()
		lenparams = len(parameters)
		lenmsmt = len(measurements)
		values=[]
		for ms in range(lenmsmt):
			for v in range(lenparams):
				values.insert(ms*lenparams+v,measurements[ms][1][v])

		values = ''.join([ str((sum(values[i::lenparams])/lenmsmt))+'|' for i in range(lenparams)])
		parameters = ''.join(s+'|' for s in parameters)

		payload = {
		'station' : id,
		'sensor' : sensor,
		'date' : msmtminute,
		'parameters' : parameters,
		'values' : values,
		'count' : lenparams,
		## TODO: create proper CRC function or hash/oath to verify secret keys
		'crc' : 13
		}
		logging.warning("Values: %s, Sending to server: %s" % (values,str(srv)))
		r = requests.post(str(srv),params=payload)
		return r.status_code

	except Exception as e:
		logging.critical('Sending error: %s' % e)
		return 4
