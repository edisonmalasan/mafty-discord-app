import asyncio
import json
import urllib.parse
from typing import Optional

import aiohttp
import discord

from config import DISCORD_API_VERSION


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


def list_user_tasks(user_id: int) -> dict[int, dict]:
    return active_tasks.get(user_id, {})


def register_task(user_id: int, task_id: int, info: dict) -> None:
    active_tasks.setdefault(user_id, {})[task_id] = info


def remove_task(user_id: int, task_id: int) -> None:
    user_tasks = active_tasks.get(user_id)
    if not user_tasks:
        return

    user_tasks.pop(task_id, None)
    if not user_tasks:
        active_tasks.pop(user_id, None)


async def autopost_task(
    interaction: discord.Interaction,
    task_id: int,
    token: str,
    channel_id: str,
    message: str,
    delay: float,
    image_payload: Optional[dict] = None
) -> None:
    emojis = ["\U0001F4AF"]
    base_url = f"https://discord.com/api/{DISCORD_API_VERSION}"
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
                post_kwargs = build_post_kwargs(base_headers, message, image_payload)

                async with session.post(send_url, **post_kwargs) as response:
                    if response.status == 200:
                        data = await response.json()
                        msg_id = data["id"]
                        print(f"[{user_id} #{task_id}] Message sent ({msg_id})")
                        await react_to_message(session, base_url, base_headers, channel_id, msg_id, emojis)

                    elif response.status == 429:
                        data = await response.json()
                        retry_after = float(data.get("retry_after", delay))
                        await notify_rate_limit(interaction, retry_after)
                        print(f"[{user_id} #{task_id}] Rate limited. Waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue

                    elif response.status == 401:
                        await notify_invalid_token(interaction)
                        break

                    else:
                        text = await response.text()
                        print(f"[{user_id} #{task_id}] Error {response.status}: {text}")

                await asyncio.sleep(delay)

        except asyncio.CancelledError:
            print(f"[TASK STOPPED] User {user_id} Task {task_id}")
            raise
        finally:
            user_tasks = active_tasks.get(user_id)
            current_task = asyncio.current_task()
            if user_tasks and user_tasks.get(task_id, {}).get("task") is current_task:
                remove_task(user_id, task_id)


def build_post_kwargs(base_headers: dict, message: str, image_payload: Optional[dict]) -> dict:
    if not image_payload:
        return {
            "headers": {
                **base_headers,
                "Content-Type": "application/json"
            },
            "json": {"content": message}
        }

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

    return {
        "headers": base_headers,
        "data": form
    }


async def react_to_message(
    session: aiohttp.ClientSession,
    base_url: str,
    headers: dict,
    channel_id: str,
    msg_id: str,
    emojis: list[str]
) -> None:
    for emoji in emojis:
        encoded = urllib.parse.quote(emoji)
        react_url = f"{base_url}/channels/{channel_id}/messages/{msg_id}/reactions/{encoded}/@me"
        async with session.put(react_url, headers=headers):
            pass
        await asyncio.sleep(0.3)


async def notify_rate_limit(interaction: discord.Interaction, retry_after: float) -> None:
    embed = discord.Embed(
        title="Rate Limited",
        description=(
            "Discord has temporarily blocked message sending for this channel.\n\n"
            f"Retry After: `{retry_after:.1f}` seconds\n\n"
            "The autopost task will automatically resume once the cooldown ends."
        ),
        color=discord.Color.orange()
    )
    embed.set_footer(text="Mafty Bot - AutoPost Service")
    embed.timestamp = discord.utils.utcnow()
    await interaction.followup.send(embed=embed, ephemeral=True)


async def notify_invalid_token(interaction: discord.Interaction) -> None:
    embed = discord.Embed(
        title="Invalid Token",
        description="The token you provided is invalid or has expired.\n\nThe autopost task has been stopped.",
        color=discord.Color.red()
    )
    embed.set_footer(text="Mafty Bot - AutoPost Service")
    embed.timestamp = discord.utils.utcnow()
    await interaction.followup.send(embed=embed, ephemeral=True)
