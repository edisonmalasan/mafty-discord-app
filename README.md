# Mafty Discord Auto Message Bot

A Discord slash-command bot for starting and stopping repeated autopost messages to a Discord channel.

The bot supports access control, per-user background autopost tasks, optional image attachments, automatic reaction after each sent message, and owner-only user management.

## Features

- `/autopost token:<token> channel_id:<id> message:<text> delay:<seconds> image:<attachment>` starts a new autopost task for the requesting user.
- `image` is optional. When provided, the same image is attached to every autopost message.
- Each user can run multiple active autopost tasks at the same time.
- Every autopost task gets a task ID such as `#1`, `#2`, or `#3`.
- `/listautopost` shows the requesting user's active autopost tasks.
- `/stop task_id:<id>` stops one specific autopost task.
- `/adduserid user_id:<id>` grants a Discord user access to the bot. Only the configured admin can use this.
- `/removeuserid user_id:<id>` revokes a Discord user's access. Only the configured admin can use this.
- Access control is stored in `users.json`.
- Multiple active autopost tasks are allowed per user.
- The bot sends an ephemeral confirmation embed when a task starts or stops.
- The bot handles Discord rate limits and waits before continuing.
- The bot stops a task when the provided token is invalid or expired.
- After each successful autopost message, the bot reacts with the configured emoji.

## Image Attachments

The `/autopost` command includes an optional `image` parameter:

```text
/autopost token:<token> channel_id:<channel_id> message:<message> delay:<seconds> image:<image_file>
```

The image is not typed as a text prompt. It must be uploaded as a Discord attachment.

How users attach the image:

1. Type `/autopost` in Discord.
2. Fill in `token`, `channel_id`, `message`, and `delay`.
3. Select the optional `image` field.
4. Upload an image file from the Discord file picker.
5. Send the slash command.

You can also drag and drop an image into Discord first, but for the slash command to use it, the file must be attached to the `image` option in the command form. The bot does not automatically pick up a normal image dropped into chat unless it is submitted as the slash command's `image` attachment.

Accepted files should have an image content type, such as PNG, JPG, JPEG, GIF, or WebP.

## Commands

### `/autopost`

Starts a new auto-posting task to a target channel.

Parameters:

- `token`: Discord authorization token used for sending the autopost message.
- `channel_id`: Target Discord channel ID.
- `message`: Message text to send.
- `delay`: Number of seconds to wait between posts.
- `image`: Optional image attachment to include with every post.

Example:

```text
/autopost token:YOUR_TOKEN channel_id:123456789012345678 message:Hello delay:60 image:banner.png
```

If an image is provided, every repeated message includes both the text and the image.

Each started task receives its own task ID. For example, if you start three autoposts, they may appear as `#1`, `#2`, and `#3`.

### `/listautopost`

Lists your active autopost tasks.

The list includes:

- task ID
- target channel ID
- interval delay
- image filename, if an image was attached
- message preview

Example:

```text
/listautopost
```

### `/stop`

Stops one specific autopost task.

Parameter:

- `task_id`: The ID of the autopost task to stop.

Example:

```text
/stop task_id:2
```

Use `/listautopost` first if you are not sure which task ID to stop. Discord should also show active task suggestions while filling in the `task_id` field.

### `/adduserid`

Grants access to a Discord user ID.

Only the configured admin user can run this command.

Example:

```text
/adduserid user_id:123456789012345678
```

### `/removeuserid`

Revokes access from a Discord user ID.

Only the configured admin user can run this command.

Example:

```text
/removeuserid user_id:123456789012345678
```

## Access Control

Allowed users are stored in `users.json`:

```json
{
  "allowed_users": [
    123456789012345678
  ]
}
```

The admin user ID is configured directly in `Mafty-Bot.py`:

```python
ADMIN_ID = 691183268611096616
```

Only users listed in `users.json` can start autopost tasks. Only the admin can add or remove allowed users.

## Setup

Follow these steps to set up and run the bot locally.

1. **Clone the repository**

   ```bash
   git clone <your-repository-url>
   cd mafty-discord-app
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv .venv
   ```

3. **Activate the virtual environment**

   Windows:

   ```bash
   .venv\Scripts\activate
   ```

   Mac/Linux:

   ```bash
   source .venv/bin/activate
   ```

4. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

5. **Create your `.env` file**

   Copy `.env.sample` to `.env`, then fill in your Discord Developer Portal values:

   ```env
   APP_ID=your-application-id
   DISCORD_TOKEN=your-bot-token
   PUBLIC_KEY=your-public-key
   ```

   `DISCORD_TOKEN` is required to run the bot. `APP_ID` and `PUBLIC_KEY` are included for Discord application completeness.

## Running the Bot

Start the bot with:

```bash
python Mafty-Bot.py
```

When the bot starts successfully, it syncs the slash commands globally and prints the logged-in bot user in the terminal.

Global slash command updates can take time to appear in Discord. If the updated `/autopost` image option does not show immediately, restart Discord or wait for Discord's command cache to refresh.

## Storage Files

The bot uses these local files:

- `.env`: Discord application secrets and bot token.
- `.env.sample`: Example environment file.
- `users.json`: Allowed Discord user IDs.
- `requirements.txt`: Python dependencies.
- `Mafty-Bot.py`: Main bot program.

Active autopost tasks and uploaded image bytes are kept in memory while the bot is running. They are not saved to disk. If the bot restarts, active autopost tasks must be started again.

## Important Notes

- Keep `.env` private. Never share your bot token.
- The `image` parameter must be a Discord attachment, not a text URL or prompt.
- Large images may take longer to upload on every autopost cycle.
- Very short delays can trigger Discord rate limits.
- Discord may reject messages if the account or token does not have permission to post in the target channel.
