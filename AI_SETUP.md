# AI Features Setup Guide

This bot now supports Llama AI models for AI assistance. Here's how to set it up:

## Environment Variables

Create a `.env` file in your bot directory with:

```bash
# Discord Bot Token
DISCORD_TOKEN=your_discord_bot_token_here

# Llama AI API Key (Required for AI features)
LLAMA_API_KEY=your_llama_api_key_here

# Optional: Local Llama URL (if running locally)
LLAMA_LOCAL_URL=http://localhost:8000
```

## AI Models Available

### 1. **Llama AI** 🦙
- **Purpose**: General AI assistance (completely free open-source)
- **Models**: Llama 2, Llama 3, and variants
- **Free APIs**: [llama-api.com](https://llama-api.com), [Together AI](https://together.ai)
- **Cloud**: Free tiers available
- **Local**: Can run on your own hardware

## Commands Available

### User Commands
```
!ai <question>                    # Smart AI that uses Llama
!ai llama <question>             # Ask Llama AI specifically
!ai enable                       # Enable AI in the server
!ai breathe                      # Get breathing exercises
```

### Admin Commands
```
jsk ai enable                    # Enable AI in any server
jsk ai llama <question>         # Ask Llama anywhere
jsk ai <question>               # General AI anywhere
jsk ai breathe                  # Get breathing exercise guidance
```

## How It Works

1. **Smart Model Selection**: The general `!ai` command automatically uses Llama
2. **Fallback System**: If one endpoint fails, it tries others
3. **Free Tier Support**: Works with free API keys
4. **Premium Required**: AI features need to be enabled per server

## Getting Llama API Keys

1. [llama-api.com](https://llama-api.com) - Free tier available
2. [Together AI](https://together.ai) - Free tier available
3. **Local Setup**: Run Llama on your own computer/server

## Local Llama Setup

If you want to run Llama locally:

1. Install Ollama: https://ollama.ai/
2. Run: `ollama run llama2`
3. Set `LLAMA_LOCAL_URL=http://localhost:11434` in your `.env`

## Troubleshooting

- **"AI not enabled"**: Use `!ai enable` in your server
- **"No API key"**: Set `LLAMA_API_KEY` in your `.env` file
- **"Model not found"**: Check your API provider's available models
