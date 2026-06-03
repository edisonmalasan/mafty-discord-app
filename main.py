import discord
from discord.ext import commands

from commands.access import register_access_commands
from commands.autopost import register_autopost_commands
from config import ADMIN_ID, BOT_TOKEN


intents = discord.Intents.default()


class MaftyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        register_autopost_commands(self)
        register_access_commands(self)
        await self.tree.sync()
        print("Slash commands synced globally.")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("DISCORD_TOKEN not set in .env")
    if not ADMIN_ID:
        raise RuntimeError("ADMIN_ID not set in .env")

    bot = MaftyBot()
    bot.run(BOT_TOKEN)


if __name__ == "__main__":
    main()
