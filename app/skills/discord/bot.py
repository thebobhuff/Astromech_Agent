import asyncio
import discord
from discord.ext import commands
from app.core.config import settings
from typing import Optional
from app.core.response_formatter import format_response_for_channel, split_response_for_channel

class DiscordSkill:
    def __init__(self):
        self.token = settings.DISCORD_BOT_TOKEN
        self.orchestrator = None # Lazy load
        
        intents = discord.Intents.default()
        intents.message_content = True
        
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        
        # Register events
        self.bot.event(self.on_ready)
        self.bot.event(self.on_message)

    async def _get_orchestrator(self):
        if not self.orchestrator:
            from app.agents.orchestrator import AgentOrchestrator
            self.orchestrator = AgentOrchestrator()
        return self.orchestrator

    async def on_ready(self):
        print(f'Discord Bot connected as {self.bot.user} (ID: {self.bot.user.id})')

    async def on_message(self, message):
        # Ignore own messages
        if message.author == self.bot.user:
            return

        # Check if mentioned or DM
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mentioned = self.bot.user in message.mentions
        
        if is_dm or is_mentioned:
            prompt = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
            
            if not prompt:
                return

            async with message.channel.typing():
                try:
                    orchestrator = await self._get_orchestrator()
                    
                    # Manage Session
                    session_id = f"discord_{message.author.id}"
                    from app.agents.session_manager import SessionManager
                    sm = SessionManager()
                    session = await sm.load_session(session_id)
                    
                    response_data = await orchestrator.run(
                        prompt,
                        session,
                        source_channel="discord",
                        source_metadata={
                            "platform_user_id": str(message.author.id),
                            "platform_username": str(message.author),
                            "chat_id": str(message.channel.id),
                            "is_dm": str(is_dm).lower(),
                            "transport": "discord",
                        },
                    )
                    
                    # Save session
                    if response_data.session_data:
                        await sm.save_session(response_data.session_data)
                        
                    # Split response if too long (>2000 chars)
                    response_text = format_response_for_channel(response_data.response, "discord")
                    chunks = split_response_for_channel(response_text, "discord")
                    if not chunks:
                        chunks = ["I couldn't generate a response for that request."]
                    
                    for chunk in chunks:
                        await message.reply(chunk)
                except Exception as e:
                    print(f"Error processing Discord message: {e}")
                    await message.reply("I encountered an error processing your request.")

        # Allow other commands to run if we add them later
        await self.bot.process_commands(message)

    async def start(self):
        if not self.token:
            print("Warning: DISCORD_BOT_TOKEN not set. Discord skill disabled.")
            return
        
        try:
            await self.bot.start(self.token)
        except Exception as e:
            print(f"Failed to start Discord bot: {e}")

    async def stop(self):
        if self.bot:
            await self.bot.close()
