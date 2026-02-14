import argparse
import asyncio
import os

# from discord_client import client, send_message
from dotenv import load_dotenv

load_dotenv()

import discord
from discord.ext import commands


# bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), intents=discord.Intents.all())


# @bot.event
# async def on_ready():
#     print(f"Logged in as {bot.user.name} - {bot.user.id}")
#     try:
#         synced = await bot.tree.sync()
#         print(f"Synced {len(synced)} command(s)")
#     except Exception as e:
#         print(e)


# @bot.command()
# async def hello(ctx):
#     await ctx.send("Hey!")


# async def send_discord_message(channel_id, message):
#     channel = bot.get_channel(int(channel_id))
#     await channel.send(message)


# bot.run(os.getenv("DISCORD_BOT_TOKEN"))


async def send_message(channel_id: str, message: str):
    # Your bot token
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")

    # Create a new bot instance
    bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

    @bot.event
    async def on_ready():
        print(f'{bot.user} is now running!')
        channel = bot.get_channel(int(channel_id))
        await channel.send(message)
        await bot.close()

    try:
        await bot.start(TOKEN)
    except discord.errors.LoginFailure as e:
        print(f"Error: {e}")


async def main():
    parser = argparse.ArgumentParser(description="Send a message to a Discord channel.")
    parser.add_argument("command", choices=["send_message"], help="The command to execute.")
    parser.add_argument("channel_id", type=str, help="The ID of the Discord channel.")
    parser.add_argument("message", type=str, help="The message to send.")

    args = parser.parse_args()

    if args.command == "send_message":
        await send_message(args.channel_id, args.message)


if __name__ == "__main__":
    asyncio.run(main())
