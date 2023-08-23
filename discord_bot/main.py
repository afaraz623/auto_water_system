import json
import os
import logging
import time

import discord 
import pandas as pd
from discord.ext import commands
from tabulate import tabulate

# keeping personal stuff out of the pushed repo
with open('secrets.json', 'r') as json_file:
    per_data = json.load(json_file)

BOT_TOKEN = per_data['bot_token']
CHANNEL_ID = int(per_data['channel_id']) # channel id needs to be an integer for discord_api to work
ATTACHMENT_PATH = 'downloaded'
RESULT_PATH = 'output'


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
            
            if not os.path.exists('downloaded'):
                os.makedirs('downloaded')

            file_path = os.path.join('downloaded', attachment.filename)
            
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            logger.info(f'{attachment.filename} downloaded!')
        
    await bot.process_commands(msg) # only catch atttachments and leave bot commands

@bot.command()
async def r(ctx):
    logger.info("user requested result")
    if os.path.exists('output/result.csv'):
        data = pd.read_csv('output/result.csv')
        data.drop('Unnamed: 0', axis = 1, inplace=True)
        
        table = tabulate(data, headers='keys', tablefmt='pretty', showindex=False)

        await ctx.send("```\n" + table + "\n```")
        logger.info("result sent to user")
        
    else:
        await ctx.send('No result.csv found')
        logger.info("no result to send")

bot.run(BOT_TOKEN)
