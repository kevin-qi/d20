0import os

import discord
import datetime
import pendulum
from dotenv import load_dotenv
import re
import pandas as pd
import numpy as np
from tabulate import tabulate
import asyncio
import gspread
from discord.ext import tasks, commands
import requests
import asyncio
import httpx
import json 
from menu import PageDisplay
from thefuzz import fuzz
from thefuzz import process
from GPTJ.gptj_api import Completion

# Context for GPT (for jokes only)
context = "This bot lives in the fantasy world of ABO. D20 is an artifical intelligence robot. D20 assists Jack Frost with running the DICE guild. DICE is a guild lead by Jack Frost. PinkPiglet helped create D20. DICE is one of the strongest guild in ABO history. DICE consists of 5 branches: DICE, Slice and DICE, Dwice, InstaDICE, and ParaDICE. Snaccman is just a plebe. Perebble is a plebe. Tonius is one of the guild leaders of Slice n DICE. ABO is Auto Battle Online, an idle pvp game created by William. PinkPiglet's favorite character is Grouch."

# Helper function for a free GPT-3 API
def post_gptj(context):
    payload = {
        "context": context,
        "token_max_length": 64,
        "temperature": 1.1,
        "top_p": 1.0,
    }
    response = requests.post("http://api.vicgalle.net:5000/generate", params=payload).json()
    return response['text']

def prettify_numbers(num_arr):
    return [str(round(num/1e9,2)) for num in num_arr]
    
# Secrets :)
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Hard coded shit
# America / Los Angeles Timezone
# As of 06/09/2021
WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
BONUS_TIMES = {'Friday': [16,19], 'Saturday': [11,16,19], 'Sunday': [11]}
PENDULUM_DAYS = {'Friday': pendulum.FRIDAY, 'Saturday': pendulum.SATURDAY, 'Sunday': pendulum.SUNDAY}
GUILD_DATA_PATH = 'data/guild_data.csv'
PLAYER_DATA_PATH = 'data/player_data.csv'
GUILD_DATA_CACHE_PATH = 'data/guild_data_cache.json'
IGN_DISCORD_MAP_PATH = 'data/ign_discord_map.json'
GUILD_KEYS = ['DICE', 'Slice n DICE','Dwice', 'InstaDICE', 'ParaDICE']
GUILD_NAMES = {'dice': 'DICE', 'slice_n_dice':'Slice_n_DICE', 'dwice': 'Dwice', 'instadice':'ParaDICE', 'paradice':'InstaDICE'}
GUILD_DATA_RANGES = {'dice': 'C6:F21', 'dwice': 'H6:K21', 'slice_n_dice': 'M6:P21', 'instadice': 'C24:F39', 'paradice':'H24:K39'}

# For pebble's DICE spreadsheets
gc = gspread.service_account('./xxxxxxxxxxxxxx.json')

# I forgot what intents are
intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


guild_data_cache = {}

CTX = None


# Outdated API endpoints
JUDY_API_SNAPSHOT = 'http://159.89.42.234:2122/v1/guild/snapshot'
JUDY_API_SNAPSHOT_LATEST = 'http://159.89.42.234:2122/v1/guild/snapshot/latest'

# Message channels in DICE discord
bot_channel_id = 859134281430859826
d20_channel_id = 852411636454916137

#context = "This is a bot that will respond with funny jokes"
#examples = {
#    "How are you?": "Much better now that you are here",
#    "How are you?": "Like you, but better"}
#context_setting = Completion(context, examples)

# Get guild data from API at timestamp
def post_guild_data(name, timestamp):
    timestamp = timestamp.isoformat()
    if name not in guild_data_cache.keys():
        guild_data_cache[name] = {}

    if(timestamp in guild_data_cache[name].keys()):
        return guild_data_cache[name][timestamp]
    else:
        try:
            res = requests.post(JUDY_API_SNAPSHOT, json={"name":name, "timestamp":timestamp}).json()
            guild_data_cache[name][timestamp] = res
            with open(GUILD_DATA_CACHE_PATH, 'w') as f:
                json.dump(guild_data_cache, f)
        except HTTPError as http_err:
            print(f'HTTP error occurred: {http_err}')  # Python 3.6
        except Exception as err:
            print(f'Other error occurred: {err}')  # Python 3.6
        else:
            print('Request Success!')
        return res

# Get latest guild data
def post_guild_data_latest(name):
    try:
        res = requests.post(JUDY_API_SNAPSHOT_LATEST, json={"name":name}).json()
    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')  # Python 3.6
    except Exception as err:
        print(f'Other error occurred: {err}')  # Python 3.6
    else:
        print('Request Success!')
    return res

