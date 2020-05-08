#!/usr/bin/python
import serial
import smbus
import time
import struct
import array
import time
import io, fcntl
import subprocess
from datetime import datetime,timedelta
import os

batcmd="cat /sys/class/leds/orangepi\:green\:pwr/brightness"

datadir='/var/data/PMS7003bis'
filenm='pms7003'
hostname = socket.gethostname()
IDstacji = 30100+int(hostname[-2:])

HTU21D_ADDR = 0x40
CMD_READ_TEMP_HOLD = b"\xE3"
CMD_READ_HUM_HOLD = b"\xE5"
CMD_READ_TEMP_NOHOLD = b"\xF3"
CMD_READ_HUM_NOHOLD = b"\xF5"
CMD_WRITE_USER_REG = b"\xE6"
CMD_READ_USER_REG = b"\xE7"
CMD_SOFT_RESET = b"\xFE"
I2C_SLAVE=0x0703



class i2c(object):
   def __init__(self, device, bus):
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
	return (ord(inp[bit]) << 8) + ord(inp[bit+1])

def checkval(inp):
	'''
	Calcaulate checksum for SEN0177 data
	'''
	val=0
	for i in range(30):
		val=val+ord(inp[i])
	return val

def readsen177(serial):
	'''
	Read data from SEN0177 by serial port and return list of all measured values
	'''
	try:
		dane=serial.read(32)
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

def readtemp():
	'''
	Read temperature and humidity from HTU21 on i2c bus 0, return data in list
	'''
	try:
		# Get I2C bus
		termometr=HTU21D()
		temp=termometr.read_temperature()
		humidity=termometr.read_humidity()
		return [round(temp,2),round(humidity,2)]

	except Exception as e:
		print ("Temperature data read error: {}".format(e))
		return 2

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
        f.write("'STATIONID','YEAR','MONTH','DAY','HOUR','MINUTE','SECOND','TIME','PM1','PM2.5','PM10','Bin0','Bin1','Bin2','Bin3','Bin4','Bin5','Temperature','Humidity'\n")
        f.close()
    return fname



ser=initsen177()
inittime=datetime.now().second

while True:
	if inittime!=datetime.now().second:
		inittime=datetime.now().second
		print(datetime.now().isoformat())
		try:
		    pmy=readsen177(ser)
		    print(pmy)
		    tmpy=[-99,-99]
		    time.sleep(0.7)

		    if pmy[-1]==1:
        			fname=filetowrite()
        			with open(fname, 'a') as f:
		                    f.write(str(IDstacji)+','+str(datetime.utcnow().year)+','+str(datetime.utcnow().month)+','+str(datetime.utcnow().day)+',' \
		                    +str(datetime.utcnow().hour)+','+str(datetime.utcnow().minute)+','+str(datetime.utcnow().second)+','+str(date2matlab(datetime.now()))+',' \
		                    +toascii(pmy)+toascii(tmpy)[:-1]+'\n')
        			f.closed
        			blink()

		    else:
        			ser.close()
        			ser=initsen177()
		except Exception as e:
				ser.close()
				ser=initsen177()
				print("ERROR")
