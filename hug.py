"""PKiN measurements API for PolandAOD database"""
import hug
import psycopg2

@hug.post('/pkin',examples='station=1500100900&date=1591286561.747425&sensor=pms7003&parameters=pm1|pm25|pm100|&values=10|20|30|&count=3&crc=99')

def measurements(station: hug.types.number, date: hug.types.in_range(1546297200.0, 1861916400.0,convert=hug.types.float_number), sensor: hug.types.text, parameters: hug.types.text, values: hug.types.text, count: hug.types.number, crc: hug.types.text, hug_timer=3):
	"""Collect data from measurement stations"""
	conn = psycopg2.connect(host="localhost",database="msmt", user="pkin", password="Rey-Nolds")
	sql = "INSERT INTO pkin(station,date,sensor,parameter,value) VALUES(%s,%s,%s,%s,%s)"
	valuesin = []
	cur = conn.cursor()
	try:
		if parameters.count('|') == count and values.count('|') == count:
			for i,j in zip(parameters.split('|')[:-1],values.split('|')[:-1]):
				valuesin.append((int(station), datetime.datetime.fromtimestamp(date).isoformat(),sensor,i,float(j)))
				#print("INSERT INTO pkin(station,date,sensor,parameter,value) VALUES(%d,%s,%s,%s,%f)" % (int(station), datetime.datetime.fromtimestamp(date).isoformat(),sensor,i,float(j)))
			cur.executemany(sql,valuesin)
			conn.commit()
	except Exception as e:
		print(e)

	cur.close()
	conn.close()

	return {'Added': int(count),'took': float(hug_timer)}
