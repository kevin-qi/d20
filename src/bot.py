from discord.ext import commands
import discord


class D20DiscordBot(commands.Bot):
    def __init__(self):
        super(D20DiscordBot, self).__init__(
            command_prefix="!",
            help_command=None,
            intents=discord.Intents.default()
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
