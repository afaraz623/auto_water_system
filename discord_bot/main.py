import json
import os
import logging
import time
import asyncio

import discord 
import pandas as pd
from discord.ext import tasks, commands
from tabulate import tabulate

# keeping personal stuff out of the pushed repo
with open('secrets.json', 'r') as json_file:
    per_data = json.load(json_file)

# constants
ATTACHMENT_PATH = 'downloaded'
RESULT_PATH = 'output'
RESULT_FILE_NAME = 'result'
BOT_TOKEN = per_data['bot_token']

CHANNEL_ID = int(per_data['channel_id']) # channel id needs to be an integer for discord_api to work

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

# creating a logger
logger = logging.getLogger("discord.client")
logger.setLevel(logging.INFO)

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user.name}")

    channel = bot.get_channel(CHANNEL_ID)
    await channel.send(f'{bot.user.name} is ready')

@bot.event
async def on_message(msg):
    if msg.channel.id == CHANNEL_ID:  
        
        channel = bot.get_channel(CHANNEL_ID)

        if msg.attachments and msg.attachments[0].filename.endswith('.pdf'):
            attachment = msg.attachments[0]
            file_data = await attachment.read()
            
            if not os.path.exists(ATTACHMENT_PATH):
                os.makedirs(ATTACHMENT_PATH)

            file_path = os.path.join(ATTACHMENT_PATH, attachment.filename)
            
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            logger.info(f'{attachment.filename} downloaded!')

            if not check_output_csv.is_running():  # checking if the loop is already running
                check_output_csv.start()

    await bot.process_commands(msg) # only catch atttachments and leave bot commands

@tasks.loop(seconds=5) 
async def check_output_csv():
    
    channel = bot.get_channel(CHANNEL_ID)

    output_csv_path = RESULT_PATH + '/' + RESULT_FILE_NAME + '.csv'
    
    if os.path.exists(output_csv_path):
        
        data = pd.read_csv(output_csv_path)
        data.drop('Unnamed: 0', axis = 1, inplace=True)
        
        table = tabulate(data, headers='keys', tablefmt='pretty', showindex=False)

        await channel.send("```\n" + table + "\n```")
        logger.info("result sent to user")

        os.remove(output_csv_path)
        logger.info("result.csv deleted")

        check_output_csv.cancel() 

bot.run(BOT_TOKEN)
