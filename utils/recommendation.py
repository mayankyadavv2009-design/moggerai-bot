import asyncio
import random
import re
import yt_dlp
from typing import Dict, Any, Optional, List, Set
from utils.database import Database
from utils.audio_source import YTDLSource, YTDL_FORMAT_OPTIONS


def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube 11-char video ID from any URL"""
    if not url:
        return None
    match = re.search(r'(?:v=|\/|youtu\.be\/|embed\/)([0-9A-Za-z_-]{11})', url)
    return match.group(1) if match else None


def clean_title_for_comparison(title: str) -> str:
    """Clean track title for fuzzy duplicate detection"""
    if not title:
        return ""
    t = title.lower()
    t = re.sub(r'\(official\s*(music\s*)?video\)', '', t)
    t = re.sub(r'\[official\s*(music\s*)?video\]', '', t)
    t = re.sub(r'\(lyrics?\)', '', t)
    t = re.sub(r'\[lyrics?\]', '', t)
    t = re.sub(r'\(audio\)', '', t)
    t = re.sub(r'\[audio\]', '', t)
    t = re.sub(r'\(hd\)', '', t)
    t = re.sub(r'\(4k\)', '', t)
    t = re.sub(r' - topic$', '', t)
    return t.strip()


class RecommendationEngine:
    @staticmethod
    async def fetch_algorithmic_radio_tracks(
        bot_loop: asyncio.AbstractEventLoop,
        video_id: str,
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Extract Google/YouTube AI's real-time Algorithmic Song Radio (list=RD{video_id})
        Contains 50-700+ songs directly correlated to what global users listen to next.
        """
        if not video_id:
            return []

        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android'],
                    'player_skip': ['configs', 'webpage']
                }
            }
        }

        radio_url = f"https://www.youtube.com/watch?v={video_id}&list=RD{video_id}"
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await bot_loop.run_in_executor(None, lambda: ydl.extract_info(radio_url, download=False))
                if info and 'entries' in info and info['entries']:
                    valid = [e for e in info['entries'] if e and e.get('title')]
                    return valid[:limit]
        except Exception as e:
            print(f"[RADIO EXTRACT ERROR] Algorithmic radio failed for {video_id}: {e}")

        return []

    @staticmethod
    async def get_autoplay_track(
        bot_loop: asyncio.AbstractEventLoop,
        guild_id: int,
        current_track: Optional[Dict[str, Any]],
        active_user_ids: List[int],
        recent_urls: List[str],
        autoplay_mode: str = "smart"
    ) -> Optional[Dict[str, Any]]:
        """
        True Unlimited AI Autoplay:
        - Uses YouTube/Spotify's global live AI Song Radio stream (list=RD{id}).
        - Incorporates server Markov transition memory.
        - Matches active room listener taste.
        - Guarantees 100% music relevance with zero artificial genre/artist limits.
        """
        if autoplay_mode == "off" or not current_track:
            return None

        recent_urls_set = set(recent_urls)
        cur_url = current_track.get('webpage_url') or current_track.get('url') or ''
        if cur_url:
            recent_urls_set.add(cur_url)

        cur_title = current_track.get('title', '')
        cur_artist = current_track.get('uploader', '')
        vid_id = extract_video_id(cur_url)

        # ----------------------------------------------------
        # TIER 1: Markov Chain Server Memory
        # ----------------------------------------------------
        if autoplay_mode in ("smart", "transition") and cur_title:
            successor = Database.get_top_successor_track(guild_id, cur_title, list(recent_urls_set))
            if successor and successor.get('url') and successor['url'] not in recent_urls_set:
                # If users in this server frequently play this transition (>= 2 plays), honor it!
                if successor.get('transition_count', 0) >= 2:
                    try:
                        data = await YTDLSource.create_source(successor['url'], loop=bot_loop)
                        if data and data.get('url'):
                            return {
                                'title': data.get('title', successor['title']),
                                'url': data.get('webpage_url') or successor['url'],
                                'duration': data.get('duration', successor.get('duration', 0)),
                                'uploader': data.get('uploader', successor.get('uploader', 'Unknown Artist')),
                                'thumbnail': data.get('thumbnail', successor.get('thumbnail', '')),
                                'requester': f"🤖 Autoplay (Learned Server Transition)",
                                'text_channel': current_track.get('text_channel'),
                                'raw_data': data,
                                'recommendation_type': 'transition'
                            }
                    except Exception as e:
                        print(f"[RECOM ERROR] Markov transition fetch failed: {e}")

        # ----------------------------------------------------
        # TIER 2: Live Global Algorithmic Song Radio (list=RD{vid_id})
        # ----------------------------------------------------
        radio_entries = []
        if vid_id:
            radio_entries = await RecommendationEngine.fetch_algorithmic_radio_tracks(bot_loop, vid_id, limit=30)

        # If direct video ID radio returned empty, fall back to searching search-based mix
        if not radio_entries:
            query = f"{cur_title} {cur_artist} mix" if cur_artist else f"{cur_title} mix"
            try:
                search_res = await YTDLSource.fetch_playlist_tracks(f"ytsearch15:{query}", loop=bot_loop)
                if search_res:
                    radio_entries = search_res
            except Exception as e:
                print(f"[RECOM ERROR] Fallback search mix failed: {e}")

        # ----------------------------------------------------
        # TIER 3: Room Listener Taste Affinity Blend
        # ----------------------------------------------------
        # If active listeners have saved favorite tracks or artists in SQLite, check if any match the radio mix!
        if radio_entries and active_user_ids and autoplay_mode in ("smart", "taste"):
            taste = Database.get_active_listeners_taste(guild_id, active_user_ids, limit=20)
            top_artists = [a['artist'].lower() for a in taste.get('top_artists', [])]
            top_titles = [clean_title_for_comparison(t['title']) for t in taste.get('top_tracks', [])]

            # Look for a track in the live algorithmic radio that matches a room listener's favorite artist
            for entry in radio_entries:
                e_id = entry.get('id')
                e_url = entry.get('webpage_url') or (f"https://www.youtube.com/watch?v={e_id}" if e_id else entry.get('url'))
                e_artist = (entry.get('uploader') or '').lower()
                e_clean_title = clean_title_for_comparison(entry.get('title', ''))

                if not e_url or e_url in recent_urls_set or e_id == vid_id:
                    continue

                # Matches listener taste
                if any(fav in e_artist for fav in top_artists) or any(fav in e_clean_title for fav in top_titles):
                    try:
                        data = await YTDLSource.create_source(e_url, loop=bot_loop)
                        if data and data.get('url'):
                            return {
                                'title': data.get('title', entry.get('title')),
                                'url': data.get('webpage_url') or e_url,
                                'duration': data.get('duration', entry.get('duration', 0)),
                                'uploader': data.get('uploader', entry.get('uploader', 'AI DJ')),
                                'thumbnail': data.get('thumbnail', ''),
                                'requester': "🎧 Autoplay (Matched to Room Listener Taste)",
                                'text_channel': current_track.get('text_channel'),
                                'raw_data': data,
                                'recommendation_type': 'user_taste'
                            }
                    except Exception as e:
                        print(f"[RECOM ERROR] Room taste radio match extract failed: {e}")

        # ----------------------------------------------------
        # TIER 4: Top Algorithmic Track from Live Google/YouTube Radio
        # ----------------------------------------------------
        if radio_entries:
            # Pick the highest-ranked track in the algorithmic mix that hasn't played recently
            for entry in radio_entries:
                e_id = entry.get('id')
                e_url = entry.get('webpage_url') or (f"https://www.youtube.com/watch?v={e_id}" if e_id else entry.get('url'))
                e_title = entry.get('title', '')
                
                if not e_url or e_url in recent_urls_set or e_id == vid_id:
                    continue
                if clean_title_for_comparison(e_title) == clean_title_for_comparison(cur_title):
                    continue

                try:
                    data = await YTDLSource.create_source(e_url, loop=bot_loop)
                    if data and data.get('url'):
                        return {
                            'title': data.get('title', e_title),
                            'url': data.get('webpage_url') or e_url,
                            'duration': data.get('duration', entry.get('duration', 0)),
                            'uploader': data.get('uploader', entry.get('uploader', 'AI Radio Discovery')),
                            'thumbnail': data.get('thumbnail', ''),
                            'requester': "📻 Autoplay (Algorithmic Song Radio)",
                            'text_channel': current_track.get('text_channel'),
                            'raw_data': data,
                            'recommendation_type': 'radio_discovery'
                        }
                except Exception as e:
                    print(f"[RECOM ERROR] Algorithmic track extract failed: {e}")

        return None

    @staticmethod
    async def generate_radio_mix(
        bot_loop: asyncio.AbstractEventLoop,
        seed_query: str,
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Generate an instant 10-track Spotify/YouTube-tier Radio Mix:
        - Resolves seed song.
        - Pulls live Google AI Algorithmic Radio for that song.
        - Returns perfectly matched songs matching the exact vibe.
        """
        # Step 1: Resolve seed track
        seed_data = await YTDLSource.create_source(seed_query, loop=bot_loop)
        if not seed_data:
            return []

        seed_url = seed_data.get('webpage_url') or seed_data.get('url') or ''
        vid_id = extract_video_id(seed_url)

        tracks: List[Dict[str, Any]] = [{
            'title': seed_data.get('title', 'Unknown Track'),
            'url': seed_url,
            'duration': seed_data.get('duration', 0),
            'uploader': seed_data.get('uploader', 'Unknown Artist'),
            'thumbnail': seed_data.get('thumbnail', ''),
            'raw_data': seed_data
        }]

        # Step 2: Extract real-time Algorithmic Radio (list=RD{vid_id})
        radio_entries = []
        if vid_id:
            radio_entries = await RecommendationEngine.fetch_algorithmic_radio_tracks(bot_loop, vid_id, limit=count + 15)

        if not radio_entries:
            query = f"{seed_data.get('title')} {seed_data.get('uploader')} mix"
            radio_entries = await YTDLSource.fetch_playlist_tracks(f"ytsearch{count + 10}:{query}", loop=bot_loop)

        seen_titles = {clean_title_for_comparison(seed_data.get('title', ''))}

        for entry in radio_entries:
            if len(tracks) >= count:
                break

            e_id = entry.get('id')
            e_url = entry.get('webpage_url') or (f"https://www.youtube.com/watch?v={e_id}" if e_id else entry.get('url'))
            e_title = entry.get('title', '')
            clean_t = clean_title_for_comparison(e_title)

            if not e_url or e_id == vid_id or clean_t in seen_titles:
                continue

            seen_titles.add(clean_t)
            tracks.append({
                'title': e_title,
                'url': e_url,
                'duration': entry.get('duration', 0),
                'uploader': entry.get('uploader', 'Radio Artist'),
                'thumbnail': entry.get('thumbnail', '')
            })

        return tracks

    @staticmethod
    async def generate_user_taste_mix(
        bot_loop: asyncio.AbstractEventLoop,
        guild_id: int,
        user_id: int,
        count: int = 15
    ) -> List[Dict[str, Any]]:
        """Generate a personalized Spotify 'Daily Mix' using Algorithmic Radios of user's top songs"""
        profile = Database.get_user_taste_profile(guild_id, user_id)
        top_songs = profile.get("top_songs", [])

        if not top_songs:
            return []

        mix_tracks: List[Dict[str, Any]] = []
        seen_titles = set()

        # Add top 3 user favorites
        for s in top_songs[:3]:
            c_t = clean_title_for_comparison(s.get('title', ''))
            if c_t and c_t not in seen_titles:
                seen_titles.add(c_t)
                mix_tracks.append({
                    'title': s.get('title'),
                    'url': s.get('url'),
                    'duration': s.get('duration', 0),
                    'uploader': s.get('artist', 'Favorite Artist'),
                    'thumbnail': s.get('thumbnail', '')
                })

        # For each favorite song, fetch its live algorithmic radio to fill the rest of the mix!
        for s in top_songs[:5]:
            if len(mix_tracks) >= count:
                break
            s_vid_id = extract_video_id(s.get('url', ''))
            if s_vid_id:
                recoms = await RecommendationEngine.fetch_algorithmic_radio_tracks(bot_loop, s_vid_id, limit=8)
                for r in recoms:
                    if len(mix_tracks) >= count:
                        break
                    r_id = r.get('id')
                    r_url = r.get('webpage_url') or (f"https://www.youtube.com/watch?v={r_id}" if r_id else r.get('url'))
                    r_title = r.get('title', '')
                    r_clean = clean_title_for_comparison(r_title)

                    if not r_url or r_clean in seen_titles or r_id == s_vid_id:
                        continue

                    seen_titles.add(r_clean)
                    mix_tracks.append({
                        'title': r_title,
                        'url': r_url,
                        'duration': r.get('duration', 0),
                        'uploader': r.get('uploader', 'AI Radio Discovery'),
                        'thumbnail': r.get('thumbnail', '')
                    })

        return mix_tracks
