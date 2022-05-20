from src import core


class GuildSummary(core.Cog):
    ...


def setup(bot):
    bot.add_cog(GuildSummary(bot))
