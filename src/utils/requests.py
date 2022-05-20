import asyncio
import httpx
import os
import json
import pandas as pd

class JudyReq():
    """
    Contains helper functions for communicating with JudyAPI
    """


    ABO_API = "http://159.223.168.89/api/v1" # Last updated 05/19/2022
    GUILD_SNAPSHOT_BULK = ABO_API + '/Guild/Snapshot/Bulk'
    GUILD_MEMBERS_BULK = ABO_API + '/Guild/Members/Bulk'
    USERS_SNAPSHOT_BULK = ABO_API + '/User/Snapshot/Bulk'

    async def post_url(self, session, endpoint, payload):
        """
        Helper function for Asyncio *gather requests

        Parameters
        ----------
        session
            Object passed from Asyncio parent function (e.g. "async with httpx.AsyncClient() as session:")
        endpoint
            API endpoint for query
        payload
            POST payload | dict
        """
        print('Initiate POST for {} for {}'.format(endpoint, payload))
        response = await session.post(url=endpoint, data=json.dumps(payload), timeout=300)
        if(response):
            print('Successful POST for {} for {}'.format(endpoint, payload))
        return response

    async def get_url(self, session, endpoint, payload):
        """
        Helper function for Asyncio *gather requests

        Parameters
        ----------
        session
            Object passed from Asyncio parent function (e.g. "async with httpx.AsyncClient() as session:")
        endpoint
            API endpoint for query
        payload
            payload | dict
        """
        print('Initiate GET for {} for {}'.format(endpoint, payload))

        response = await session.get(url=endpoint, params=payload, timeout=300)
        print(response)
        if(response):
            print('Successful GET for {} for {}'.format(endpoint, payload))
        return response

    async def fetch_guilds(self, guild_names, timestamp=None):
        """
        Query guild data for guild_names at timestamp
        """
        print('fetching from {}'.format(guild_names))
        if(timestamp == None): # Fetch latest
            async with httpx.AsyncClient() as session:
                payload = {"names":guild_names}
                results = await asyncio.gather(*[self.get_url(session, self.GUILD_MEMBERS_BULK, payload)])
        else: # Fetch snapshot
            async with httpx.AsyncClient() as session:
                payload = {"names":guild_names, "timestamp":timestamp}
                results = await asyncio.gather(*[self.get_url(session, self.GUILD_SNAPSHOT_BULK, payload)])
        return [res.json() for res in results]

    async def fetch_players(self, player_names, timestamps=None):
        """
        Make query to USERS_SNAPSHOT_BULK at multiple timestamps in parallel
        """
        print('fetching from {}'.format(player_names))
        print(timestamps)
        async with httpx.AsyncClient() as session:
            results = await asyncio.gather(*[self.get_url(session, self.USERS_SNAPSHOT_BULK, {"names":player_names, "timestamp":timestamp}) for timestamp in timestamps])
        return [res.json() for res in results]

    async def fetch_guild_member_names(self, guild_names, timestamp=None):
        """
        Fetch list of all player names in guild_names

        Parameters
        ----------
        guild_names
            List of guild_names

        Returns
        -------
        List of member names
        """
        res = await self.fetch_guilds(guild_names)
        res = res[0] # Only made 1 request here, so no need for list of res
        print(res)
        member_names = []
        for guild in res['Guilds']:
            gname = guild['Name']
            for member in guild['Members']:
                member_names += [member['Name']]
        return member_names

    async def fetch_player_data(self, player_names, timestamps):
        """
        Fetch player data from multiple player_names at multiple timestamps

        Parameters
        ----------
        player_names
            List of IGNs to query
        timestamps
            List of timestamps to query

        Returns
        -------
        Dict of pd.DataFrames, Key corresponds to the index of the corresponding timestamp in timestamps
        """
        responses = await self.fetch_players(player_names, timestamps)
        players = {}
        for i in range(len(responses)):
            res = responses[i]
            timestamp = timestamps[i]

            players[i] = pd.DataFrame(columns = ['name', 'guild', 'total_stones', 'season_stones'])
            for user in res['Users']:
                if(user != None):
                    name = user['Name']
                    guild = user['GuildName']
                    total_stones = user['GuildXp']
                    season_stones = user['SeasonGuildXp']
                    temp_df = pd.DataFrame([{"name":name,"guild":guild,"total_stones":total_stones,'season_stones':season_stones}])
                    players[i] = pd.concat([players[i],temp_df], ignore_index=True)
            players[i] = players[i].sort_values(by=['name'])
        return players
