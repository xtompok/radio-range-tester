import gpsd
from datetime import datetime
import serial
import csv
from protocol import decode_packet, packet_fieldnames, encode_packet
import click
import toml
from pathlib import Path
import asyncio
import serial_asyncio
import time
from signal import SIGINT, SIGTERM


#Packet structure: 0x02 | packet_id(16bit) | timestamp(32bit) | lon (32bit) | lat (32bit) | 0x03
# First 32 bytes escaped with 0x7D + <byte> ^ 0x20

class RadioProtocol(asyncio.Protocol):
	def __init__(self, config, csvwriter):
		self.csvwriter = csvwriter
		self.csvwriter.writerow(packet_fieldnames())
		self.recv_packet_id = None
		self.config = config


	def connection_made(self,transport):
		self.transport = transport
		self.buf = []
		asyncio.ensure_future(self.send())
		print("Radio connected")
	
	def connection_lost(self,exc):
		self.csvfile.close()
		print("Radio disconnected")

	def data_received(self,data):
		#print(f"Got data: {data}")
		if len(self.buf) > 30:
			self.buf.clear()
		for b in data:
			if b != 0x02 and len(self.buf) == 0:
				print("Waiting for 0x02...")
				continue

			self.buf.append(b)
			if b != 0x03:
				continue
			
			#print(f"Read:{self.buf}")
			data = decode_packet(self.buf)
			now = datetime.now()
			self.buf.clear()
			if data is None:
				continue	
			if self.recv_packet_id is not None and data[0] != self.recv_packet_id+1:
				print(f"Lost packet(s): last received: {self.recv_packet_id}, now received: {data[0]}")
			self.recv_packet_id = data[0]
			gps_packet = gpsd.get_current()
			outdata = (data[0], data[1], gps_packet.lon, gps_packet.lat)
			print(f"{now.second}.{now.microsecond}: {outdata}")
			self.csvwriter.writerow(outdata)

	async def send(self):
		pkt_id = 0

		last_second_sent = datetime.now().second
		while True:
			atime = int(time.time())
			now = datetime.now()
			if now.second < 20:
				await asyncio.sleep(1)
				continue
			
			if last_second_sent == now.second:
				await asyncio.sleep(0.001)
				continue
			if now.microsecond/1000 < self.config['radio']['send_shift_ms']:
				await asyncio.sleep(0.001)
				continue
			gps_packet = gpsd.get_current()
			buf = encode_packet(pkt_id, atime, gps_packet.lon, gps_packet.lat)
			#print(buf)
			self.transport.serial.write(buf)
			last_second_sent = now.second
			print(f"{now.second}.{now.microsecond}: Packet {pkt_id} sent")
			pkt_id = (pkt_id+1)%65536
			await asyncio.sleep(0.1)




@click.command()
@click.argument('config_file',type=click.File('r'))
def run(config_file):
	config = toml.load(config_file)
#	radio = serial.Serial(config['radio']['port'],baudrate=config['radio']['baudrate'], timeout=1)
	csvname = config['log']['csv_prefix']+"_"+datetime.strftime(datetime.now(),"%Y-%m-%d_%H-%M-%S")+".csv"
	csvpath = Path(config['log']['directory'])/Path(csvname)

	with open(csvpath,"w") as csvfile:
		csvwriter = csv.writer(csvfile)

		gpsd.connect()

		loop = asyncio.get_event_loop()
		radio = serial_asyncio.create_serial_connection(loop, lambda: RadioProtocol(config,csvwriter), config['radio']['port'], baudrate = config['radio']['baudrate'])
		task = asyncio.ensure_future(radio)
		print("Running loop")
		loop.run_forever()
	print("Loop ended")
	exit()


if __name__ == "__main__":
	run()

