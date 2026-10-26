"""GET /api/analyze?url=<spotify playlist or album URL> -> mood profile JSON."""
import os
import sys
from statistics import mean

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _lib import EXTRA, FEATURES, LABELS, ApiError, cover_url, get_entity, get_features, make_handler, parse_id, query, spotify_id


def mood_label(valence, energy):
    if valence >= 0.5:
        return "Happy & Energetic" if energy >= 0.5 else "Chill & Content"
    return "Intense & Restless" if energy >= 0.5 else "Sad & Mellow"


def summarize(entity, features_by_id):
    tracks = []
    for t in entity.get("trackList", []):
        tid = spotify_id(t.get("uri"))
        f = features_by_id.get(tid)
        if f:
            tracks.append({"id": tid, "title": t.get("title"), "artist": t.get("subtitle"), **{k: f[k] for k in FEATURES + EXTRA}})
    if not tracks:
        raise ApiError(422, "No audio features available for these tracks")

    averages = {k: round(mean(t[k] for t in tracks), 3) for k in FEATURES + EXTRA}

    def pick(key, fn):
        t = fn(tracks, key=lambda t: t[key])
        return {"id": t["id"], "title": t["title"], "artist": t["artist"], "value": t[key]}

    return {
        "playlist": {
            "id": entity.get("id"),
            "type": entity.get("type"),
            "name": entity.get("name"),
            "owner": entity.get("subtitle"),
            "image": cover_url(entity),
            "url": f"https://open.spotify.com/{entity.get('type')}/{entity.get('id')}",
        },
        "trackCount": len(entity.get("trackList", [])),
        "analyzedCount": len(tracks),
        "mood": mood_label(averages["valence"], averages["energy"]),
        "features": [{"key": k, "label": LABELS[k], "value": averages[k]} for k in FEATURES],
        "tempo": round(averages["tempo"]),
        "loudness": averages["loudness"],
        "highlights": {
            "happiest": pick("valence", max),
            "saddest": pick("valence", min),
            "mostEnergetic": pick("energy", max),
            "mostDanceable": pick("danceability", max),
        },
        "tracks": tracks,
    }


def analyze(url):
    kind, sid = parse_id(url, ("playlist", "album"))
    entity = get_entity(kind, sid)
    ids = [spotify_id(t["uri"]) for t in entity.get("trackList", []) if (t.get("uri") or "").startswith("spotify:track:")]
    if not ids:
        raise ApiError(422, "This playlist has no tracks")
    return summarize(entity, get_features(ids))


handler = make_handler(lambda path: analyze(query(path, "url")))
