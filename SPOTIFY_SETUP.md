# Spotify Integration Setup Guide

This guide will help you set up Spotify integration for your Discord bot, similar to the bleed bot functionality.

## Prerequisites

1. A Spotify Developer Account
2. A Discord Bot Token
3. Python 3.8+ with the required dependencies

## Step 1: Create a Spotify App

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Log in with your Spotify account
3. Click "Create App"
4. Fill in the app details:
   - **App Name**: Your Bot Name (e.g., "Wizard Bot")
   - **App Description**: "Discord bot Spotify integration"
   - **Website**: Your bot's website (e.g., "https://wizardspell.netlify.app/")
   - **Redirect URI**: `https://your-website.com/spotify/callback`
5. Click "Save"
6. Note down your **Client ID** and **Client Secret**

## Step 1.5: Host the Callback Page

1. Upload the `spotify_callback.html` file to your website
2. Make sure it's accessible at: `https://your-website.com/spotify/callback`
3. This page will handle the Spotify authorization callback and display the code for users to copy

## Step 2: Configure Environment Variables

Create a `.env` file in your bot's root directory and add:

```env
DISCORD_TOKEN=your_discord_bot_token
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=https://your-website.com/spotify/callback
```

## Step 3: Update Configuration Files

### Option A: Using Environment Variables (Recommended)
The bot will automatically use the environment variables from your `.env` file.

### Option B: Manual Configuration
Edit `spotify_config.json`:

```json
{
  "client_id": "your_spotify_client_id",
  "client_secret": "your_spotify_client_secret",
  "redirect_uri": "https://your-website.com/spotify/callback",
  "scope": "user-read-playback-state user-modify-playback-state user-read-currently-playing user-library-modify user-library-read user-top-read"
}
```

## Step 4: Install Dependencies

Run the following command to install the required packages:

```bash
pip install -r requirements.txt
```

## Step 5: Run the Bot

Start your bot with:

```bash
python main.py
```

## Usage

### For Users

1. **Connect Spotify Account**:
   ```
   !spotify login
   ```
   This will provide a link to authorize the bot with Spotify.

2. **Complete Authorization**:
   After clicking the link and authorizing, copy the code from the URL and use:
   ```
   !spotify auth <code>
   ```

3. **Play Music**:
   ```
   !spotify play <song name>
   !spotify play welcome
   ```

4. **Control Playback**:
   ```
   !spotify pause
   !spotify resume
   !spotify skip
   !spotify previous
   !spotify now
   ```

5. **Auto-Play Feature**:
   Once connected, users can simply type:
   ```
   play welcome
   music never gonna give you up
   song bohemian rhapsody
   ```
   And the bot will automatically play the requested song on their Spotify.

### Available Commands

- `!spotify` - Show help and available commands
- `!spotify login` - Connect your Spotify account
- `!spotify auth <code>` - Complete authentication
- `!spotify play <query>` - Play a song
- `!spotify pause` - Pause current song
- `!spotify resume` - Resume current song
- `!spotify skip` - Skip to next song
- `!spotify previous` - Go to previous song
- `!spotify now` - Show currently playing
- `!spotify like` - Like current song
- `!spotify unlike` - Unlike current song
- `!spotify logout` - Disconnect Spotify

## Features

### Auto-Play Integration
- Users can type `play <song>`, `music <song>`, or `song <song>` to automatically play music
- Works seamlessly with connected Spotify accounts
- No need to use the full `!spotify play` command

### Wizard-Themed Responses
- All responses include wizard-themed messages
- Maintains the bot's personality while providing Spotify functionality

### Secure Token Management
- User tokens are stored securely in `spotify_tokens.json`
- Automatic token refresh handling
- Easy logout functionality

## Troubleshooting

### Common Issues

1. **"Not Connected" Error**:
   - Make sure the user has completed the login process
   - Check if the authorization code was entered correctly

2. **"Authentication Failed"**:
   - Verify your Spotify app credentials
   - Ensure the redirect URI matches exactly

3. **"No Results Found"**:
   - Try different search terms
   - Make sure the song exists on Spotify

4. **"Failed to Play"**:
   - Ensure Spotify is open and active on the user's device
   - Check if the user has Spotify Premium (required for playback control)

### Support

If you encounter issues:
1. Check the console logs for error messages
2. Verify all configuration files are correct
3. Ensure all dependencies are installed
4. Make sure your Spotify app has the correct permissions

## Security Notes

- Never share your Spotify Client Secret
- Keep your `.env` file secure and don't commit it to version control
- The bot only requests necessary permissions for music control
- User tokens are stored locally and can be revoked at any time

## Advanced Configuration

### Custom Redirect URI
If you want to use a different redirect URI:
1. Update it in your Spotify app settings
2. Update the `redirect_uri` in your configuration
3. Make sure the URI is accessible and returns the authorization code
4. Host the `spotify_callback.html` file at your chosen URI path

### Website Integration
The callback page (`spotify_callback.html`) is designed to:
- Display a professional authorization interface
- Show the authorization code clearly
- Provide copy-to-clipboard functionality
- Guide users through the next steps
- Match your bot's wizard theme

### Additional Scopes
You can add more Spotify scopes by modifying the `scope` field in your configuration:
- `playlist-read-private` - Read private playlists
- `playlist-modify-public` - Modify public playlists
- `user-read-email` - Read user email
- And more...

## License

This integration follows the same license as your Discord bot project.
