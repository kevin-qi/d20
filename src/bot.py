from discord.ext import commands
import discord


class D20DiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.messages = True
        intents.message_content = True

        super(D20DiscordBot, self).__init__(
            help_command=None,
            intents=intents
        )

        self._startup_called = False

    async def on_ready(self):
        if not self._startup_called:
            self.dispatch("startup")

        print("Bot is ready")

    async def on_startup(self):
        self._startup_called = True

        self.load_extension("src.exts.guild_summary")

    def add_cog(self, cog: commands.Cog, *, override: bool = False) -> None:
        super(D20DiscordBot, self).add_cog(cog, override=override)
        print(f"Loaded cog '{cog.qualified_name}'")