# Async post helper
async def post_url(session, url, name, timestamp):
    if(timestamp == None):
        print('Initiate POST for {} for {}'.format(url, name))
        response = await session.post(url=url, data=json.dumps({"name": name}), timeout=3000)
        if(response):
            print('Successful POST for {} for {}'.format(url, name))
        #response.raise_for_status() 
    else:
        print('Initiate POST for {} for {} at {}'.format(url, name, timestamp))
        response = await session.post(url=url, data=json.dumps({"name": name, "timestamp": timestamp}), timeout=3000)
        if(response):
            print('Successful POST for {} for {}'.format(url, name))
    return response

# Async get latest guild data for list of guilds
async def async_post_latest_guild_data(names):
    async with httpx.AsyncClient() as session: 
        results = await asyncio.gather(*[post_url(session, JUDY_API_SNAPSHOT_LATEST, name) for name in names])
    
    return [res.json() for res in results]

# Async get guild data for list of guilds at timestamp
async def async_post_guild_data(names, timestamp):
    async with httpx.AsyncClient() as session: 
        results = await asyncio.gather(*[post_url(session, JUDY_API_SNAPSHOT, name, timestamp) for name in names])
    
    return [res.json() for res in results]

#asyncio.run(async_post_latest_guild_data(['DICE', 'Dwice', 'InstaDICE']))
def get_total_stone_gains(hist_res):
    if(hist_res[-1] == []):
        if(len(hist_res) == 1):
            return [0, 0, 0, 0, 0]
        return get_total_stone_gains(hist_res[:-1]) + [0]
    total_stones = []
    i=0
    for gdata in hist_res:
        df = pd.DataFrame(gdata)
        total_stones = total_stones + [np.sum(df.seasonStones)]
        i = i+1
    return list(total_stones)

# Calculate guild stone gains for the day and find the naughty ones for Jack to discipline
def raid_reminder():
    today_reset_time = pendulum.today('UTC').add(hours=22).subtract(minutes=1)#.subtract(hours=3*24)
    if(pendulum.now('UTC') > today_reset_time):
        today_reset_time = today_reset_time.add(hours=24)
    prev_reset_time = today_reset_time.subtract(hours=24)
    msg = ''
    naughty_list = []
    for guild in GUILD_KEYS:
        res = post_guild_data_latest(guild)['members']
        res_prev = post_guild_data(guild, prev_reset_time)['members']
        df, member_names = guild_history_helper([res, res_prev], [])
        df = df.reset_index()
        for i in range(len(df)):
            stone_gain = df['0d'][i]
            name = df['name'][i]
            if(float(stone_gain) < 1.5):
                naughty_list += [name]
    return naughty_list


def guild_history_helper(hist_res, ignore_list):
    if(hist_res[-1] == []):
        return pd.DataFrame(), []
    dfs = {}
    total_stones = []
    i=0
    for gdata in hist_res:
        dfs[i] = pd.DataFrame(gdata)
        dfs[i] = dfs[i].drop(['updateTime','level','totalStones','rating'], axis=1)
        i = i+1

    name_sets = [set(dfs[i].name) for i in range(len(hist_res))]
    member_names = set.intersection(*name_sets)
    member_names = member_names.difference(set(ignore_list))
    for i in range(len(name_sets)):
        dfs[i] = dfs[i].loc[~dfs[i]['name'].isin(ignore_list)].sort_values(by=['name'])
        dfs[i] = dfs[i].loc[dfs[i]['name'].isin(member_names)].sort_values(by=['name'])
    daily_stones={}
    for i in range(len(name_sets)-1):
        daily_stones[i] = np.array(list(dfs[i].seasonStones)) - np.array(list(dfs[i+1].seasonStones))


    if(len(hist_res) == 5):
        df = pd.DataFrame({'name':dfs[0].name, 
                           '0d':prettify_numbers(daily_stones[0]),
                           '-1d':prettify_numbers(daily_stones[1]), 
                           '-2d':prettify_numbers(daily_stones[2]),
                           '-3d':prettify_numbers(daily_stones[3]),
                           'season':prettify_numbers(dfs[0].seasonStones)
                           })
    elif(len(hist_res) == 4):
        df = pd.DataFrame({'name':dfs[0].name, 
                           '0d':prettify_numbers(daily_stones[0]),
                           '-1d':prettify_numbers(daily_stones[1]), 
                           '-2d':prettify_numbers(daily_stones[2]),
                           '-3d':['N/A']*len(daily_stones[0]),
                           'season':prettify_numbers(dfs[0].seasonStones)
                           })
    elif(len(hist_res) == 3):
        df = pd.DataFrame({'name':dfs[0].name, 
                           '0d':prettify_numbers(daily_stones[0]),
                           '-1d':prettify_numbers(daily_stones[1]), 
                           '-2d':['N/A']*len(daily_stones[0]),
                           '-3d':['N/A']*len(daily_stones[0]),
                           'season':prettify_numbers(dfs[0].seasonStones)
                           })
    elif(len(hist_res) == 2):
        df = pd.DataFrame({'name':dfs[0].name, 
                           '0d':prettify_numbers(daily_stones[0]),
                           '-1d':['N/A']*len(daily_stones[0]),
                           '-2d':['N/A']*len(daily_stones[0]),
                           '-3d':['N/A']*len(daily_stones[0]),
                           'season':prettify_numbers(dfs[0].seasonStones)
                           })
    df = df.sort_values(by=['season'], ascending=False)
    return df, list(member_names) + ignore_list

