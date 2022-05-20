import discord
from discord.ext import commands
import re
import numpy as np

class Listener(commands.Cog): 

    def __init__(self, bot): 
        self.bot = bot


    @commands.Cog.listener() 
    async def on_message(self, message):
        # Ignore self commands
        #if(message.author == self.bot.user):
        #    return
        print(message.content)
        if message.author.name == 'Judy':
            print(message.content)
            print(message.embeds)
            if message.embeds:
                embedded = message.embeds[0]
                #print(embedded.description)
                #print(embedded.fields[0].value)
                #print(embedded.footer)
                #print(embedded.title)
                print(embedded.title)

                if re.search("(.*) \\(Rank .*\\)", embedded.title):
                    print(embedded.fields)
                    if(not embedded.fields == []):
                        summary = embedded.fields[0].value
                        lvls = np.array(re.findall(' (\d\d\d) ', summary)).astype(np.int16)
                        trophies = np.array([x.replace(',','') for x in re.findall('\d*,\d*', summary)]).astype(np.int16)
                        guild_name = re.findall("(.*) \\(Rank .*\\)", embedded.title)[0]
                        #print(np.median(lvls), np.median(trophies), guild_name)
                        msg = '{} | Avg Lv: {} | Min Lv: {} | Max Lv: {} | Avg Trophies: {}'.format(guild_name, str(round(np.mean(lvls))), np.min(lvls), np.max(lvls), str(round(np.mean(trophies))))
                        await message.channel.send(msg)