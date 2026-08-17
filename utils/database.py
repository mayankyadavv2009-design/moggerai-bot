import sqlite3
import os
from typing import List, Dict, Optional, Any

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "resonance.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Server Settings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS server_settings (
        guild_id INTEGER PRIMARY KEY,
        volume REAL DEFAULT 0.8,
        active_filter TEXT DEFAULT 'normal',
        dj_role_id INTEGER DEFAULT 0,
        dj_only INTEGER DEFAULT 0,
        autoplay INTEGER DEFAULT 1,
        autoplay_mode TEXT DEFAULT 'smart',
        stay_247 INTEGER DEFAULT 0
    )
    """)

    # Playlists Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS playlists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER,
        user_id INTEGER,
        name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(guild_id, user_id, name)
    )
    """)

    # Playlist Tracks Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS playlist_tracks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        playlist_id INTEGER,
        title TEXT,
        url TEXT,
        duration INTEGER,
        thumbnail TEXT,
        FOREIGN KEY(playlist_id) REFERENCES playlists(id) ON DELETE CASCADE
    )
    """)

    # User Listening History Table (Tracks user music taste & play count)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_listening_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER,
        user_id INTEGER,
        user_name TEXT,
        title TEXT,
        artist TEXT,
        url TEXT,
        duration INTEGER DEFAULT 0,
        thumbnail TEXT DEFAULT '',
        played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Song Transition Intelligence (Markov Chain: What songs users play most after song X)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS song_transitions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER,
        from_title TEXT,
        from_artist TEXT,
        to_title TEXT,
        to_artist TEXT,
        to_url TEXT,
        to_duration INTEGER DEFAULT 0,
        to_thumbnail TEXT DEFAULT '',
        transition_count INTEGER DEFAULT 1,
        last_transition TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(guild_id, from_title, to_title)
    )
    """)

    # Attempt migration if autoplay_mode column missing
    try:
        cursor.execute("ALTER TABLE server_settings ADD COLUMN autoplay_mode TEXT DEFAULT 'smart'")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


