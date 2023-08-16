from discord.ext import commands
import discord
import os

BOT_TOKEN = 'MTE0MTEzNzM3NzYwNDE1MzM5Ng.GaA9eG.oYs1zjGYExBzrCBOLGmh7BxBPkIMqXI2qlGElA'
CHANNEL_ID = 1141149964995678269

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

    channel = bot.get_channel(CHANNEL_ID)
    await channel.send(f'{bot.user.name} is online')

@bot.event
async def on_message(message):
    if message.channel.id == CHANNEL_ID:  
        if message.attachments and message.attachments[0].filename.endswith('.pdf'):
            attachment = message.attachments[0]
            file_data = await attachment.read()
            
            if not os.path.exists('downloaded'):
                os.makedirs('downloaded')
                
            file_path = os.path.join('downloaded', attachment.filename)
            
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            print(f"Downloaded the PDF: {attachment.filename}")

bot.run(BOT_TOKEN)