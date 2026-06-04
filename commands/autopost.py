import asyncio
from typing import Optional

import discord
from discord import app_commands

from services.autopost_service import (
    autopost_task,
    get_next_task_id,
    list_user_tasks,
    register_task,
    remove_task,
    short_text,
)
from services.users import is_allowed
from utils.embeds import error_embed, success_embed


def register_autopost_commands(bot: discord.Client) -> None:
    @bot.tree.command(name="autopost", description="Start auto-posting messages.")
    async def autopost(
        interaction: discord.Interaction,
        token: str,
        channel_id: str,
        message: str,
        delay: float,
        image: Optional[discord.Attachment] = None,
        emoji: Optional[str] = None
    ):
        user_id = interaction.user.id
        reaction_emoji = emoji.strip() if emoji else None

        if not is_allowed(user_id):
            embed = error_embed(
                title="Access Restricted",
                description=(
                    "You are not authorized to use this command.\n\n"
                    "Please open a ticket in our server if you want access to this service."
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
        task = asyncio.create_task(
            autopost_task(
                interaction,
                task_id,
                token,
                channel_id,
                message,
                delay,
                image_payload,
                reaction_emoji
            )
        )
        register_task(user_id, task_id, {
            "task": task,
            "channel_id": channel_id,
            "message": message,
            "delay": delay,
            "image_filename": image.filename if image else None,
            "reaction_emoji": reaction_emoji,
            "started_at": discord.utils.utcnow()
        })

        embed = discord.Embed(
            title=f"Mafty Autopost #{task_id} Started",
            color=discord.Color.green()
        )
        embed.add_field(name="Message:", value=f"```{message}```", inline=False)
        embed.add_field(name="Channel ID:", value=f"{channel_id}", inline=True)
        embed.add_field(name="Interval:", value=f"{delay} seconds", inline=True)
        embed.add_field(name="Image:", value=image.filename if image else "None", inline=True)
        embed.add_field(name="Reaction Emoji:", value=reaction_emoji or "None", inline=True)
        embed.add_field(name="\u200b", value="The autopost task is now running.", inline=False)
        embed.set_footer(text="Mafty Bot - AutoPost Service")
        embed.timestamp = discord.utils.utcnow()

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="listautopost", description="List your active autopost tasks.")
    async def list_autopost(interaction: discord.Interaction):
        user_tasks = list_user_tasks(interaction.user.id)
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
            emoji_text = info.get("reaction_emoji") or "None"
            embed.add_field(
                name=f"Autopost #{task_id}",
                value=(
                    f"Channel ID: `{info['channel_id']}`\n"
                    f"Interval: `{info['delay']} seconds`\n"
                    f"Image: `{image_text}`\n"
                    f"Reaction Emoji: `{emoji_text}`\n"
                    f"Message: ```{short_text(info['message'])}```"
                ),
                inline=False
            )

        embed.set_footer(text="Use /stop task_id:<id> to stop one autopost.")
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="stop", description="Stop one of your active autopost tasks.")
    async def stop(interaction: discord.Interaction, task_id: int):
        user_tasks = list_user_tasks(interaction.user.id)
        task_info = user_tasks.get(task_id)
        if not task_info:
            await interaction.response.send_message(
                embed=error_embed("No Task Found", f"No active autopost task found for ID `{task_id}`."),
                ephemeral=True
            )
            return

        task_info["task"].cancel()
        remove_task(interaction.user.id, task_id)

        await interaction.response.send_message(
            embed=success_embed("Autopost Stopped", f"Autopost `#{task_id}` has been stopped successfully."),
            ephemeral=True
        )

    @stop.autocomplete("task_id")
    async def stop_task_autocomplete(
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[int]]:
        choices = []

        for task_id, info in sorted(list_user_tasks(interaction.user.id).items()):
            name = (
                f"#{task_id} | channel {info['channel_id']} | "
                f"{short_text(info['message'], 35)}"
            )
            if not current or current in str(task_id):
                choices.append(app_commands.Choice(name=name[:100], value=task_id))

        return choices[:25]