class Database:
    @staticmethod
    def get_guild_setting(guild_id: int, key: str, default: Any = None) -> Any:
        init_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT {key} FROM server_settings WHERE guild_id = ?", (guild_id,))
            row = cursor.fetchone()
            return row[0] if row else default
        except Exception:
            return default
        finally:
            conn.close()

    @staticmethod
    def update_guild_setting(guild_id: int, key: str, value: Any):
        init_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute(f"""
            INSERT INTO server_settings (guild_id, {key}) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET {key} = ?
            """, (guild_id, value, value))
            conn.commit()
        finally:
            conn.close()

    # ------------------- Playlists -------------------
    @staticmethod
    def save_playlist(guild_id: int, user_id: int, name: str, tracks: List[Dict[str, Any]]) -> bool:
        init_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("""
            INSERT INTO playlists (guild_id, user_id, name) VALUES (?, ?, ?)
            ON CONFLICT(guild_id, user_id, name) DO UPDATE SET created_at = CURRENT_TIMESTAMP
            """, (guild_id, user_id, name))

            cursor.execute("SELECT id FROM playlists WHERE guild_id = ? AND user_id = ? AND name = ?",
                           (guild_id, user_id, name))
            playlist_id = cursor.fetchone()[0]

            cursor.execute("DELETE FROM playlist_tracks WHERE playlist_id = ?", (playlist_id,))

            for t in tracks:
                cursor.execute("""
                INSERT INTO playlist_tracks (playlist_id, title, url, duration, thumbnail)
                VALUES (?, ?, ?, ?, ?)
                """, (playlist_id, t.get("title", "Unknown"), t.get("url", ""), t.get("duration", 0), t.get("thumbnail", "")))

            conn.commit()
            return True
        except Exception as e:
            print(f"[DB ERROR] Failed to save playlist: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def get_user_playlists(guild_id: int, user_id: int) -> List[str]:
        init_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT name FROM playlists WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            rows = cursor.fetchall()
            return [r[0] for r in rows]
        finally:
            conn.close()

    @staticmethod
    def load_playlist(guild_id: int, user_id: int, name: str) -> List[Dict[str, Any]]:
        init_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("""
            SELECT pt.title, pt.url, pt.duration, pt.thumbnail 
            FROM playlist_tracks pt
            JOIN playlists p ON pt.playlist_id = p.id
            WHERE p.guild_id = ? AND p.user_id = ? AND p.name = ?
            """, (guild_id, user_id, name))
            rows = cursor.fetchall()
            return [{"title": r[0], "url": r[1], "duration": r[2], "thumbnail": r[3]} for r in rows]
        finally:
            conn.close()

    @staticmethod
    def delete_playlist(guild_id: int, user_id: int, name: str) -> bool:
        init_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM playlists WHERE guild_id = ? AND user_id = ? AND name = ?", (guild_id, user_id, name))
            affected = cursor.rowcount
            conn.commit()
            return affected > 0
        finally:
            conn.close()

    # ------------------- Listening History & User Taste -------------------
    @staticmethod
    def record_real_listen(guild_id: int, user_id: int, user_name: str, title: str, artist: str, url: str, duration_sec: int, thumbnail: str = ""):
        """Record real listener attendance and exact listened seconds"""
        if not title or title == "Unknown Track" or duration_sec <= 0 or not user_id:
            return
        # Cap single song max recorded to 3600 seconds
        duration_sec = min(int(duration_sec), 3600)
        init_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("""
            INSERT INTO user_listening_history (guild_id, user_id, user_name, title, artist, url, duration, thumbnail)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (guild_id, user_id, user_name, title, artist or "Unknown Artist", url, duration_sec, thumbnail))
            conn.commit()
        except Exception as e:
            print(f"[DB ERROR] record_real_listen: {e}")
        finally:
            conn.close()

    @staticmethod
    def record_play(guild_id: int, user_id: int, user_name: str, title: str, artist: str, url: str, duration: int = 0, thumbnail: str = "") -> int:
        if not title or title == "Unknown Track":
            return 0
        init_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("""
            INSERT INTO user_listening_history (guild_id, user_id, user_name, title, artist, url, duration, thumbnail)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (guild_id, user_id, user_name, title, artist or "Unknown Artist", url, duration, thumbnail))
            conn.commit()
            return cursor.lastrowid or 0
        except Exception as e:
            print(f"[DB ERROR] record_play: {e}")
            return 0
        finally:
            conn.close()

    @staticmethod
    def update_play_duration(history_id: int, actual_listened_sec: int):
        if not history_id or actual_listened_sec <= 0:
            return
        # Cap max recorded per single song track to 1 hour to prevent runaway timer bugs
        actual_listened_sec = min(int(actual_listened_sec), 3600)
        init_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("""
            UPDATE user_listening_history
            SET duration = ?
            WHERE id = ?
            """, (actual_listened_sec, history_id))
            conn.commit()
        except Exception as e:
            print(f"[DB ERROR] update_play_duration: {e}")
        finally:
            conn.close()

    @staticmethod
    def format_listen_time(total_seconds: int) -> str:
        """Format total listening seconds into clean, human-readable format (e.g. '2 hrs 14 mins')"""
        if not total_seconds or total_seconds <= 0:
            return "0 mins"
        total_seconds = int(total_seconds)
        hrs = total_seconds // 3600
        rem = total_seconds % 3600
        mins = rem // 60
        secs = rem % 60

        if hrs > 0:
            if mins > 0:
                return f"{hrs} hr{'s' if hrs > 1 else ''} {mins} min{'s' if mins != 1 else ''}"
            return f"{hrs} hr{'s' if hrs > 1 else ''}"
        elif mins > 0:
            if secs > 0 and mins < 10:
                return f"{mins} min{'s' if mins != 1 else ''} {secs} sec{'s' if secs != 1 else ''}"
            return f"{mins} min{'s' if mins != 1 else ''}"
        else:
            return f"{secs} sec{'s' if secs != 1 else ''}"

    @staticmethod
    def record_transition(guild_id: int, from_track: Dict[str, Any], to_track: Dict[str, Any]):
        if not from_track or not to_track:
            return
        from_title = from_track.get('title', '').strip()
        to_title = to_track.get('title', '').strip()
        if not from_title or not to_title or from_title == to_title:
            return

        from_artist = from_track.get('uploader', 'Unknown Artist')
        to_artist = to_track.get('uploader', 'Unknown Artist')
        to_url = to_track.get('webpage_url') or to_track.get('url') or ''
        to_duration = to_track.get('duration', 0)
        to_thumbnail = to_track.get('thumbnail', '')

        init_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("""
            INSERT INTO song_transitions (guild_id, from_title, from_artist, to_title, to_artist, to_url, to_duration, to_thumbnail, transition_count, last_transition)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(guild_id, from_title, to_title) DO UPDATE SET
                transition_count = transition_count + 1,
                last_transition = CURRENT_TIMESTAMP,
                to_url = excluded.to_url,
                to_duration = excluded.to_duration,
                to_thumbnail = excluded.to_thumbnail
            """, (guild_id, from_title, from_artist, to_title, to_artist, to_url, to_duration, to_thumbnail))
            conn.commit()
        except Exception as e:
            print(f"[DB ERROR] record_transition: {e}")
        finally:
            conn.close()

    @staticmethod
    def get_top_successor_track(guild_id: int, from_title: str, exclude_urls: List[str] = None) -> Optional[Dict[str, Any]]:
        if not from_title:
            return None
        exclude_urls = exclude_urls or []
        init_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("""
            SELECT to_title, to_artist, to_url, to_duration, to_thumbnail, transition_count
            FROM song_transitions
            WHERE guild_id = ? AND from_title = ?
            ORDER BY transition_count DESC, last_transition DESC
            LIMIT 10
            """, (guild_id, from_title))
            rows = cursor.fetchall()
            for r in rows:
                if r[2] and r[2] not in exclude_urls:
                    return {
                        "title": r[0],
                        "uploader": r[1],
                        "url": r[2],
                        "duration": r[3],
                        "thumbnail": r[4],
                        "transition_count": r[5]
                    }
            return None
        except Exception as e:
            print(f"[DB ERROR] get_top_successor_track: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def get_active_listeners_taste(guild_id: int, user_ids: List[int], limit: int = 10) -> Dict[str, Any]:
        if not user_ids:
            return {"top_artists": [], "top_tracks": []}
        init_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            placeholders = ",".join("?" for _ in user_ids)
            
            # Top artists among listeners
            cursor.execute(f"""
            SELECT artist, COUNT(*) as play_count
            FROM user_listening_history
            WHERE user_id IN ({placeholders}) AND artist != 'Unknown Artist' AND artist != ''
            GROUP BY artist
            ORDER BY play_count DESC
            LIMIT ?
            """, user_ids + [limit])
            top_artists = [{"artist": r[0], "count": r[1]} for r in cursor.fetchall()]

            # Top tracks among listeners
            cursor.execute(f"""
            SELECT title, artist, url, duration, thumbnail, COUNT(*) as play_count
            FROM user_listening_history
            WHERE user_id IN ({placeholders}) AND title != 'Unknown Track'
            GROUP BY title, artist
            ORDER BY play_count DESC
            LIMIT ?
            """, user_ids + [limit])
            top_tracks = [{
                "title": r[0],
                "uploader": r[1],
                "url": r[2],
                "duration": r[3],
                "thumbnail": r[4],
                "play_count": r[5]
            } for r in cursor.fetchall()]

            return {
                "top_artists": top_artists,
                "top_tracks": top_tracks
            }
        except Exception as e:
            print(f"[DB ERROR] get_active_listeners_taste: {e}")
            return {"top_artists": [], "top_tracks": []}
        finally:
            conn.close()

    @staticmethod
    def get_user_taste_profile(guild_id: int, user_id: int) -> Dict[str, Any]:
        init_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            where_sql = "WHERE user_id = ?"
            params = [user_id]
            if guild_id:
                where_sql += " AND guild_id = ?"
                params.append(guild_id)

            # Total plays and actual listened seconds
            cursor.execute(f"SELECT COUNT(*), SUM(duration) FROM user_listening_history {where_sql}", tuple(params))
            total_plays_row = cursor.fetchone()
            total_plays = total_plays_row[0] or 0
            total_duration_sec = total_plays_row[1] or 0

            # Top 5 artists
            cursor.execute(f"""
            SELECT artist, COUNT(*) as c
            FROM user_listening_history
            {where_sql} AND artist != 'Unknown Artist' AND artist != ''
            GROUP BY artist
            ORDER BY c DESC
            LIMIT 5
            """, tuple(params))
            top_artists = [{"artist": r[0], "count": r[1]} for r in cursor.fetchall()]

            # Top 5 songs
            cursor.execute(f"""
            SELECT title, artist, url, thumbnail, COUNT(*) as c
            FROM user_listening_history
            {where_sql} AND title != 'Unknown Track'
            GROUP BY title, artist
            ORDER BY c DESC
            LIMIT 5
            """, tuple(params))
            top_songs = [{"title": r[0], "artist": r[1], "url": r[2], "thumbnail": r[3], "count": r[4]} for r in cursor.fetchall()]

            # Recently played
            cursor.execute(f"""
            SELECT title, artist, url, thumbnail, played_at
            FROM user_listening_history
            {where_sql}
            ORDER BY played_at DESC
            LIMIT 5
            """, tuple(params))
            recent = [{"title": r[0], "artist": r[1], "url": r[2], "thumbnail": r[3], "played_at": r[4]} for r in cursor.fetchall()]

            return {
                "user_id": user_id,
                "total_plays": total_plays,
                "total_duration_sec": total_duration_sec,
                "formatted_total_time": Database.format_listen_time(total_duration_sec),
                "top_artists": top_artists,
                "top_songs": top_songs,
                "recent": recent
            }
        except Exception as e:
            print(f"[DB ERROR] get_user_taste_profile: {e}")
            return {
                "user_id": user_id,
                "total_plays": 0,
                "total_duration_sec": 0,
                "formatted_total_time": "0 mins",
                "top_artists": [],
                "top_songs": [],
                "recent": []
            }
        finally:
            conn.close()
