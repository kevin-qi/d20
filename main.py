import discord
from dotenv import load_dotenv
import os

load_dotenv()

DICE_SERVER_ID = 783787350521806868
TEST_SERVER_ID = 977045406787702807

bot = discord.Bot()

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")

@bot.slash_command(guild_ids=[DICE_SERVER_ID, TEST_SERVER_ID])
async def hello(ctx):
    await ctx.respond("Hello!")

bot.run(os.getenv('BOT_TOKEN'))