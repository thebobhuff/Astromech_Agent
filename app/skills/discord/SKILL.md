# Discord Integration

This skill allows the agent to interact with Discord.

## Prerequisites

- A Discord bot token.
- The `discord.py` library installed.

## Setup

1.  Obtain a Discord bot token from the Discord Developer Portal.
2.  Install the `discord.py` library using `pip install discord.py`.
3.  Set the bot token as an environment variable named `DISCORD_BOT_TOKEN`.

## Usage

To use this skill, you can use the `discord_tool.py` script.

```bash
python app/skills/discord/scripts/discord_tool.py [command] [arguments]
```

## Commands

-   `send_message`: Sends a message to a specified Discord channel.

    ```bash
    python app/skills/discord/scripts/discord_tool.py send_message [channel_id] [message]
    ```

## When to use

-   When the user asks to send a message to a Discord channel.
-   When the user asks to retrieve information from a Discord channel.
