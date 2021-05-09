import discord
import os
import sys

os.chdir(os.environ.get('Raika_path'))
pin = sys.argv[1]

client = discord.Client()

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$'):
        await message.channel.send(pin)
    elif message.content.startswith("close"):
        await message.channel.send('Closing!')
        await client.close()

client.run(os.environ.get('Raika_discord'))
