import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import aiohttp
import urllib.parse
import os
import json
from typing import Optional
from dotenv import load_dotenv

# ENV SETUP
load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_TOKEN")


# CONSTANTS
USERS_FILE = "users.json"
ADMIN_ID = 691183268611096616  # ONLY you can add/remove users


# BOT SETUP
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


# USER PERSISTENCE
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

# EMBED HELPERS
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

# TASK REGISTRY
active_tasks: dict[int, dict[int, dict]] = {}

def get_next_task_id(user_id: int) -> int:
    user_tasks = active_tasks.get(user_id, {})
    task_id = 1
    while task_id in user_tasks:
        task_id += 1
    return task_id

def short_text(value: str, limit: int = 80) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit - 3]}..."

# AUTPOST WORKER
async def autopost_task(
    interaction: discord.Interaction,
    task_id: int,
    token: str,
    channel_id: str,
    message: str,
    delay: float,
    image_payload: Optional[dict] = None
):
    # emojis = ["💯", "✅", "❤️"]
    emojis = ["💯"]
    api_version = "v9"

    base_url = f"https://discord.com/api/{api_version}"
    send_url = f"{base_url}/channels/{channel_id}/messages"

    base_headers = {
        "Authorization": token,
        "User-Agent": "Mozilla/5.0"
    }

    user_id = interaction.user.id
    print(f"[TASK STARTED] User {user_id} Task {task_id}")

    async with aiohttp.ClientSession() as session:
        try:
            while True:
                if image_payload:
                    form = aiohttp.FormData()
                    form.add_field(
                        "payload_json",
                        json.dumps({"content": message}),
                        content_type="application/json"
                    )
                    form.add_field(
                        "files[0]",
                        image_payload["data"],
                        filename=image_payload["filename"],
                        content_type=image_payload["content_type"]
                    )
                    post_kwargs = {
                        "headers": base_headers,
                        "data": form
                    }
                else:
                    post_kwargs = {
                        "headers": {
                            **base_headers,
                            "Content-Type": "application/json"
                        },
                        "json": {"content": message}
                    }

                async with session.post(
                    send_url,
                    **post_kwargs
                ) as response:
  
                    # SUCCESS
                    if response.status == 200:
                        data = await response.json()
                        msg_id = data["id"]
                        print(f"[{user_id} #{task_id}] Message sent ({msg_id})")

                        # React with emojis
                        for emoji in emojis:
                            encoded = urllib.parse.quote(emoji)
                            react_url = (
                                f"{base_url}/channels/{channel_id}/messages/"
                                f"{msg_id}/reactions/{encoded}/@me"
                            )
                            async with session.put(react_url, headers=base_headers):
                                pass
                            await asyncio.sleep(0.3)
                    # RATE LIMITED
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

                        print(f"[{user_id} #{task_id}] Rate limited. Waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                    # INVALID TOKEN
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
                    # OTHER ERRORS
                    else:
                        text = await response.text()
                        print(f"[{user_id} #{task_id}] Error {response.status}: {text}")

                # NORMAL INTERVAL WAIT
                await asyncio.sleep(delay)
                
        # MANUAL STOP
        except asyncio.CancelledError:
            print(f"[TASK STOPPED] User {user_id} Task {task_id}")
            raise
        finally:
            user_tasks = active_tasks.get(user_id)
            if user_tasks and user_tasks.get(task_id, {}).get("task") is asyncio.current_task():
                del user_tasks[task_id]
                if not user_tasks:
                    del active_tasks[user_id]


# /AUTOPOST
@bot.tree.command(name="autopost", description="Start auto-posting messages.")
async def autopost(
    interaction: discord.Interaction,
    token: str,
    channel_id: str,
    message: str,
    delay: float,
    image: Optional[discord.Attachment] = None
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

    image_payload = None
    if image is not None:
        if image.content_type and not image.content_type.startswith("image/"):
            embed = error_embed(
                "Invalid Image",
                "The `image` attachment must be an image file."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        image_payload = {
            "filename": image.filename,
            "content_type": image.content_type or "application/octet-stream",
            "data": await image.read()
        }

    task_id = get_next_task_id(user_id)

    # Start the background autopost task
    task = asyncio.create_task(
        autopost_task(interaction, task_id, token, channel_id, message, delay, image_payload)
    )
    active_tasks.setdefault(user_id, {})[task_id] = {
        "task": task,
        "channel_id": channel_id,
        "message": message,
        "delay": delay,
        "image_filename": image.filename if image else None,
        "started_at": discord.utils.utcnow()
    }

    # Restore full multi-line embed format
    embed = discord.Embed(
        title=f"Mafty Autopost #{task_id} Started",
        color=discord.Color.green()
    )
    embed.add_field(name="Message:", value=f"```{message}```", inline=False)
    embed.add_field(name="Channel ID:", value=f"{channel_id}", inline=True)
    embed.add_field(name="Interval:", value=f"{delay} seconds", inline=True)
    embed.add_field(name="Image:", value=image.filename if image else "None", inline=True)
    embed.add_field(name="\u200b", value="🟢 The autopost task is now running.", inline=False)
    embed.set_footer(text="Mafty Bot • AutoPost Service")
    embed.timestamp = discord.utils.utcnow()

    await interaction.response.send_message(embed=embed, ephemeral=True)

# /LISTAUTOPOST
@bot.tree.command(name="listautopost", description="List your active autopost tasks.")
async def list_autopost(interaction: discord.Interaction):
    user_id = interaction.user.id

    user_tasks = active_tasks.get(user_id, {})
    if not user_tasks:
        await interaction.response.send_message(
            embed=error_embed("No Active Autoposts", "You do not have any active autopost tasks."),
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="Your Active Autoposts",
        color=discord.Color.blue()
    )

    for task_id, info in sorted(user_tasks.items()):
        image_text = info["image_filename"] or "None"
        embed.add_field(
            name=f"Autopost #{task_id}",
            value=(
                f"Channel ID: `{info['channel_id']}`\n"
                f"Interval: `{info['delay']} seconds`\n"
                f"Image: `{image_text}`\n"
                f"Message: ```{short_text(info['message'])}```"
            ),
            inline=False
        )

    embed.set_footer(text="Use /stop task_id:<id> to stop one autopost.")
    embed.timestamp = discord.utils.utcnow()

    await interaction.response.send_message(embed=embed, ephemeral=True)

# /STOP
@bot.tree.command(name="stop", description="Stop one of your active autopost tasks.")
async def stop(interaction: discord.Interaction, task_id: int):
    user_id = interaction.user.id

    user_tasks = active_tasks.get(user_id, {})
    task_info = user_tasks.get(task_id)
    if not task_info:
        await interaction.response.send_message(
            embed=error_embed("No Task Found", f"No active autopost task found for ID `{task_id}`."),
            ephemeral=True
        )
        return

    task_info["task"].cancel()
    del user_tasks[task_id]
    if not user_tasks:
        del active_tasks[user_id]

    await interaction.response.send_message(
        embed=success_embed("Autopost Stopped", f"Autopost `#{task_id}` has been stopped successfully."),
        ephemeral=True
    )
    return

@stop.autocomplete("task_id")
async def stop_task_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> list[app_commands.Choice[int]]:
    user_tasks = active_tasks.get(interaction.user.id, {})
    choices = []

    for task_id, info in sorted(user_tasks.items()):
        name = (
            f"#{task_id} | channel {info['channel_id']} | "
            f"{short_text(info['message'], 35)}"
        )
        if not current or current in str(task_id):
            choices.append(app_commands.Choice(name=name[:100], value=task_id))

    return choices[:25]

# /ADDUSERID
@bot.tree.cmmand(name="adduserid", description="Grant bot access to a user ID.")
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


# /REMOVEUSERID
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



# RUN
if __name__ == "__main__":
    if not BOT_TOKEN:
        raise RuntimeError("DISCORD_TOKEN not set in .env")

    bot.run(BOT_TOKEN)
