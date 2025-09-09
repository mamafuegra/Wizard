import discord
from discord.ext import commands
import os
import json
import secrets
import time
from typing import Optional, Dict, Any

import spotipy
from spotipy.oauth2 import SpotifyOAuth

SPOTIFY_CONFIG_PATH = 'spotify_config.json'
USER_TOKENS_PATH = 'spotify_tokens.json'


def load_config() -> Dict[str, Any]:
    try:
        with open(SPOTIFY_CONFIG_PATH, 'r') as f:
            cfg = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        cfg = {}
    cfg.setdefault('client_id', os.getenv('SPOTIFY_CLIENT_ID', ''))
    cfg.setdefault('client_secret', os.getenv('SPOTIFY_CLIENT_SECRET', ''))
    cfg.setdefault('redirect_uri', os.getenv('SPOTIFY_REDIRECT_URI', 'https://wizardspell.netlify.app/spotify/callback'))
    cfg.setdefault('scope', 'user-read-playback-state user-modify-playback-state user-read-currently-playing')
    return cfg


def load_tokens() -> Dict[str, Any]:
    try:
        with open(USER_TOKENS_PATH, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_tokens(tokens: Dict[str, Any]) -> None:
    with open(USER_TOKENS_PATH, 'w') as f:
        json.dump(tokens, f, indent=2)


def build_auth_url(client_id: str, redirect_uri: str, scope: str, state: str) -> str:
    from urllib.parse import urlencode
    params = {
        'client_id': client_id,
        'response_type': 'code',
        'redirect_uri': redirect_uri,
        'scope': scope,
        'state': state
    }
    return f"https://accounts.spotify.com/authorize?{urlencode(params)}"


class SpotifyCog(commands.Cog, name='spotify'):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.cfg = load_config()
        # Persisted tokens per Discord user id (str)
        self.user_tokens: Dict[str, Any] = load_tokens()
        # ephemeral state -> user id mapping for OAuth
        self.pending_auth: Dict[str, int] = {}

    # ----- Auth helpers -----
    def _auth_manager(self, user_id: int) -> SpotifyOAuth:
        return SpotifyOAuth(
            client_id=self.cfg['client_id'],
            client_secret=self.cfg['client_secret'],
            redirect_uri=self.cfg['redirect_uri'],
            scope=self.cfg['scope'],
            cache_path=f'.cache-{user_id}'
        )

    def _get_client(self, user_id: int) -> Optional[spotipy.Spotify]:
        # Rely on spotipy cache file for refresh
        try:
            auth = self._auth_manager(user_id)
            return spotipy.Spotify(auth_manager=auth)
        except Exception:
            return None

    # ----- Command routing similar to bleed -----
    @commands.command(name='spotify')
    async def spotify_root(self, ctx: commands.Context, *args: str) -> None:
        if not args:
            await ctx.send("Use `spotify login` to connect, or `spotify play <query>` to play.")
            return
        sub = args[0].lower()
        rest = ' '.join(args[1:]) if len(args) > 1 else ''
        if sub in ('login', 'connect', 'authorize'):
            await self.login(ctx)
        elif sub == 'play' and rest:
            await self.play(ctx, query=rest)
        elif sub == 'pause':
            await self.pause(ctx)
        elif sub in ('resume', 'start'):
            await self.resume(ctx)
        elif sub in ('next', 'skip'):
            await self.next(ctx)
        elif sub in ('prev', 'previous', 'back'):
            await self.previous(ctx)
        elif sub in ('now', 'np', 'status'):
            await self.now(ctx)
        elif sub == 'like':
            await self.like(ctx)
        elif sub == 'unlike':
            await self.unlike(ctx)
        elif sub == 'queue':
            if rest:
                await self.queue(ctx, query=rest)
            else:
                await self.now(ctx)
        elif sub == 'repeat':
            await self.repeat(ctx, mode=rest)
        elif sub == 'shuffle':
            await self.shuffle(ctx, state=rest)
        elif sub == 'volume':
            vol = None
            try:
                if rest:
                    vol = int(rest)
            except Exception:
                pass
            await self.volume(ctx, volume=vol)
        elif sub == 'logout':
            await self.logout(ctx)
        elif sub == 'devices':
            await self.device_list(ctx)
        else:
            await self.play(ctx, query=' '.join(args))

    # jsk alias
    @commands.command(name='jsk_spotify', aliases=['jskspotify'])
    async def jsk_spotify(self, ctx: commands.Context, *args: str) -> None:
        await self.spotify_root(ctx, *args)

    # ----- DM-based login -----
    @commands.command(name='spotify_login', aliases=['spotify_connect'])
    async def login(self, ctx: commands.Context) -> None:
        user_id = ctx.author.id
        state = secrets.token_urlsafe(24)
        self.pending_auth[state] = user_id
        url = build_auth_url(self.cfg['client_id'], self.cfg['redirect_uri'], self.cfg['scope'], state)
        embed = discord.Embed(title='Connect your Spotify', description=f"Click [here]({url}) to authorize. After authorizing, you'll be connected automatically.", color=0x1DB954)
        try:
            await ctx.author.send(embed=embed)
            if ctx.guild:
                await ctx.send(f"✅ {ctx.author.mention}, I sent you a DM with the Spotify authorization link.")
        except discord.Forbidden:
            await ctx.send("❌ I couldn't DM you. Enable DMs from server members and try again.")

    # Note: No manual auth-code command. Authorization should complete on your website callback.

    # ----- Playback & library commands -----
    @commands.command(name='spotify_play')
    async def play(self, ctx: commands.Context, *, query: str) -> None:
        sp = self._get_client(ctx.author.id)
        if not sp:
            await ctx.send('❌ Not connected. Use `spotify login`.')
            return
        try:
            res = sp.search(q=query, type='track', limit=1)
            items = res.get('tracks', {}).get('items', [])
            if not items:
                await ctx.send(f"❌ No results for '{query}'.")
                return
            track = items[0]
            sp.start_playback(uris=[track['uri']])
            await ctx.send(f"🎵 Now playing: {track['name']} — {', '.join(a['name'] for a in track['artists'])}")
        except Exception as e:
            await ctx.send(f'❌ Play failed: {e}')

    @commands.command(name='spotify_pause')
    async def pause(self, ctx: commands.Context) -> None:
        sp = self._get_client(ctx.author.id)
        if not sp:
            await ctx.send('❌ Not connected. Use `spotify login`.')
            return
        try:
            sp.pause_playback()
            await ctx.send('⏸️ Paused.')
        except Exception as e:
            await ctx.send(f'❌ Pause failed: {e}')

    @commands.command(name='spotify_resume')
    async def resume(self, ctx: commands.Context) -> None:
        sp = self._get_client(ctx.author.id)
        if not sp:
            await ctx.send('❌ Not connected. Use `spotify login`.')
            return
        try:
            sp.start_playback()
            await ctx.send('▶️ Resumed.')
        except Exception as e:
            await ctx.send(f'❌ Resume failed: {e}')

    @commands.command(name='spotify_next')
    async def next(self, ctx: commands.Context) -> None:
        sp = self._get_client(ctx.author.id)
        if not sp:
            await ctx.send('❌ Not connected. Use `spotify login`.')
            return
        try:
            sp.next_track()
            await ctx.send('⏭️ Skipped.')
        except Exception as e:
            await ctx.send(f'❌ Skip failed: {e}')

    @commands.command(name='spotify_previous')
    async def previous(self, ctx: commands.Context) -> None:
        sp = self._get_client(ctx.author.id)
        if not sp:
            await ctx.send('❌ Not connected. Use `spotify login`.')
            return
        try:
            sp.previous_track()
            await ctx.send('⏮️ Previous.')
        except Exception as e:
            await ctx.send(f'❌ Previous failed: {e}')

    @commands.command(name='spotify_seek')
    async def seek(self, ctx: commands.Context, seconds: int) -> None:
        sp = self._get_client(ctx.author.id)
        if not sp:
            await ctx.send('❌ Not connected. Use `spotify login`.')
            return
        try:
            current = sp.current_playback()
            if not current or not current.get('item'):
                await ctx.send('❌ Nothing is playing.')
                return
            sp.seek_track(int(seconds * 1000))
            await ctx.send(f'⏩ Seeked to {seconds}s')
        except Exception as e:
            await ctx.send(f'❌ Seek failed: {e}')

    @commands.command(name='spotify_now')
    async def now(self, ctx: commands.Context) -> None:
        sp = self._get_client(ctx.author.id)
        if not sp:
            await ctx.send('❌ Not connected. Use `spotify login`.')
            return
        try:
            current = sp.current_playback()
            if not current or not current.get('item'):
                await ctx.send('🎵 Nothing playing.')
                return
            t = current['item']
            await ctx.send(f"🎵 Now playing: {t['name']} — {', '.join(a['name'] for a in t['artists'])}")
        except Exception as e:
            await ctx.send(f'❌ Failed: {e}')

    @commands.command(name='spotify_like')
    async def like(self, ctx: commands.Context) -> None:
        sp = self._get_client(ctx.author.id)
        if not sp:
            await ctx.send('❌ Not connected. Use `spotify login`.')
            return
        try:
            current = sp.current_playback()
            if not current or not current.get('item'):
                await ctx.send('❌ Nothing is playing.')
                return
            sp.current_user_saved_tracks_add([current['item']['id']])
            await ctx.send('❤️ Liked the current track.')
        except Exception as e:
            await ctx.send(f'❌ Like failed: {e}')

    @commands.command(name='spotify_unlike')
    async def unlike(self, ctx: commands.Context) -> None:
        sp = self._get_client(ctx.author.id)
        if not sp:
            await ctx.send('❌ Not connected. Use `spotify login`.')
            return
        try:
            current = sp.current_playback()
            if not current or not current.get('item'):
                await ctx.send('❌ Nothing is playing.')
                return
            sp.current_user_saved_tracks_delete([current['item']['id']])
            await ctx.send('💔 Unliked the current track.')
        except Exception as e:
            await ctx.send(f'❌ Unlike failed: {e}')

    @commands.command(name='spotify_queue')
    async def queue(self, ctx: commands.Context, *, query: str) -> None:
        sp = self._get_client(ctx.author.id)
        if not sp:
            await ctx.send('❌ Not connected. Use `spotify login`.')
            return
        try:
            res = sp.search(q=query, type='track', limit=1)
            items = res.get('tracks', {}).get('items', [])
            if not items:
                await ctx.send(f"❌ No results for '{query}'.")
                return
            sp.add_to_queue(items[0]['uri'])
            await ctx.send(f"➕ Queued: {items[0]['name']}")
        except Exception as e:
            await ctx.send(f'❌ Queue failed: {e}')

    @commands.command(name='spotify_repeat')
    async def repeat(self, ctx: commands.Context, *, mode: str = '') -> None:
        sp = self._get_client(ctx.author.id)
        if not sp:
            await ctx.send('❌ Not connected. Use `spotify login`.')
            return
        try:
            mode = (mode or '').lower()
            if mode not in ('off', 'track', 'context'):
                # toggle cycle off -> track -> context
                current = sp.current_playback() or {}
                cur = (current.get('repeat_state') or 'off')
                mode = 'track' if cur == 'off' else ('context' if cur == 'track' else 'off')
            sp.repeat(mode)
            await ctx.send(f'🔁 Repeat set to {mode}.')
        except Exception as e:
            await ctx.send(f'❌ Repeat failed: {e}')

    @commands.command(name='spotify_shuffle')
    async def shuffle(self, ctx: commands.Context, *, state: str = '') -> None:
        sp = self._get_client(ctx.author.id)
        if not sp:
            await ctx.send('❌ Not connected. Use `spotify login`.')
            return
        try:
            val = None
            if state:
                s = state.lower()
                if s in ('on', 'true', '1', 'yes'):
                    val = True
                elif s in ('off', 'false', '0', 'no'):
                    val = False
            if val is None:
                current = sp.current_playback() or {}
                val = not bool(current.get('shuffle_state'))
            sp.shuffle(val)
            await ctx.send(f"🔀 Shuffle {'on' if val else 'off'}.")
        except Exception as e:
            await ctx.send(f'❌ Shuffle failed: {e}')

    @commands.command(name='spotify_volume')
    async def volume(self, ctx: commands.Context, *, volume: Optional[int] = None) -> None:
        sp = self._get_client(ctx.author.id)
        if not sp:
            await ctx.send('❌ Not connected. Use `spotify login`.')
            return
        try:
            if volume is None:
                current = sp.current_playback() or {}
                dev = (current.get('device') or {})
                await ctx.send(f"🔊 Volume: {dev.get('volume_percent', 'N/A')}%")
                return
            if not 0 <= volume <= 100:
                await ctx.send('❌ Volume must be 0-100.')
                return
            sp.volume(volume)
            await ctx.send(f'🔊 Volume set to {volume}%.')
        except Exception as e:
            await ctx.send(f'❌ Volume failed: {e}')

    @commands.command(name='spotify_device')
    async def device_list(self, ctx: commands.Context) -> None:
        sp = self._get_client(ctx.author.id)
        if not sp:
            await ctx.send('❌ Not connected. Use `spotify login`.')
            return
        try:
            devices = sp.devices().get('devices', [])
            if not devices:
                await ctx.send('❌ No active devices found. Open Spotify on a device.')
                return
            lines = [f"- {d['name']} ({'active' if d['is_active'] else 'idle'})" for d in devices]
            await ctx.send("🖥️ Devices:\n" + '\n'.join(lines))
        except Exception as e:
            await ctx.send(f'❌ Devices failed: {e}')

    @commands.command(name='spotify_logout')
    async def logout(self, ctx: commands.Context) -> None:
        user_id = ctx.author.id
        try:
            # Remove cached file if present
            try:
                os.remove(f'.cache-{user_id}')
            except FileNotFoundError:
                pass
            if str(user_id) in self.user_tokens:
                del self.user_tokens[str(user_id)]
                save_tokens(self.user_tokens)
            await ctx.send('🔌 Disconnected your Spotify.')
        except Exception as e:
            await ctx.send(f'❌ Logout failed: {e}')


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SpotifyCog(bot))
