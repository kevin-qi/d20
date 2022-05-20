import discord

import re
import numpy as np
import os
import pandas as pd
from thefuzz import fuzz
from thefuzz import process

from src import core
from src.utils.abotime import ABOtime
from src.utils.requests import JudyReq

class Reminder(core.Cog):
    """
    Reminder provides remind functionality to quickly find those who haven't raided yet.
    """

    def __init__(self, bot): 
        self.ABOtime = ABOtime()
        self.tracked_guilds = ['Dark n DICE', 'DICE', 'InstaDICE']
        super(Reminder, self).__init__(bot)

    @discord.slash_command()
    async def remind(self, ctx):
        """
        Provide quick raid reminders based on stone gains for the day.

        Steps: Get members in relevant guilds. Then calculate stone gains by each member with a seperate User query.
               This is more robust to day 1 roster changes.
        """
        # Timestamp of last reset
        curr_ts = self.ABOtime.now()['timestamp']
        prev_reset_ts = self.ABOtime.prev_reset()['timestamp']

        # Concatenated string of all guild names seperated by commas
        guild_names_string = ','.join(self.tracked_guilds) 
        
        # Fetch list of member names {"guildname": [member_list], ...}
        guild_member_names = await JudyReq().fetch_guild_member_names(guild_names_string)

        member_names_string = ','.join(guild_member_names)
        cur_member_stones = {}
        prev_member_stones = {}

        # DataFrames containing results from each timestamp
        dfs = await JudyReq().fetch_player_data(member_names_string, [prev_reset_ts.isoformat(), curr_ts.isoformat()])

        prev_df = dfs[0] # Stones from prev reset
        curr_df = dfs[1] # Stones from today

        # gains
        stone_gain = curr_df['total_stones'] - prev_df['total_stones']

        curr_df['gains'] = stone_gain

        # Find players who didn't meet criteria
        # TODO: Use a better dynamically calculated criteria
        reminder_list = curr_df[curr_df['gains'] < 2e9]['name']

        # Get discord members that are not Community Members
        discord_member_list = ctx.guild.members
        active_members = []
        active_uids = []
        role = discord.utils.find(lambda r: r.name == 'Community Members', ctx.guild.roles)
        for member in discord_member_list:
            if(role not in member.roles):
                if(member.nick):
                    active_members += [member.nick]
                else:
                    active_members += [member.name]
                active_uids += [member.id]

        # Map IGN to discord names using fuzzy logic because they are not always the same 
        mapped_names = []
        mapped_scores = []
        mapped_uids = []
        for ign in reminder_list:
            extraction = process.extractOne(ign, active_members)

            if(extraction == None):
                mapped_names += ['No Match']
                mapped_scores += [0]
            elif(extraction[1] > 70):
                mapped_names += [extraction[0]]
                mapped_scores += [extraction[1]]
                mapped_uids += [active_uids[active_members.index(extraction[0])]]
            else:
                mapped_names += ['No Match']
                mapped_scores += [extraction[1]]

        # Construct reminder message that can be copy and pasted to ping people
        zipped = zip(reminder_list,mapped_names)
        msg = "```\n"
        msg += "Remindee\nIGNs : Discord Name\n"
        msg += "-------------\n"
        msg += '\n'.join(['{} : {}'.format(ign, dis) for (ign,dis) in zipped])
        msg += '\n```'
        await ctx.send(msg)
        msg = "Reminder Message (Copy and Paste):\n```\n"
        msg += ' '.join(['<@{}>'.format(uid) for uid in mapped_uids])
        msg += ' Morning mates :wave::sunny:, please be sure to get your raids in before reset. Thanks!'
        msg += "```"
        await ctx.send(msg)

    @discord.slash_command()
    async def timeseries(self, ctx):
        curr_ts = self.ABOtime.now()['timestamp']
        timestamps = [curr_ts.subtract(minutes=30*i) for i in range(100)]
        print(timestamps)
        dfs = await JudyReq().fetch_player_data("Deadly,Tonius,DaddyJoe,Jemoni,Binx,Genro", [curr_ts, curr_ts.subtract(minutes=30)])
        df = pd.concat(dfs, ignore_index=True)
        print(df)
        df.to_csv("timeseries.csv")
def setup(bot):
    bot.add_cog(Reminder(bot))

