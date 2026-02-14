import discord
import os

from dotenv import load_dotenv

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

class DiscordClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)


intents = discord.Intents.default()
client = DiscordClient(intents=intents)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}!')


async def send_message(channel_id: str, message: str):
    channel = client.get_channel(int(channel_id))
    if channel:
        await channel.send(message)
        return f"Message sent to channel {channel_id}"
    else:
        return f"Channel {channel_id} not found"


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    print(f"Message from {message.author}: {message.content}")


async def main():

    @client.tree.command()  # Correct decorator
    async def hello(interaction: discord.Interaction):
        await interaction.response.send_message(f'Hello, im {client.user}!')

    await client.tree.sync()


    client.run(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
