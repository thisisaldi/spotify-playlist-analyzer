"""Shared helpers for the API functions (underscore prefix: Vercel doesn't route it).

Track lists and metadata come from Spotify's public embed pages (the Web API no
longer returns playlist items to Development Mode apps); audio features and
candidate tracks come from ReccoBeats, which accepts Spotify track IDs.
"""
import json
import os
import re
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qs, urlparse

FEATURES = ["danceability", "energy", "speechiness", "acousticness", "instrumentalness", "liveness", "valence"]
EXTRA = ["tempo", "loudness"]
LABELS = {
    "danceability": "Danceable",
    "energy": "Energy Level",
    "speechiness": "Speech-like",
    "acousticness": "Acoustic Sound",
    "instrumentalness": "Instrumental Feel",
    "liveness": "Live Performance",
    "valence": "Happiness",
}
RECCO = "https://api.reccobeats.com/v1"
RECCO_BATCH = 40
ID_RE = re.compile(r"(playlist|album|track)[/:]([A-Za-z0-9]{22})")
NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)
UA = {"User-Agent": "Mozilla/5.0 (playlist-mood-analyzer)"}


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def parse_id(url, kinds):
    m = ID_RE.search(url or "")
    if not m or m.group(1) not in kinds:
        raise ApiError(400, f"Paste a Spotify {' or '.join(kinds)} link, e.g. https://open.spotify.com/{kinds[0]}/...")
    return m.group(1), m.group(2)


def spotify_id(uri_or_href):
    return (uri_or_href or "").replace(":", "/").rstrip("/").rsplit("/", 1)[-1]


def fetch(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code in (400, 404):
            raise ApiError(404, "Not found on " + urlparse(url).netloc)
        raise ApiError(502, f"Upstream error ({e.code}) from {urlparse(url).netloc}")
    except urllib.error.URLError:
        raise ApiError(502, f"Could not reach {urlparse(url).netloc}")


def recco(path):
    return json.loads(fetch(RECCO + path))


def get_entity(kind, sid):
    # ponytail: embed page lists at most ~100 tracks; use the Web API with a user token if full playlists matter
    m = NEXT_DATA_RE.search(fetch(f"https://open.spotify.com/embed/{kind}/{sid}").decode("utf-8"))
    if not m:
        raise ApiError(502, "Spotify page format changed; could not read it")
    # unknown/private ids still render the page, just without an entity
    entity = (((json.loads(m.group(1)).get("props") or {}).get("pageProps") or {}).get("state") or {}).get("data", {}).get("entity")
    if not entity:
        raise ApiError(404, f"Spotify {kind} not found. Is it public?")
    return entity


def cover_url(entity):
    sources = (entity.get("coverArt") or {}).get("sources") or (entity.get("visualIdentity") or {}).get("image") or []
    return max(sources, key=lambda s: s.get("maxWidth") or s.get("width") or 0)["url"] if sources else None


def get_features(track_ids):
    """{spotify_id: feature row} for the ids ReccoBeats knows; unknown ids are absent."""
    chunks = [track_ids[i:i + RECCO_BATCH] for i in range(0, len(track_ids), RECCO_BATCH)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = pool.map(lambda ids: recco("/audio-features?ids=" + ",".join(ids)).get("content", []), chunks)
    # ReccoBeats returns its own id; the Spotify id is in href
    return {spotify_id(row["href"]): row for rows in results for row in rows if row.get("href")}


def analyze_audio(mp3_url):
    """Features computed by ReccoBeats from a 30s preview clip."""
    boundary = uuid.uuid4().hex
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="audioFile"; filename="preview.mp3"\r\n'
        "Content-Type: audio/mpeg\r\n\r\n"
    ).encode() + fetch(mp3_url) + f"\r\n--{boundary}--\r\n".encode()
    return json.loads(fetch(RECCO + "/analysis/audio-features", body, {"Content-Type": f"multipart/form-data; boundary={boundary}"}))


def query(path, key, default=""):
    return parse_qs(urlparse(path).query).get(key, [default])[0]


def send(h, status, body, cache=False):
    payload = b"" if body is None else json.dumps(body).encode()
    allowed = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",")]
    origin = h.headers.get("Origin", "")
    h.send_response(status)
    h.send_header("Content-Type", "application/json")
    h.send_header("Access-Control-Allow-Origin", "*" if "*" in allowed else (origin if origin in allowed else allowed[0]))
    h.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
    h.send_header("Vary", "Origin")
    # cache successful results at Vercel's CDN: repeat requests never hit upstream
    h.send_header("Cache-Control", "public, s-maxage=21600, stale-while-revalidate=86400" if cache else "no-store")
    h.send_header("Content-Length", str(len(payload)))
    h.end_headers()
    h.wfile.write(payload)


def serve(h, run):
    """Run run(path) -> dict and write it as JSON. Vercel only detects functions that define
    `class handler(BaseHTTPRequestHandler)` literally, so each endpoint file declares its own."""
    try:
        send(h, 200, run(h.path), cache=True)
    except ApiError as e:
        send(h, e.status, {"error": str(e)})
    except Exception:
        send(h, 500, {"error": "Something went wrong"})
