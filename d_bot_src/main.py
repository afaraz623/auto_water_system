import json
import os
import pickle
import queue

import discord 
import pandas as pd
from discord.ext import tasks, commands
from tabulate import tabulate
import paho.mqtt.client as mqtt

from logs import log_init, log


# keeping personal stuff out of the pushed repo
with open('secrets.json', 'r') as json_file:
    per_data = json.load(json_file)

# constants
ATTACHMENT_PATH = 'attachments'
TOPIC = 'parsed_data'
BROKER_IP = '192.168.100.3'
BROKER_PORT = 1883

BOT_TOKEN = per_data['bot_token']
CHANNEL_ID = int(per_data['channel_id']) # channel id needs to be an integer for discord_api to work

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

log_init(log.INFO)

data_queue = queue.Queue()


@bot.event
async def on_ready():
        log.info(f"Logged in as {bot.user.name}")

        channel = bot.get_channel(CHANNEL_ID)
        await channel.send(f'{bot.user.name} is ready')

@bot.event
async def on_message(msg):
	if msg.channel.id == CHANNEL_ID:  

		if msg.attachments and msg.attachments[0].filename.endswith('.pdf'):
			attachment = msg.attachments[0]
			file_data = await attachment.read()
		
			if not os.path.exists(ATTACHMENT_PATH):
				os.makedirs(ATTACHMENT_PATH)

			file_path = os.path.join(ATTACHMENT_PATH, attachment.filename)
			
			with open(file_path, 'wb') as f:
				f.write(file_data)
			
			log.info(f'{attachment.filename} downloaded!')

			def on_message(client, userdata, msg):
				try:
					data = pickle.loads(msg.payload)
					data_queue.put(data)
					log.debug(f'Received Data in queue:\n{data}')

					client.disconnect()

				except Exception as e:
					log.error(f'Error while unpickling data: {e}')
			
			client = mqtt.Client('Bot')
			client.connect(BROKER_IP, BROKER_PORT, 60)

			client.loop_start()
			client.subscribe(TOPIC, qos=0)
			client.on_message = on_message

			if not send_output_to_user.is_running():  # checking if the loop is already running
				send_output_to_user.start()

	await bot.process_commands(msg) # only catch atttachments and leave bot commands

@tasks.loop(seconds=1) # if queue has data, it will be sent to the user else keep waiting for the msg to arrive
async def send_output_to_user():
	if not data_queue.empty():
		channel = bot.get_channel(CHANNEL_ID)
		
		table = tabulate(data_queue.get(), headers='keys', tablefmt='pretty', showindex=False)
		await channel.send("```\n" + table + "\n```")
		log.info("result sent to user")

		send_output_to_user.stop() 

bot.run(BOT_TOKEN)
