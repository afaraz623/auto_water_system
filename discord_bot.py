from discord.ext import commands
from tabulate import tabulate
import pandas as pd
import discord
import json
import os

# keeping personal stuff out of the pushed repo
with open('personal.json', 'r') as json_file:
    per_data = json.load(json_file)

BOT_TOKEN = per_data['bot_token']
CHANNEL_ID = int(per_data['channel_id']) # channel id needs to be an integer for discord_api to work

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

    channel = bot.get_channel(CHANNEL_ID)
    await channel.send(f'{bot.user.name} is online')

@bot.event
async def on_message(msg):
    if msg.channel.id == CHANNEL_ID:  
        
        if msg.attachments and msg.attachments[0].filename.endswith('.pdf'):
            attachment = msg.attachments[0]
            file_data = await attachment.read()
            
            if not os.path.exists('downloaded'):
                os.makedirs('downloaded')
                
            file_path = os.path.join('downloaded', attachment.filename)
            
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            print(f"Downloaded the PDF: {attachment.filename}")
    
    await bot.process_commands(msg) # only catch atttachments and leave bot commands

@bot.command()
async def result(ctx):
    if os.path.exists('result.csv'):
        data = pd.read_csv('result.csv')
        data.drop('Unnamed: 0', axis = 1, inplace=True)
        
        table = tabulate(data, headers='keys', tablefmt='pretty', showindex=False)

        await ctx.send("```\n" + table + "\n```")
        os.remove('result.csv')
        
    else:
        await ctx.send('No result.csv found')

bot.run(BOT_TOKEN)
