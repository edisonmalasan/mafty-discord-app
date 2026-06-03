import discord

from config import ADMIN_ID
from services.users import load_users, save_users
from utils.embeds import error_embed, success_embed


def register_access_commands(bot: discord.Client) -> None:
    @bot.tree.command(name="adduserid", description="Grant bot access to a user ID.")
    async def add_userid(interaction: discord.Interaction, user_id: str):
        if interaction.user.id != ADMIN_ID:
            embed = error_embed(
                "Permission Denied",
                "Only the bot owner can do this action."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        users = load_users()
        user_id_int = int(user_id)

        if user_id_int in users:
            embed = error_embed(
                "User Already Allowed",
                f"User ID `{user_id}` already has access."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        users.add(user_id_int)
        save_users(users)

        embed = success_embed(
            "User Added",
            f"User ID `{user_id}` has been granted access permanently."
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="removeuserid", description="Revoke bot access from a user ID.")
    async def remove_userid(interaction: discord.Interaction, user_id: str):
        if interaction.user.id != ADMIN_ID:
            embed = error_embed(
                "Permission Denied",
                "Only the bot owner can do this action."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        users = load_users()
        user_id_int = int(user_id)

        if user_id_int not in users:
            embed = error_embed(
                "User Not Found",
                f"User ID `{user_id}` does not currently have access."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        users.remove(user_id_int)
        save_users(users)

        embed = success_embed(
            "User Removed",
            f"User ID `{user_id}` access has been revoked."
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
