# FFXIV Character Management Discord Bot

A Discord bot for Final Fantasy XIV that helps users manage character groups and provides recommendations for mount/minion farming based on character progression.

## Features

- **Character Management**: Register, update, and manage FFXIV characters
- **Group Management**: Organize characters into groups for raid teams or FCs
- **Mount/Minion Tracking**: Track missing collectibles and get farming recommendations
- **MSQ Progression**: Track Main Scenario Quest progression and get content recommendations
- **API Integration**: Uses XIVAPI and FFXIVCollect API for character and collection data

## Technical Details

- Built with [interactions.py](https://github.com/interactions-py/interactions.py) for Discord interactions
- PostgreSQL database for persistent storage
- Redis caching for API response caching
- Optimized for EC2 deployment alongside other services (e.g., Minecraft)

## Requirements

- Python 3.8+
- PostgreSQL 12+
- Redis 6+
- Ubuntu 22.04 (recommended)

## Installation

### Option 1: Automated Installation (EC2)

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ffxiv-discord-bot.git
   cd ffxiv-discord-bot
   ```

2. Run the installation script:
   ```bash
   sudo ./install.sh
   ```

3. Configure environment variables:
   ```bash
   sudo nano /etc/systemd/system/ffxiv-bot.service
   ```
   
4. Update the Discord token and other settings.

5. Restart the service:
   ```bash
   sudo systemctl restart ffxiv-bot.service
   ```

### Option 2: Manual Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ffxiv-discord-bot.git
   cd ffxiv-discord-bot
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up the database:
   ```bash
   # Create a PostgreSQL user and database
   sudo -u postgres psql
   postgres=# CREATE USER ffxiv_bot WITH PASSWORD 'password';
   postgres=# CREATE DATABASE ffxiv_bot OWNER ffxiv_bot;
   postgres=# \q
   
   # Initialize the database
   python setup_db.py
   ```

5. Create a `.env` file by copying the example:
   ```bash
   cp .env.example .env
   nano .env
   ```

6. Update the environment variables in the `.env` file.

7. Run the bot:
   ```bash
   python bot.py
   ```

## Configuration

The bot is configured using environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| DISCORD_TOKEN | Discord bot token (required) | None |
| TEST_GUILD_ID | Discord guild ID for testing | None |
| DATABASE_URL | PostgreSQL connection string | postgresql://postgres:postgres@localhost/ffxiv_bot |
| REDIS_URL | Redis connection string | redis://localhost:6379/0 |
| REDIS_PASSWORD | Redis password (if required) | None |
| REDIS_CACHE_TTL | Cache time-to-live in seconds | 3600 |
| XIVAPI_KEY | XIVAPI key for higher rate limits | None |
| LOGGING_LEVEL | Logging level (INFO, DEBUG, etc.) | INFO |
| LOG_TO_FILE | Whether to log to a file | false |
| LOG_FILE_PATH | Log file path | logs/bot.log |

## Discord Bot Setup

1. Create a new application at [Discord Developer Portal](https://discord.com/developers/applications)
2. Navigate to the "Bot" tab and click "Add Bot"
3. Enable all Privileged Gateway Intents (Presence, Server Members, and Message Content)
4. Copy the token and set it as your `DISCORD_TOKEN` environment variable
5. Generate an OAuth2 URL with the following scopes:
   - bot
   - applications.commands
6. Add the bot to your server using the generated URL

## Commands

### Character Commands

- `/character register <name> <server> [primary]` - Register a new character
- `/character list` - List your registered characters
- `/character update <lodestone_id>` - Update character information
- `/character verify <lodestone_id>` - Verify character ownership
- `/character remove <lodestone_id>` - Remove a character

### Group Commands

- `/group create <name> [description] [color]` - Create a new character group
- `/group list` - List available groups
- `/group view <group_name>` - View group details
- `/group recommend <group_name>` - Get recommendations for a group
- `/group remove_character <group_name> <character_name>` - Remove a character from a group
- `/group delete <group_name> <confirm>` - Delete a group

### Farming Commands

- `/farm missing <type> [character]` - Show missing mounts or minions
- `/farm search <type> <name>` - Search for a mount or minion

### MSQ Progression Commands

- `/msq update <expansion> <progress> [character]` - Update MSQ progression
- `/msq view [character]` - View MSQ progression
- `/msq recommendations [character]` - Get content recommendations based on MSQ progress

## Development

### Project Structure

```
ffxiv-discord-bot/
├── bot.py                       # Main bot entry point
├── config.py                    # Configuration management
├── cogs/                        # Command modules
│   ├── characters.py            # Character management
│   ├── groups.py                # Group management
│   ├── farming.py               # Mount/minion farming
│   └── progression.py           # MSQ progression tracking
├── models/                      # Database models
│   ├── base.py                  # Base model class
│   ├── character.py             # Character model
│   ├── group.py                 # Group model
│   └── progress.py              # Progress model
├── services/                    # Service layer
│   ├── api_cache.py             # Redis caching
│   ├── ffxivcollect.py          # FFXIVCollect API client
│   ├── xivapi.py                # XIVAPI client
│   └── recommendation.py        # Recommendation engine
└── utils/                       # Utility functions
    ├── db.py                    # Database utilities
    └── logging.py               # Logging configuration
```

### Adding New Features

1. Create a new cog in the `cogs/` directory
2. Implement your commands using the interactions.py framework
3. Add the cog to the priority extensions list in `bot.py` if needed

## Troubleshooting

### Common Issues

- **Database connection failed**: Ensure PostgreSQL is running and credentials are correct
- **Redis connection failed**: Ensure Redis is running and credentials are correct
- **Command not found**: Make sure the bot has the applications.commands scope and has been invited to your server
- **API rate limiting**: Consider getting an XIVAPI key for higher rate limits

### Logs

Check the logs for more detailed error information:

```bash
# Check systemd service logs
sudo journalctl -u ffxiv-bot.service

# Check application logs
cat logs/bot.log
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [interactions.py](https://github.com/interactions-py/interactions.py) - Discord bot framework
- [XIVAPI](https://xivapi.com/) - Final Fantasy XIV data API
- [FFXIVCollect](https://ffxivcollect.com/) - Collection tracking API