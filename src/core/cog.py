from discord.ext.commands import Cog as _Cog, Bot as _Bot


class Cog(_Cog):
    def __init__(self, bot):
        self.bot: _Bot = bot