def get_guild_history(name):

    today_reset_time = pendulum.today('UTC').add(hours=22).subtract(minutes=1)#.subtract(hours=3*24)
    if(pendulum.now('UTC') > today_reset_time):
        today_reset_time = today_reset_time.add(hours=24)
    prev_reset_time = today_reset_time.subtract(hours=24)
    prev_prev_reset_time = today_reset_time.subtract(hours=48)
    prev_prev_prev_reset_time = today_reset_time.subtract(hours=72)
    prev_prev_prev_prev_reset_time = today_reset_time.subtract(hours=96)
    res = post_guild_data_latest(name)['members']
    res_prev = post_guild_data(name, prev_reset_time)['members']
    res_prev_prev = post_guild_data(name, prev_prev_reset_time)['members']
    res_prev_prev_prev = post_guild_data(name, prev_prev_prev_reset_time)['members']
    res_prev_prev_prev_prev = post_guild_data(name, prev_prev_prev_prev_reset_time)['members']
    
    dfs = {}
    member_names = {}
    dfs[0], member_names = guild_history_helper([res, res_prev, res_prev_prev, res_prev_prev_prev, res_prev_prev_prev_prev], [])
    dfs[1], member_names = guild_history_helper([res, res_prev, res_prev_prev, res_prev_prev_prev], list(member_names))
    dfs[2], member_names = guild_history_helper([res, res_prev, res_prev_prev], list(member_names))
    dfs[3], member_names = guild_history_helper([res, res_prev], list(member_names))
    df = pd.concat([dfs[0], dfs[1], dfs[2], dfs[3]], ignore_index=True)
    # Handle new members:
    #for i in range(len(name_sets)):

    df = df.append({'name':'-----',
               '0d':'-----',
               '-1d':'-----',
               '-2d':'-----',
               '-3d':'-----',
               'season':'-----'}, ignore_index=True)
    total_stone_gains = get_total_stone_gains([res, res_prev, res_prev_prev, res_prev_prev_prev, res_prev_prev_prev_prev])
    total_stone_gains = list(np.flip(np.diff(np.flip(total_stone_gains))))
    df = df.append({'name':'TOTAL',
                    '0d':prettify_numbers([total_stone_gains[0]])[0],
                    '-1d':prettify_numbers([total_stone_gains[1]])[0],
                    '-2d':prettify_numbers([total_stone_gains[2]])[0],
                    '-3d':prettify_numbers([total_stone_gains[3]])[0],
                    'season':str(round(np.sum(df.season[:-1].astype(float)),2))}, ignore_index=True)
    print(df)
    return df
    #print(tabulate(df, headers='keys', showindex='never'))

def next_day(given_date, weekday):
    day_shift = (weekday - given_date.weekday()) % 7
    return given_date + datetime.timedelta(days=day_shift)

def compile_report():
    pages = []
    for guild in GUILD_KEYS:
        embed = discord.Embed(title=guild+' History', description=None)
        df = get_guild_history(guild)
        print(tabulate(df, tablefmt='simple', showindex="never", headers='keys'))
        embed.description = '```\n'+tabulate(df, tablefmt='simple', showindex="never", headers='keys')+'```'
        pages += [embed]
    return pages
#compile_report()
@tasks.loop(seconds=30)
async def bonus_reminder():
    now = pendulum.now("America/Los_Angeles")
    now_weekday = WEEKDAYS[now.weekday()]
    for day in BONUS_TIMES.keys():
        for hour in BONUS_TIMES[day]:
            if(now_weekday == day):
                next_bonus = now.start_of('day').add(hours=hour)
                next_bonus_end = now.start_of('day').add(hours=hour+2)
                delta = next_bonus - now
                delta_end = next_bonus_end - now
                #print(delta.in_minutes())
                msg = ''
                #print(guild.roles)
                guild = CTX.guild
                msg += discord.utils.get(guild.roles, name="Dice's Guild Member").mention
                msg += discord.utils.get(guild.roles, name="Dwice's Guild member").mention
                msg += discord.utils.get(guild.roles, name="InstaDICE's Guild Member").mention  
                msg += discord.utils.get(guild.roles, name="Slice n DICE's Guild Member").mention  
                msg += discord.utils.get(guild.roles, name="paraDICE's Guild Member").mention                    
                if(delta.in_minutes() == 30):
                    await asyncio.sleep(60)
                    bot_channel = bot.get_channel(bot_channel_id)
                    await bot_channel.send(msg+'\nBonus time starts in 30 minutes!')
                    await asyncio.sleep(120)
                if(delta.in_minutes() == 0):
                    await asyncio.sleep(60)
                    bot_channel = bot.get_channel(bot_channel_id)
                    await bot_channel.send(msg+'\nBonus time starts now!')
                    await asyncio.sleep(120)
                    #await channel.send("<@Dice's Guild Member> <@DICE Twice's Guild member> <@InstaDICE's Guild Member> \nBonus time starts now!")

