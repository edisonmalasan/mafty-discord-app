# Mafty Bot - Discord Auto-Post Service

Mafty Bot is a Discord bot designed to provide an automated message posting service ("autopost"). It allows authorized users to schedule automatic messages to be sent to a specific channel at regular intervals. 

> [!WARNING]
> This bot utilizes user tokens to send messages on behalf of a user account. This practice is known as "self-botting" and is technically against **Discord's Terms of Service**. Use this tool at your own risk.

## Features
- **Auto-Posting:** Automatically sends a specific message to a targeted channel on an interval.
- **Access Control:** Restricts the autopost functionality to a whitelist of approved Discord user IDs.
- **Admin Management:** The bot owner can add or remove users from the allowed list directly via Discord slash commands.
- **Rate-Limit Handling:** Built-in sleep and retry logic to avoid spamming Discord API endpoints unecessarily when rate-limited.
- **Auto-Reactions:** The bot script automatically reacts to its successfully posted messages with emojis (💯, ✅, ❤️).

## Prerequisites
- Python 3.8 or higher.
- A registered Discord Bot with a valid token.
- The bot must be invited to a server with `application.commands` (slash commands) scope to use the commands.

## Installation

1. Clone or download the repository containing `Mafty-Bot.py`.
2. Install the required Python libraries:
   ```bash
   pip install discord.py aiohttp python-dotenv
   ```
3. Create a `.env` file in the same directory as the script and add your Discord Bot token:
   ```env
   DISCORD_TOKEN=your_bot_token_here
   ```

## Configuration

Before running the bot, you may want to configure the admin ID in `Mafty-Bot.py`:
- Open `Mafty-Bot.py` and locate the `ADMIN_ID` variable (around line 17).
- Change it to your personal Discord User ID so you can use the admin commands.
  ```python
  ADMIN_ID = 123456789012345678  # Replace with your Discord ID
  ```

## Usage

Start the bot by running:
```bash
python Mafty-Bot.py
```

### Slash Commands

The following slash commands are available once the bot is running and synced:

#### User Commands (Requires Whitelisting)
- `/autopost <token> <channel_id> <message> <delay>`
  - Starts the auto-posting task.
  - `token`: The Discord user authorization token.
  - `channel_id`: The ID of the channel where messages should be posted.
  - `message`: The content of the message to send.
  - `delay`: The interval between messages in seconds.
- `/stop`
  - Stops your currently active autopost task.

#### Admin Commands (Requires Admin ID)
- `/adduserid <user_id>`
  - Grants a specific Discord user access to use the `/autopost` command.
- `/removeuserid <user_id>`
  - Revokes a user's access to the autopost service.

## Data Storage
- Allowed users are saved persistently in a `users.json` file in the same directory as the script. This file is updated automatically when you use the admin commands.

## License
This project is licensed under the [MIT License](LICENSE).
