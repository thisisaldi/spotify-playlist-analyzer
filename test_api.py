"""Offline checks for the API logic. Run: python test_api.py"""
import sys

sys.path.insert(0, "api")
from _lib import ApiError, FEATURES, cover_url, parse_id, spotify_id
from analyze import mood_label, summarize
from similar import similarity, tempo_gap


def raises(status, fn, *args):
    try:
        fn(*args)
    except ApiError as e:
        assert e.status == status, (e.status, status)
        return
    raise AssertionError(f"{fn.__name__}{args} did not raise")


PID = "37i9dQZF1DXcBWIGoYBM5M"
LISTS = ("playlist", "album")

assert parse_id(f"https://open.spotify.com/playlist/{PID}?si=abc", LISTS) == ("playlist", PID)
assert parse_id(f"https://open.spotify.com/intl-id/playlist/{PID}/", LISTS) == ("playlist", PID)
assert parse_id(f"spotify:album:{PID}", LISTS) == ("album", PID)
assert parse_id(f"https://open.spotify.com/track/{PID}", ("track",)) == ("track", PID)
for bad in ("", "hello", f"https://open.spotify.com/track/{PID}"):
    raises(400, parse_id, bad, LISTS)

assert spotify_id("spotify:track:abc") == spotify_id("https://open.spotify.com/track/abc/") == "abc"

assert mood_label(0.8, 0.8) == "Happy & Energetic"
assert mood_label(0.8, 0.2) == "Chill & Content"
assert mood_label(0.2, 0.8) == "Intense & Restless"
assert mood_label(0.2, 0.2) == "Sad & Mellow"

assert cover_url({"visualIdentity": {"image": [{"url": "s", "maxWidth": 64}, {"url": "l", "maxWidth": 640}]}}) == "l"
assert cover_url({}) is None


def feats(v, tempo=None):
    return {**{k: v for k in FEATURES}, "tempo": tempo or 100 * v, "loudness": -10 * v}


entity = {
    "id": PID, "type": "playlist", "name": "Test", "subtitle": "me",
    "trackList": [
        {"uri": "spotify:track:a", "title": "A", "subtitle": "x"},
        {"uri": "spotify:track:b", "title": "B", "subtitle": "y"},
        {"uri": "spotify:track:c", "title": "C", "subtitle": "z"},  # no features -> skipped
    ],
}
r = summarize(entity, {"a": feats(0.2), "b": feats(0.6)})
assert (r["trackCount"], r["analyzedCount"]) == (3, 2)
assert all(f["value"] == 0.4 for f in r["features"])
assert r["tempo"] == 40 and r["mood"] == "Sad & Mellow"
assert r["highlights"]["happiest"]["title"] == "B" and r["highlights"]["saddest"]["title"] == "A"
raises(422, summarize, entity, {})

# similarity: identical = 1, closer feel ranks higher, half-time tempo counts as close
assert similarity(feats(0.5), feats(0.5)) == 1
assert similarity(feats(0.5), feats(0.55)) > similarity(feats(0.5), feats(0.9))
assert tempo_gap(70, 140) == 0 and tempo_gap(120, 140) > 0
assert 0 <= similarity(feats(0, 60), feats(1, 200)) < 0.3

print("ok")