@tasks.loop(minutes=15)
#@bot.command(name='test')
async def update_roster_sheet():
    url = "http://159.89.42.234:2122/v1/guild/snapshot"

    today_reset_time = pendulum.today('UTC').add(hours=22).subtract(minutes=1)#.subtract(hours=3*24)
    if(pendulum.now('UTC') > today_reset_time):
        today_reset_time = today_reset_time.add(hours=24)
    prev_reset_time = today_reset_time.subtract(hours=24)

    names = ("Slice n Dice", "DICE", "Dwice", "InstaDice", "ParaDICE", "Goon Squad", "Legion", "Balance", "PING", "Hellfire Beasts", "LegionOfAlpacas", "The Unsullied", "Goon Corp", "FhukYou", "Karnage", "Anonymo", "AntiGuild", "Titans", "AlpacaLegion", "Bin Dippers", "Khaos", "FhukIt", "Legion Revenant", "Crimson Dawn", "Bertold Guild")

    roster_sheet_key="1qJqAodIvaMT3Aap5RyLPBkDsdsRTmw_Ymz7FzZfjFks"
    ws = gc.open_by_key(roster_sheet_key).worksheet("AutoExport")

    
    data = await async_post_guild_data(names, prev_reset_time.isoformat())
    print(data)
    if data:
        members = []
        for g in data:
            for m in g["members"]:
                members.append([
                    g['name'], m["name"], m["level"], m["rating"], m["seasonStones"], m["totalStones"], g['rank']
                ])
        print(members)
        ws.update("A3:Z", members)
    #print(ws.get("A3:Z"))

update_roster_sheet.start()

if(os.path.exists(GUILD_DATA_PATH)):
    print("Loading guild data from database")
    guild_data = pd.read_csv(GUILD_DATA_PATH)
else:
    print("No existing guild data, initializing new database")
    guild_data = pd.DataFrame(columns=['guild_name', 'summary', 'last_updated'])
    guild_data.to_csv(GUILD_DATA_PATH)

if(os.path.exists(PLAYER_DATA_PATH)):
    print("Loading player data from database")
    player_data = pd.read_csv(PLAYER_DATA_PATH)
    player_data = player_data.dropna()
else:
    print("No existing guild data, initializing new database")
    player_data = pd.DataFrame(columns=['name', 'lvl', 'trophies', 'total_stones', 'guild', 'timestamp'])
    player_data.to_csv(PLAYER_DATA_PATH)

if(os.path.exists(GUILD_DATA_CACHE_PATH)):
    print("Loading guild history data cache from database")
    with open(GUILD_DATA_CACHE_PATH, 'r') as f:
        guild_data_cache = json.load(f)
else:
    guild_data_cache = {}

if(os.path.exists(IGN_DISCORD_MAP_PATH)):
    print("Loading ign discord mapping from file")
    with open(IGN_DISCORD_MAP_PATH, 'r') as f:
        IGN_DISCORD_MAPPING = json.load(f)
else:
    IGN_DISCORD_MAPPING = {'SkyLightRed':'JackFrost', 'Snaccman':'Big Daddy Snacc', 'Shanzaberon':'Shanza'}


def get_stone_gains(t_minus_days):
    today= player_data['timestamp'].max().split(' ')[0]
    day = pendulum.from_format(today,'M/DD/YYYY').subtract(hours=24*t_minus_days).format('M/DD/YYYY')
    prev_day = pendulum.from_format(today,'M/DD/YYYY').subtract(hours=24*(t_minus_days+1)).format('M/DD/YYYY')
    
    data = player_data[player_data['timestamp'].str.contains(day)]
    prev_data = player_data[player_data['timestamp'].str.contains(prev_day)]
    tracked = pd.merge(prev_data, data, how='inner', on=['name'])
    
    return tracked

