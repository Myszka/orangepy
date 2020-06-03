from datetime import datetime, timedelta
import os
import logging
import subprocess

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

def blink(led=0):
	red = "red\:status"
	green = "green\:pwr"

	if led == 0:
		colour = red
	else:
		colour = green

	batcmd="cat /sys/class/leds/orangepi\:"+colour+"/brightness"
	result = subprocess.check_output(batcmd, shell=True)
	if (int(result)==1):
		os.system("echo 0 > /sys/class/leds/orangepi\:"+colour+"/brightness")
	elif (int(result)==0):
		os.system("echo 1 > /sys/class/leds/orangepi\:"+colour+"/brightness")

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
