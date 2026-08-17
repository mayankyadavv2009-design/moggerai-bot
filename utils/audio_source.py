import discord
import yt_dlp
import asyncio
import re
import requests
from typing import Dict, Any, Optional, List
from config import FFMPEG_BEFORE_OPTIONS, AUDIO_FILTERS

PRIMARY_YTDL_OPTIONS = {
    'format': 'bestaudio/18/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch5',
    'source_address': '0.0.0.0',
    'extract_flat': False,
    'socket_timeout': 15,
    'extractor_args': {
        'youtube': {
            'player_client': ['tv_embedded', 'ios', 'android', 'web'],
            'player_skip': ['configs', 'webpage']
        }
    }
}

FALLBACK_IOS_OPTIONS = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch5',
    'socket_timeout': 15,
    'extractor_args': {
        'youtube': {
            'player_client': ['ios', 'tv_embedded', 'web'],
            'player_skip': ['configs']
        }
    }
}

ytdl_primary = yt_dlp.YoutubeDL(PRIMARY_YTDL_OPTIONS)
ytdl_fallback = yt_dlp.YoutubeDL(FALLBACK_IOS_OPTIONS)
YTDL_FORMAT_OPTIONS = PRIMARY_YTDL_OPTIONS


def clean_metadata_title(title: str) -> str:
    """Clean track title from YouTube tags for pristine display"""
    if not title:
        return "Unknown Track"
    t = title
    t = re.sub(r'\(Official\s*(Music\s*)?Video\)', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\[Official\s*(Music\s*)?Video\]', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\(Official\s*Audio\)', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\[Official\s*Audio\]', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\(Lyric\s*Video\)', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\[Lyric\s*Video\]', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\(Lyrics?\)', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\[Lyrics?\]', '', t, flags=re.IGNORECASE)
    t = re.sub(r'[\(\[]\s*HD\s*[\)\]]', '', t, flags=re.IGNORECASE)
    t = re.sub(r'[\(\[]\s*4K\s*[\)\]]', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\|\s*Official\s*Video', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s+', ' ', t)
    return t.strip()


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source: discord.AudioSource, *, data: Dict[str, Any], volume: float = 0.8, filter_name: str = "normal"):
        super().__init__(source, volume)
        self.data = data
        self.title = clean_metadata_title(data.get('title', 'Unknown Title'))
        self.url = data.get('webpage_url') or data.get('url') or ''
        self.stream_url = data.get('url')
        self.duration = data.get('duration', 0)
        self.thumbnail = data.get('thumbnail', '')
        self.uploader = data.get('uploader', 'Unknown Artist').replace(' - Topic', '')
        self.filter_name = filter_name

    @classmethod
    async def create_source(
        cls,
        search: str,
        *,
        loop: asyncio.AbstractEventLoop = None,
        volume: float = 0.8,
        filter_name: str = "normal"
    ) -> Optional[Dict[str, Any]]:
        """Multi-client failover extraction engine with candidate filtering for 100% resilient audio streaming"""
        loop = loop or asyncio.get_event_loop()
        
        # Resolve Spotify URLs
        if "open.spotify.com/track/" in search:
            search = await cls._resolve_spotify_track(search)
        
        is_direct = search.startswith("http://") or search.startswith("https://")
        query = search if is_direct else (search if search.startswith("ytsearch") else f"ytsearch5:{search}")

        def _pick_valid_entry(res_data):
            if not res_data:
                return None
            if 'entries' in res_data and res_data['entries']:
                for entry in res_data['entries']:
                    if entry and entry.get('url'):
                        entry['title'] = clean_metadata_title(entry.get('title', ''))
                        return entry
            elif res_data.get('url'):
                res_data['title'] = clean_metadata_title(res_data.get('title', ''))
                return res_data
            return None

        # Attempt 1: Primary TV / iOS / Android Multi-Client
        try:
            raw_data = await loop.run_in_executor(None, lambda: ytdl_primary.extract_info(query, download=False))
            valid = _pick_valid_entry(raw_data)
            if valid:
                return valid
        except Exception as e1:
            print(f"[YTDL PRIMARY] Attempt 1 failed for '{query}': {e1}")

        # Attempt 2: Fallback iOS/Web Multi-Client
        try:
            raw_data = await loop.run_in_executor(None, lambda: ytdl_fallback.extract_info(query, download=False))
            valid = _pick_valid_entry(raw_data)
            if valid:
                return valid
        except Exception as e2:
            print(f"[YTDL FALLBACK] Attempt 2 failed for '{query}': {e2}")

        # Attempt 3: Direct URL to search fallback
        if is_direct:
            try:
                clean_query = f"ytsearch5:{search.split('/')[-1].replace('watch?v=', '')}"
                raw_data = await loop.run_in_executor(None, lambda: ytdl_primary.extract_info(clean_query, download=False))
                valid = _pick_valid_entry(raw_data)
                if valid:
                    return valid
            except Exception:
                pass

        return None

    @classmethod
    def build_ffmpeg_source(cls, data: Dict[str, Any], volume: float = 0.8, filter_name: str = "normal", seek_seconds: int = 0) -> 'YTDLSource':
        stream_url = data.get('url')
        
        before_opts = FFMPEG_BEFORE_OPTIONS
        if seek_seconds > 0:
            before_opts = f"-ss {seek_seconds} " + FFMPEG_BEFORE_OPTIONS

        options_list = []
        filter_str = AUDIO_FILTERS.get(filter_name, "")
        if filter_str:
            options_list.append(f'-af "{filter_str}"')

        options_str = " ".join(options_list)
        
        ffmpeg_source = discord.FFmpegPCMAudio(
            stream_url,
            before_options=before_opts,
            options=options_str
        )
        
        return cls(ffmpeg_source, data=data, volume=volume, filter_name=filter_name)

    @staticmethod
    async def fetch_playlist_tracks(url: str, loop: asyncio.AbstractEventLoop = None) -> List[Dict[str, Any]]:
        loop = loop or asyncio.get_event_loop()
        playlist_opts = dict(PRIMARY_YTDL_OPTIONS)
        playlist_opts['noplaylist'] = False
        playlist_opts['extract_flat'] = 'in_playlist'

        def _extract():
            with yt_dlp.YoutubeDL(playlist_opts) as ydl:
                return ydl.extract_info(url, download=False)

        try:
            data = await loop.run_in_executor(None, _extract)
            tracks = []
            if data and 'entries' in data:
                for entry in data['entries']:
                    if entry:
                        t_id = entry.get('id')
                        t_url = entry.get('url') or entry.get('webpage_url') or (f"https://www.youtube.com/watch?v={t_id}" if t_id else '')
                        tracks.append({
                            'title': clean_metadata_title(entry.get('title', 'Unknown Track')),
                            'url': t_url,
                            'duration': entry.get('duration', 0),
                            'uploader': entry.get('uploader', 'Unknown Artist').replace(' - Topic', ''),
                            'thumbnail': entry.get('thumbnail', '')
                        })
            return tracks
        except Exception as e:
            print(f"[PLAYLIST EXTRACT ERROR] {e}")
            return []

    @staticmethod
    async def _resolve_spotify_track(url: str) -> str:
        try:
            oembed_url = f"https://open.spotify.com/oembed?url={url}"
            resp = requests.get(oembed_url, timeout=5).json()
            title = resp.get("title", "")
            return title if title else url
        except Exception:
            return url
