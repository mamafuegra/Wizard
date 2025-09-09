# Netlify Spotify Authentication Setup

## 📁 File Structure for Netlify

Upload these files to your Netlify site:

```
your-netlify-site/
├── spotify/
│   └── callback.html  (the callback page)
└── spotify-auth.html  (optional: dedicated auth page)
```

## 🔗 URL Structure

Your Spotify redirect URI will be:
```
https://wizardspell.netlify.app/spotify/callback
```

## 📝 Steps to Set Up

### 1. Create the Directory Structure
In your Netlify project, create a `spotify` folder and upload the callback page there.

### 2. Update Your Spotify App Settings
- Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
- Edit your app
- Set redirect URI to: `https://wizardspell.netlify.app/spotify/callback`

### 3. Update Your Bot Configuration
In your `.env` file:
```env
SPOTIFY_REDIRECT_URI=https://wizardspell.netlify.app/spotify/callback
```

### 4. Test the Flow
1. User types `!spotify login`
2. Bot provides Spotify auth link
3. User authorizes on Spotify
4. Spotify redirects to: `https://wizardspell.netlify.app/spotify/callback?code=AUTH_CODE`
5. Your page displays the code
6. User copies code and uses `!spotify auth <code>`

## 🎨 Optional: Dedicated Auth Page

You can also create a dedicated page at `https://wizardspell.netlify.app/spotify-auth.html` that explains the process and provides a direct link to start authentication.

## ✅ Benefits of This Approach

- ✅ Works perfectly with Netlify's static hosting
- ✅ No server-side code needed
- ✅ Professional user experience
- ✅ Mobile-friendly
- ✅ Matches your site's design
- ✅ Easy to maintain and update


