import sys
import yaml
import platform
import subprocess
from typing import TypedDict

from src.bot import D20DiscordBot


class BotConfigDict(TypedDict):
    BOT_TOKEN: str


def install_uvloop():
    if platform.system() == "Linux":
        try:
            import uvloop
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "uvloop"])

            install_uvloop()
        else:
            uvloop.install()


if __name__ == '__main__':
    install_uvloop()

    with open("botconfig.yml") as fh:
        config: BotConfigDict = yaml.safe_load(fh)

    bot = D20DiscordBot()

    bot.run(config["BOT_TOKEN"])
