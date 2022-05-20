import discord
from dotenv import load_dotenv
import os


load_dotenv()

intents = discord.Intents.default()
intents.members=True
intents.messages = True
intents.message_content=True

bot = discord.Bot(intents=intents)


cogs_list = [
    'listener',
    'reminder',
]

for cog in cogs_list:
    bot.load_extension(f'cogs.{cog}')


bot.run(os.getenv('BOT_TOKEN'))