@tasks.loop(seconds = 60)
async def daily_report():
    prev_updated = None

    now = pendulum.now("America/Los_Angeles")
    reset_time = now.start_of('day').add(hours=15).add(minutes=0)
    delta = reset_time - now
    if(delta.in_hours() == 0 and delta.minutes >= 0 and delta.minutes <= 0):
        print("Checking daily report updates")
        sh = gc.open("DICE")
        ws = sh.get_worksheet(0)
        last_updated = ws.get('D2')[0][0]
        #print(last_updated)
        last_updated = pendulum.parse(last_updated)
        last_updated = last_updated.in_tz('America/Los_Angeles')
        last_updated = last_updated.format("M/DD/YYYY HH:mm")
        #print(last_updated)
        player_data = pd.read_csv(PLAYER_DATA_PATH)
        player_data = player_data.dropna()
        prev_updated = player_data['timestamp'].max()
        #print(prev_updated)
        if(last_updated != prev_updated):
            print("Updating player data history")
            reports = {}
            guild_tracking_data = pd.DataFrame(columns = ['name', 'lvl', 'trophies', 'total_stones', 'guild', 'timestamp'])
            for guild in GUILD_DATA_RANGES.keys():
                reports[guild] = ws.get(GUILD_DATA_RANGES[guild])
                #print(tabulate(reports[guild], tablefmt='plain',showindex="never"))
                df = pd.DataFrame(reports[guild], columns = ['name', 'lvl', 'trophies', 'total_stones'])
                df['guild'] = [guild]*len(df)
                df['timestamp'] = [last_updated]*len(df)
                guild_tracking_data = guild_tracking_data.append(df.loc[1:])
            player_data = player_data.append(guild_tracking_data)
            player_data.to_csv(PLAYER_DATA_PATH, index=False)
            #print(tabulate(guild_tracking_data))
            await asyncio.sleep(1)
            pages = compile_report()
            d20_channel = bot.get_channel(d20_channel_id)
            await PageDisplay(pages=pages).start(CTX, channel=d20_channel)
        else:
            print("Already updated for the day")

