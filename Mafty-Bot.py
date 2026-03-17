import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import aiohttp
import urllib.parse
import os
import json
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_TOKEN")


# constants
USERS_FILE = "users.json"
ADMIN_ID = 691183268611096616

# bot setup
intents = discord.Intents.default()

class MaftyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Slash commands synced globally.")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")

bot = MaftyBot()

# user persistence
def load_users() -> set[int]:
    if not os.path.exists(USERS_FILE):
        return set()
    with open(USERS_FILE, "r") as f:
        data = json.load(f)
        return set(data.get("allowed_users", []))

def save_users(users: set[int]):
    with open(USERS_FILE, "w") as f:
        json.dump({"allowed_users": list(users)}, f, indent=2)

def is_allowed(user_id: int) -> bool:
    return user_id in load_users()

# helpers
def success_embed(title: str, description: str):
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.green()
    )
    embed.set_footer(text="Mafty Bot • AutoPost Service")
    embed.timestamp = discord.utils.utcnow()
    return embed

def error_embed(title: str, description: str):
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.red()
    )
    embed.set_footer(text="Mafty Bot • Access Control")
    embed.timestamp = discord.utils.utcnow()
    return embed

# stored task in regis
active_tasks: dict[int, asyncio.Task] = {}

# automsg worker
async def autopost_task(
    interaction: discord.Interaction,
    token: str,
    channel_id: str,
    message: str,
    delay: float
):
    emojis = ["💯", "✅", "❤️"]
    api_version = "v9"

    base_url = f"https://discord.com/api/{api_version}"
    send_url = f"{base_url}/channels/{channel_id}/messages"

    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    user_id = interaction.user.id
    print(f"[TASK STARTED] User {user_id}")

    async with aiohttp.ClientSession() as session:
        try:
            while True:
                async with session.post(
                    send_url,
                    headers=headers,
                    json={"content": message}
                ) as response:

                    # success
                    if response.status == 200:
                        data = await response.json()
                        msg_id = data["id"]
                        print(f"[{user_id}] Message sent ({msg_id})")

                        # React with emojis
                        for emoji in emojis:
                            encoded = urllib.parse.quote(emoji)
                            react_url = (
                                f"{base_url}/channels/{channel_id}/messages/"
                                f"{msg_id}/reactions/{encoded}/@me"
                            )
                            async with session.put(react_url, headers=headers):
                                pass
                            await asyncio.sleep(0.3)

                    # limit rate
                    elif response.status == 429:
                        data = await response.json()
                        retry_after = float(data.get("retry_after", delay))

                        embed = discord.Embed(
                            title="⏳ Rate Limited",
                            description=(
                                "Discord has temporarily blocked message sending for this channel.\n\n"
                                f"**Retry After:** `{retry_after:.1f}` seconds\n\n"
                                "🟡 The autopost task will automatically resume once the cooldown ends."
                            ),
                            color=discord.Color.orange()
                        )
                        embed.set_footer(text="Mafty Bot • AutoPost Service")
                        embed.timestamp = discord.utils.utcnow()

                        await interaction.followup.send(embed=embed, ephemeral=True)

                        print(f"[{user_id}] Rate limited. Waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue

                    # if invalid token
                    elif response.status == 401:
                        embed = discord.Embed(
                            title="❌ Invalid Token",
                            description=(
                                "The token you provided is invalid or has expired.\n\n"
                                "🔴 The autopost task has been stopped."
                            ),
                            color=discord.Color.red()
                        )
                        embed.set_footer(text="Mafty Bot • AutoPost Service")
                        embed.timestamp = discord.utils.utcnow()

                        await interaction.followup.send(embed=embed, ephemeral=True)
                        break

                    # other errors
                    else:
                        text = await response.text()
                        print(f"[{user_id}] Error {response.status}: {text}")

                # normal interval rate
                await asyncio.sleep(delay)

        # manual stop
        except asyncio.CancelledError:
            print(f"[TASK STOPPED] User {user_id}")
            raise

# command /AUTOPOST
@bot.tree.command(name="autopost", description="Start auto-posting messages.")
async def autopost(
    interaction: discord.Interaction,
    token: str,
    channel_id: str,
    message: str,
    delay: float
):
    user_id = interaction.user.id

    if not is_allowed(user_id):
        embed = error_embed(
            title="🔒 Access Restricted",
            description=(
                "You are not authorized to use this command.\n\n"
                "📩 Please open a ticket in our server if you want access to this service."
            )
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if user_id in active_tasks:
        embed = error_embed(
            "⚠ Autopost Already Running",
            "You already have an active autopost task.\n\nUse `/stop` before starting a new one."
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    task = asyncio.create_task(
        autopost_task(interaction, token, channel_id, message, delay)
    )
    active_tasks[user_id] = task

    embed = discord.Embed(
        title="Mafty Autopost Service Started",
        color=discord.Color.green()
    )
    embed.add_field(name="Message:", value=f"```{message}```", inline=False)
    embed.add_field(name="Channel ID:", value=f"{channel_id}", inline=True)
    embed.add_field(name="Interval:", value=f"{delay} seconds", inline=True)
    embed.add_field(name="\u200b", value="🟢 The autopost task is now running.", inline=False)
    embed.set_footer(text="Mafty Bot • AutoPost Service")
    embed.timestamp = discord.utils.utcnow()

    await interaction.response.send_message(embed=embed, ephemeral=True)

# command /STOP
@bot.tree.command(name="stop", description="Stop your active autopost task.")
async def stop(interaction: discord.Interaction):
    user_id = interaction.user.id

    task = active_tasks.get(user_id)
    if not task:
        await interaction.response.send_message(
            embed=error_embed("ℹ No Task", "No active autopost task."),
            ephemeral=True
        )
        return

    task.cancel()
    del active_tasks[user_id]

    await interaction.response.send_message(
        embed=success_embed("🛑 Autopost Stopped", "Your autopost task has been stopped successfully."),
        ephemeral=True
    )

# command /ADDUSERID -> admin only
@bot.tree.command(name="adduserid", description="Grant bot access to a user ID.")
async def add_userid(interaction: discord.Interaction, user_id: str):
    if interaction.user.id != ADMIN_ID:
        embed = error_embed(
            "🔒 Permission Denied",
            "❌ Only the bot owner can do this action."
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    users = load_users()
    user_id_int = int(user_id)

    if user_id_int in users:
        embed = error_embed(
            "⚠ User Already Allowed",
            f"User ID `{user_id}` already has access."
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    users.add(user_id_int)
    save_users(users)

    embed = success_embed(
        "✅ User Added",
        f"User ID `{user_id}` has been granted access permanently."
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# command /REMOVEUSERID -> admin only
@bot.tree.command(name="removeuserid", description="Revoke bot access from a user ID.")
async def remove_userid(interaction: discord.Interaction, user_id: str):
    if interaction.user.id != ADMIN_ID:
        embed = error_embed(
            "🔒 Permission Denied",
            "❌ Only the bot owner can do this action."
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    users = load_users()
    user_id_int = int(user_id)

    if user_id_int not in users:
        embed = error_embed(
            "ℹ User Not Found",
            f"User ID `{user_id}` does not currently have access."
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    users.remove(user_id_int)
    save_users(users)

    embed = success_embed(
        "🗑 User Removed",
        f"User ID `{user_id}` access has been revoked."
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


if __name__ == "__main__":
    if not BOT_TOKEN:
        raise RuntimeError("DISCORD_TOKEN not set in .env")

    bot.run(BOT_TOKEN)
