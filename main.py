import discord
from dotenv import load_dotenv
import os

from cogs.listener import Listener


load_dotenv()

DICE_SERVER_ID = 783787350521806868
TEST_SERVER_ID = 977045406787702807


intents = discord.Intents.default()
intents.members=True
intents.messages = True
intents.message_content=True

bot = discord.Bot(intents=intents)



@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")

@bot.slash_command(guild_ids=[DICE_SERVER_ID, TEST_SERVER_ID])
async def hello(ctx):
    await ctx.respond("Hello!")

bot.add_cog(Listener(bot))

bot.run(os.getenv('BOT_TOKEN'))