import requests
import datetime, time
import socket
import logging
import sd_notify

format = "[%(asctime)s] %(message)s"
logging.basicConfig(format=format, level=logging.INFO ,datefmt="%Y-%m-%d %H:%M:%S")

stationid = socket.gethostname()[-2:]
poweraddr = "http://PKINpower0%s/cm" % stationid
command = { 'cmnd':'Backlog; Delay 1800; Power OFF; Delay 600; Power ON'}
commandclr = {'cmnd':'Backlog'}

def waiter(s):
	for i in range(round(s/5)):
		time.sleep(5)
		if notify.enabled():
			notify.notify()

notify = sd_notify.Notifier()
if notify.enabled():
	notify.status("Power Relay watchdog initialization ...")
	notify.ready()

while True:
	try:
		r = requests.get(poweraddr,commandclr)
		logging.info("Power Relay command %s - response: %d" % (commandclr,r.status_code))
		time.sleep(1)

		requests.get(poweraddr,command)
		logging.info("Power Relay command %s - response: %d" % (command,r.status_code))
		if notify.enabled():
			notify.status("Sent backlog command to Power Relay [%d]" % r.status_code )
		waiter(90)

	except Exception as e:
		logging.critical("Communication ERROR with Power Relay: %s" % e)
