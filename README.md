# Wizard Discord Bot

A feature-rich Discord bot with moderation, fun commands, voice management, and AI capabilities powered by Llama.

## Features

### Core Commands
- **Moderation**: Jail, ban, kick, mute, and more
- **Information**: Server info, user info, and statistics
- **Fun**: Quotes, insults, and interactive commands
- **Voice Management**: Create and manage voice channels
- **Role Management**: Advanced role and button role systems
- **Tickets**: Support ticket system
- **Giveaways**: Interactive giveaway system
- **Welcome System**: Customizable welcome messages
- **Anti-Nuke**: Protection against malicious actions
- **Auto-Mod**: Automatic content moderation

### AI Commands (Premium Required)
- `!ai <question>` - Ask AI a question (uses Llama)
- `!ai enable` - Enable AI features in the server
- `!ai llama <question>` - Ask Llama AI (completely free open-source)
- `!ai breathe` - Get breathing exercise guidance

### Admin Commands
- `jsk ai enable` - Enable AI features in any server (Bot Owner only)
- `jsk ai breathe` - Get breathing exercise guidance (Bot Owner only)
- `jsk ai llama <question>` - Ask Llama AI (completely free) in any server
- `jsk ai <question>` - Ask AI a question in any server (Bot Owner only)

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd fuena-main
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file with:
   ```bash
   DISCORD_TOKEN=your_discord_bot_token_here
   LLAMA_API_KEY=your_llama_api_key_here
   ```

4. **Run the bot**
   ```bash
   python main.py
   ```

## Configuration

### AI Setup
The bot uses Llama AI models for AI assistance. See [AI_SETUP.md](AI_SETUP.md) for detailed setup instructions.

### Server-Specific Settings
- **Prefix**: Customizable command prefix per server
- **Second Owner**: Set a second owner for additional permissions
- **Premium Features**: Enable AI and other premium features per server

## Customization

You can customize Wizard's quotes, insults, and responses by editing the arrays at the top of `main.py`:

```python
WIZARD_QUOTES = [
    "Your custom quote here!",
    "Another custom quote!",
    # Add more quotes...
]
```

## Support

For help and support:
- Check the [AI_SETUP.md](AI_SETUP.md) for AI configuration
- Review the command help with `!help` in Discord
- Contact the bot owner for premium features

## License

This project is open source and available under the [MIT License](LICENSE).