@bot.command(name='bonus')
async def bonus(ctx):
    global CTX
    CTX = ctx

    msg = 'Bonus Time Countdown\n```'
    now = pendulum.now("America/Los_Angeles")
    now_weekday = WEEKDAYS[now.weekday()]
    for day in BONUS_TIMES.keys():
        for hour in BONUS_TIMES[day]:
            is_now = False
            if(now_weekday == day):
                next_bonus = now.start_of('day').add(hours=hour)
                next_bonus_end = now.start_of('day').add(hours=hour+2)
                delta = next_bonus - now
                delta_end = next_bonus_end - now
                if abs(delta_end.in_hours() - delta.in_hours()) == 2:
                    next_bonus = now.next(PENDULUM_DAYS[day]).add(hours=hour)
                    next_bonus_end = now.next(PENDULUM_DAYS[day]).add(hours=hour+2)
            else:
                next_bonus = now.next(PENDULUM_DAYS[day]).add(hours=hour)
                next_bonus_end = now.next(PENDULUM_DAYS[day]).add(hours=hour+2)
            delta = next_bonus - now
            delta_end = next_bonus_end - now
            if not abs(delta_end.in_hours() - delta.in_hours()) == 2:
                next_bonus_start = next_bonus_end.subtract(hours=2)
                remaining_mins= 120-abs((next_bonus_start - now).in_minutes())
                msg = msg + '\n{}: Now! ({}hr {}min remaining).'.format(day,remaining_mins // 60,remaining_mins % 60)
            else:
                msg = msg + '\n{}: {}d {}hr {}min'.format(day, delta.days % 7, delta.hours, delta.minutes)
    await ctx.send(msg+'```')

def is_admin(ctx):
    admin_role = discord.utils.get(ctx.guild.roles, name="Admin")
    return admin_role in ctx.author.roles

@bot.command(name='maps')
@commands.check(is_admin)
async def maps(ctx, *args):
    if(len(args) >= 1):
        if(args[0] == '--add' or args[0] == '-a'):
            arg = ' '.join(args[1:])
            if(':' in arg):
                ign, dis = arg.split(':')[0].strip(), arg.split(':')[1].strip()
                IGN_DISCORD_MAPPING[ign] = dis
                with open(IGN_DISCORD_MAP_PATH, 'w') as f:
                    json.dump(IGN_DISCORD_MAPPING, f)
                await ctx.send("Added {} : {} to MAPS".format(ign, dis))
            else:
                await ctx.send("Invalid command. Do you mean `!maps --add <ign>:<discord_name>`")
        elif(args[0] == '--list' or args[0] == '-l'):
            msg = '```json\n{\n'
            msg += ',\n'.join(['{} : {}'.format(ign,IGN_DISCORD_MAPPING[ign]) for ign in IGN_DISCORD_MAPPING.keys()])
            msg += '\n}```'
            await ctx.send(msg)
        elif(args[0] == '--remove' or args[0] == '-rm'):
            arg = ' '.join(args[1:]).strip()
            if(arg in IGN_DISCORD_MAPPING.keys()):
                IGN_DISCORD_MAPPING.pop(arg)
                with open(IGN_DISCORD_MAP_PATH, 'w') as f:
                    json.dump(IGN_DISCORD_MAPPING, f)
                await ctx.send("Removed {} from MAPS".format(arg))
            else:
                await ctx.send("{} does not exist in MAPS".format(arg))
        else:
            await ctx.send("Invalid command. Do you mean `!maps --add <ign>:<discord_name>` or `!maps --list` or `!maps --remove <ign>`?")
    else:
        await ctx.send("Invalid command. Do you mean `!maps --add <ign>:<discord_name>` or `!maps --list` or `!maps --remove <ign>`?")


print(process.extractOne('Rayonguyanachmp', ['Tonius','Dragyus']))
@bot.command(name='remind')
@commands.check(is_admin)
async def remind(ctx, *args):
    #msg = raid_reminder()
    active_members = {}
    guild_role_names = ["Dice's Guild Member", "Dwice's Guild member", "InstaDICE's Guild Member","Slice n DICE's Guild Member","paraDICE's Guild Member"]
    guild_member_roles = [discord.utils.get(ctx.guild.roles, name=name) for name in guild_role_names]
    print(guild_member_roles)
    member_list = await ctx.guild.fetch_members(limit=None).flatten()
    for member in member_list:
        name = member.nick
        if(name == None):
            name = member.name
        if(name in IGN_DISCORD_MAPPING.keys()):
            name = IGN_DISCORD_MAPPING[name]
        if(any(role in member.roles for role in guild_member_roles)):
            active_members[name] = member
    print(len(active_members))
    if(len(active_members) > 75):
        await ctx.send("Warning: There are more than 75 active members according to discord roles")

    print(list(active_members.keys()))
    #igns = ['pinkPorklet', 'SkyLightRed', 'Twystidersdfa', 'JackFrost']
    igns = raid_reminder()
    igns_mapped = []
    igns_mapped = [IGN_DISCORD_MAPPING[ign] if ign in IGN_DISCORD_MAPPING.keys() else ign for ign in igns ]
    mapped_names = []
    mapped_scores = []

    for ign in igns_mapped:
        extraction = process.extractOne(ign, list(active_members.keys()))

        if(extraction == None):
            mapped_names += ['No Match']
            mapped_scores += [0]
        elif(extraction[1] > 70):
            mapped_names += [extraction[0]]
            mapped_scores += [extraction[1]]
        else:
            mapped_names += ['No Match']
            mapped_scores += [extraction[1]]
    
    print(list(zip(mapped_names, mapped_scores)))
    zipped = zip(igns,mapped_names)
    uids = [active_members[name].id for name in mapped_names if name != 'No Match']
    msg = "```\n"
    msg += "Remindee\nIGNs : Discord Name\n"
    msg += "-------------\n"
    msg += '\n'.join(['{} : {}'.format(ign, dis) for (ign,dis) in zipped])
    msg += '\n```'
    await ctx.send(msg)
    msg = "Reminder Message (Copy and Paste):\n```\n"
    msg += ' '.join(['<@{}>'.format(uid) for uid in uids])
    msg += ' Morning mates :wave::sunny:, please be sure to get your raids in before reset. Thanks!'
    msg += "```"
    await ctx.send(msg)

@bot.command(name='yield')
async def expected_yield(ctx, *args):
    if(len(args) != 2):
        ctx.send("Invalid number of arguments. Do you mean !yield <avg_level> <avg_battle_time>?")
    bt = float(args[-1])
    lvl = float(args[0])
    if(lvl < 300):
        await ctx.send("This command currently is only valid for lvl > 300")
    else:
        per_battle_gain = lvl*0.04929021025847054 - 7.71414356501938
        expected = (25*60*per_battle_gain*2)/(bt)
        await ctx.send("Your expected stone yield is {}b without bonus and {}b with bonus".format(round(expected/1000,2), round(1.25*expected/1000,2)))

@bot.command(name='history')
@commands.cooldown(1, 120, commands.BucketType.guild)
async def history(ctx, *args):
    global CTX
    CTX = ctx
    if(len(args) == 0): # Return DICE family summary
        pages = compile_report()
        d20_channel = bot.get_channel(d20_channel_id)
        await PageDisplay(pages=pages, timeout=10800).start(ctx)
    else:
        name = ' '.join(args)
        embed = discord.Embed(title=name+' History', description=None)
        df = get_guild_history(name)
        print(tabulate(df, tablefmt='simple', showindex="never", headers='keys'))
        embed.description = '```\n'+tabulate(df, tablefmt='simple', showindex="never", headers='keys')+'```'
        await ctx.send(embed=embed)

@bot.command(name='d20')
async def d20(ctx):
    msg = "```\n"
    msg += 'Commands\n'
    msg += '--------\n'
    msg += '`!gdata`\n'
    msg += '\tSimplified guild summary\n'
    msg += '`!gdata -v`\n'
    msg += '\tVerbose guild summary\n'
    msg += '`!gdata -rm <guild_name>`\n'
    msg += '\tRemove <guild_name> from guild summary tracking\n'
    msg += '\n'
    msg += '`!history`\n'
    msg += '\tStone gain history of DICE guilds\n'
    msg += '`!history <guild_name>`\n'
    msg += '\tStone gain history of <guild_name>\n'
    msg += '\n'
    msg += '`!remind`\n'
    msg += '\tRaid reminder helper\n'
    msg += '`!maps --add <ign>:<discord_name>` OR `!maps -a <ign>:<discord_name>`\n'
    msg += '\tAdd <ign>:<discord_name> mapping\n'
    msg += '`!maps --remove <ign>` OR `!maps -r <ign>`\n'
    msg += '\tRemove <ign> mapping\n'
    msg += '`!maps --list` OR `!maps -l`\n'
    msg += '\tList current mappings\n'
    msg += '```'
    await ctx.send(msg)

bot.help_command = None

@bot.command(name='g')
async def g(ctx):
    pass

@bot.command(name='gdata')
async def gdata(ctx, *args): 
    if len(args) == 0: # Simplified gdata
        embed = discord.Embed(title = 'Guilds Data',description=None)
        guild_data = pd.read_csv(GUILD_DATA_PATH)
        msg='```'
        guild_stats = pd.DataFrame(columns=['Name', 'Lv', 'TR'])#, 'Min', 'Max'])
        for i,row in guild_data.iterrows():
            summary = row['summary']
            lvls = np.array(re.findall(' (\d\d\d) ', summary)).astype(np.int16)
            trophies = np.array([x.replace(',','') for x in re.findall('\d*,\d*', summary)]).astype(np.int16)
            guild_stats = guild_stats.append({'Name': row['guild_name'],
                                'Lv': np.round(np.mean(lvls)),
                                'TR': np.round(np.mean(trophies))}, ignore_index=True)
            #msg += '{} | Avg Trophies: {} | Avg Levels: {}\n'.format(row['guild_name'], np.mean(trophies), np.mean(lvls))
        #print(tabulate(guild_stats.head(30)))
        msg += tabulate(guild_stats.sort_values(by='Lv', ascending=False).head(30),
                                                headers='keys', 
                                                tablefmt='simple',
                                                showindex="never",
                                                colalign=('left','left','left'))[:2000]
        msg = msg.replace('Lv','Lv')
        msg = msg.replace('TR','🏆')
        msg = msg.replace('MinT','Min 🏆')
        msg = msg.replace('MaxT','Max 🏆')
        embed.description = msg[:2000]+'```'
        await ctx.send(embed=embed)
    elif len(args) == 1:
        if(args[0] == '-v'): # Verbose gdata
            embed = discord.Embed(title = 'Guilds Data',description=None)
            guild_data = pd.read_csv(GUILD_DATA_PATH)
            msg='```\n'
            guild_stats = pd.DataFrame(columns=['Name', 'lvls', 'Lv (avg|min|max)', 'Tr (avg|min|max)'])#, 'Min', 'Max'])
            for i,row in guild_data.iterrows():
                summary = row['summary']
                lvls = np.array(re.findall(' (\d\d\d) ', summary)).astype(np.int16)
                trophies = np.array([x.replace(',','') for x in re.findall('\d*,\d*', summary)]).astype(np.int16)
                if(trophies.size > 0  and lvls.size > 0):
                    guild_stats = guild_stats.append({
                                        'Name': row['guild_name'],
                                        'lvls': np.round(np.mean(lvls)),
                                        'Lv (avg|min|max)': '{} | {} | {}'.format(str(round(np.mean(lvls))),np.round(np.min(lvls)), np.round(np.max(lvls))),
                                        'Tr (avg|min|max)': '{} | {} | {}'.format(np.round(np.mean(trophies)),np.round(np.min(trophies)), np.round(np.max(trophies)))},
                                        ignore_index=True)
                #msg += '{} | Avg Trophies: {} | Avg Levels: {}\n'.format(row['guild_name'], np.mean(trophies), np.mean(lvls))
            #print(tabulate(guild_stats.head(30)))
            msg += tabulate(guild_stats.sort_values(by='lvls', ascending=False).drop(['lvls'], axis=1).head(30),headers='keys', tablefmt='simple',showindex="never",
                                                    colalign=('left','left','left'))[:1996]
            msg = msg.replace('Avg Lv','Avg Lv')
            msg = msg.replace('Tr','🏆')
            msg = msg.replace('Min Tr ','Min 🏆')
            msg = msg.replace('Max Tr','Max 🏆')
            embed.description = msg[:2000]+'```'
            await ctx.send(embed=embed)
        else:
            msg = 'Invalid command. Do you mean (`!gdata`, `!gdata -v`, `!gdata -rm <guild_name>`)?'
            await ctx.send(msg)
    else:
        if args[0] == '-rm': # remove guild from guild report
            gname = ' '.join(args[1:])
            guild_data = pd.read_csv(GUILD_DATA_PATH)
            if(guild_data.guild_name.str.lower().isin([gname.lower()]).any()):
                guild_data = guild_data[guild_data.guild_name.str.lower() != gname.lower()]
                guild_data.to_csv(GUILD_DATA_PATH, index=False)
                await ctx.send("Removed {} from gdata".format(gname))
            else:
                await ctx.send("{} does not exist in gdata".format(gname));
            print("Removed", gname)
            
        else:
            msg = 'Invalid command. Do you mean (`!gdata`, `!gdata -v`, `!gdata -rm <guild_name>`)?'
            await ctx.send(msg)



@bot.event
async def on_message(message):
    global context
    await bot.process_commands(message)
    if(message.author == bot.user):
        return
    if '<@&852406387107168288>' in message.content or '<@!852406387107168288>' in message.content or 'D20' in message.content or 'd20' in message.content:
        
        msg = 'D20'.join(message.content.split('<@!852406387107168288>'))
        msg = 'D20'.join(message.content.split('<@&852406387107168288>'))
        msg = 'Human: '+msg
        print(msg)
        prompt = msg
        User = "Friend"
        temperature = 0.5
        top_probability = 1.0
        Bot = 'D20'
        """response = response = context_setting.completion(prompt,
              user=User,
              bot=Bot,
              max_tokens=32,
              temperature=temperature,
              top_p=top_probability)"""
        context = context+' '+msg
        response = post_gptj(context)
        if(':' in response):
            response = response.split(':')[1]
            matches = re.findall(r'(.*[.?!])', response)
            if(matches != []):
                response = matches[0]
                print("D20 response:", response)
                context = context + ' D20: ' + response
                print("Context:", context)
                #words = response.split()
                #if '.' in response:
                #    response = '.'.join(response.split('.')[-1])
                #print (" ".join(sorted(set(words), key=words.index)))
                if(not response == ''):
                    await message.channel.send(response)
    if message.author.name == 'Judy':
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
                    guild_data = pd.read_csv(GUILD_DATA_PATH)
                    summary = embedded.fields[0].value
                    lvls = np.array(re.findall(' (\d\d\d) ', summary)).astype(np.int16)
                    trophies = np.array([x.replace(',','') for x in re.findall('\d*,\d*', summary)]).astype(np.int16)
                    guild_name = re.findall("(.*) \\(Rank .*\\)", embedded.title)[0]
                    #print(np.median(lvls), np.median(trophies), guild_name)
                    msg = '{} | Avg Lv: {} | Min Lv: {} | Max Lv: {} | Avg Trophies: {}'.format(guild_name, str(round(np.mean(lvls))), np.min(lvls), np.max(lvls), str(round(np.mean(trophies))))
                    await message.channel.send(msg)


                    todays_date = pendulum.now("America/Los_Angeles").to_date_string()
                    print(guild_name)
                    #print(guild_data['guild_name'])
                    if(guild_name in list(guild_data['guild_name'])):
                        guild_data.loc[guild_data['guild_name'] == guild_name, ['summary', 'last_updated']] = [summary, todays_date]
                        print("Updated guild data in database")
                    else:
                        guild_data = guild_data.append({'guild_name': guild_name, 'summary': summary, 'last_updated': todays_date}, ignore_index=True)
                        print("Added new guild data in database")
                    guild_data.to_csv(GUILD_DATA_PATH, index=False)

    if message.content.startswith('!detailsasfdWUEFHASDF'):
        embed = discord.Embed(title=name, colour=colour, timestamp=timestamp, url=link, description=description)
        plt.savefig('images/graph.png', transparent=True)
        plt.close(fig)

        with open('images/graph.png', 'rb') as f:
            file = io.BytesIO(f.read())
        
        image = discord.File(file, filename='graph.png')
        embed.set_image(url=f'attachment://graph.png')


    if(np.random.rand()<0.0005):
        await message.reply("<3")
    if(np.random.rand()<0.0005):
        await message.reply("You're the best!")
    if(np.random.rand()<0.0005):
        await message.reply("Hope you roll a D20!")
    if(np.random.rand()<0.0005):
        await message.reply("D20 wishes you a wonderful day!")


#if message.content.startswith('!build suicidesquad'):
#    dice_sh = gc.open("DICE Data")
#    builds_ws = dice_sh.get_worksheet(1)
#   suicide_squad = builds_ws.get('A2:C24')
#    build_info = tabulate(suicide_squad, tablefmt='plain',showindex="never")
#    embed = discord.Embed()
#    embed.description = '```\n'+build_info+'\n```'
#    embed.title = 'Suicide Squad'
#    await message.channel.send(embed=embed)

bot.run(TOKEN)

