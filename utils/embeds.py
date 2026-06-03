import discord


def success_embed(title: str, description: str) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.green()
    )
    embed.set_footer(text="Mafty Bot - AutoPost Service")
    embed.timestamp = discord.utils.utcnow()
    return embed


def error_embed(title: str, description: str) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.red()
    )
    embed.set_footer(text="Mafty Bot - Access Control")
    embed.timestamp = discord.utils.utcnow()
    return embed
