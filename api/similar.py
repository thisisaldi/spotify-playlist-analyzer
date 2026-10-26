"""GET /api/similar?url=<spotify track URL>&limit=10 -> tracks with the closest listening feel.

Content-based, not collaborative: ReccoBeats recommendations only supply a candidate
pool, which is re-ranked purely by audio-feature distance to the seed track. A second
round seeds from the closest matches to pull the pool further toward the seed's vibe.
"""
import math
import os
import sys
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _lib import FEATURES, LABELS, ApiError, analyze_audio, cover_url, get_entity, get_features, make_handler, parse_id, query, recco, spotify_id

# How much each dimension shapes the "feel". Valence/energy dominate perceived mood.
WEIGHTS = {
    "energy": 1.5, "valence": 1.5, "danceability": 1.0, "acousticness": 1.0,
    "instrumentalness": 0.75, "speechiness": 0.75, "liveness": 0.25, "tempo": 1.0, "loudness": 0.5,
}
MAX_SEEDS = 5  # ReccoBeats limit


def tempo_gap(a, b):
    # 70 BPM and 140 BPM feel alike (half-time), so compare against the closest octave
    return min(abs(a - b), abs(a * 2 - b), abs(a - b * 2)) / 60


def similarity(a, b):
    """0..1, 1 = identical feel."""
    diffs = {k: a[k] - b[k] for k in WEIGHTS if k not in ("tempo", "loudness")}
    diffs["tempo"] = tempo_gap(a["tempo"], b["tempo"])
    diffs["loudness"] = (a["loudness"] - b["loudness"]) / 15
    dist = sum(WEIGHTS[k] * min(abs(d), 1) ** 2 for k, d in diffs.items()) / sum(WEIGHTS.values())
    return 1 - math.sqrt(dist)


def artist_seeds(entity, seed_features, exclude):
    """Seed candidates from the artist's own catalog when ReccoBeats doesn't know the track."""
    artist = (entity.get("artists") or [{}])[0]
    found = recco("/artist/search?size=5&searchText=" + quote(artist.get("name", ""))).get("content", [])
    match = next((a for a in found if spotify_id(a.get("href")) == spotify_id(artist.get("uri"))), None)
    if not match:
        return []
    ids = [spotify_id(t["href"]) for t in recco(f"/artist/{match['id']}/track?size=50").get("content", [])]
    feats = get_features([i for i in ids if i not in exclude])
    return sorted(feats, key=lambda i: -similarity(seed_features, feats[i]))[:MAX_SEEDS]


def candidates(seeds):
    return recco("/track/recommendation?size=100&seeds=" + ",".join(seeds)).get("content", [])


def similar(url, limit):
    _, tid = parse_id(url, ("track",))
    entity = get_entity("track", tid)
    seed_features = get_features([tid]).get(tid)
    if seed_features:
        seeds = [tid]
    else:
        preview = (entity.get("audioPreview") or {}).get("url")
        if not preview:
            raise ApiError(422, "No audio data available for this track")
        seed_features = analyze_audio(preview)
        seeds = artist_seeds(entity, seed_features, {tid})
        if not seeds:
            raise ApiError(422, "Not enough data to find similar tracks for this one yet")

    seed_title = (entity.get("name") or "").lower()
    pool, features = {}, {}
    for _ in range(2):
        for t in candidates(seeds):
            pool.setdefault(spotify_id(t["href"]), t)
        features.update(get_features([i for i in pool if i not in features]))
        ranked = sorted((i for i in features if i != tid), key=lambda i: -similarity(seed_features, features[i]))
        seeds = ranked[:MAX_SEEDS] or seeds

    results, seen = [], {seed_title}
    for i in ranked:
        t = pool[i]
        artists = [a["name"] for a in t.get("artists", [])]
        key = t["trackTitle"].lower()
        if key in seen:  # pool often holds re-releases / remasters of one song
            continue
        seen.add(key)
        results.append({
            "id": i,
            "title": t["trackTitle"],
            "artist": ", ".join(artists),
            "url": f"https://open.spotify.com/track/{i}",
            "similarity": round(similarity(seed_features, features[i]) * 100),
            "features": {k: features[i][k] for k in FEATURES + ["tempo"]},
        })
        if len(results) == limit:
            break

    return {
        "seed": {
            "id": tid,
            "title": entity.get("name"),
            "artist": ", ".join(a["name"] for a in entity.get("artists", [])),
            "image": cover_url(entity),
            "url": f"https://open.spotify.com/track/{tid}",
            "features": {k: seed_features[k] for k in FEATURES + ["tempo"]},
        },
        "labels": LABELS,
        "tracks": results,
    }


def run(path):
    try:
        limit = max(1, min(int(query(path, "limit", "10")), 25))
    except ValueError:
        raise ApiError(400, "limit must be a number")
    return similar(query(path, "url"), limit)


handler = make_handler(run)
