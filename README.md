# Spotify Vibe Analyzer

Two things Spotify doesn't give you:

1. **Playlist mood**: paste a public playlist or album and get its mood profile (radar chart, mood label, tempo, happiest/saddest/most energetic tracks).
2. **Similar vibes**: paste a track you love and get songs with the same *listening feel*, matched purely on audio features (energy, valence, danceability, acousticness, tempo…), not on what other people listen to.

A dependency-free Python API on Vercel serverless functions, plus a single-page demo.

## How it works

Spotify's Web API no longer exposes audio features (Nov 2024) or playlist items for apps you don't own (Feb 2026 Development Mode changes), so:

- **Track lists and metadata** come from Spotify's public embed pages. No credentials needed.
- **Audio features** come from [ReccoBeats](https://reccobeats.com), looked up by Spotify track ID. If a track isn't in their database, its 30-second preview is sent to ReccoBeats' audio analysis instead.
- **Similar vibes** is content-based: ReccoBeats recommendations are used only as a *candidate pool*. Every candidate is re-ranked by weighted distance between audio features (valence and energy weigh most; tempo is compared octave-aware, so 70 and 140 BPM count as close). A second round seeds from the best matches to move the pool closer to the original vibe.

## API

Both endpoints are `GET`, return JSON, send CORS headers, and are cached at Vercel's CDN for 6 hours. Errors return `{ "error": "..." }` with status 400/404/422/502.

### `GET /api/analyze?url=<playlist or album link>`

```json
{
  "playlist": { "id": "…", "type": "playlist", "name": "Today's Top Hits", "owner": "Spotify", "image": "https://…", "url": "https://open.spotify.com/playlist/…" },
  "trackCount": 50,
  "analyzedCount": 24,
  "mood": "Happy & Energetic",
  "features": [{ "key": "danceability", "label": "Danceable", "value": 0.635 }, "…"],
  "tempo": 125,
  "loudness": -7.142,
  "highlights": { "happiest": { "id": "…", "title": "…", "artist": "…", "value": 0.96 }, "saddest": {}, "mostEnergetic": {}, "mostDanceable": {} },
  "tracks": [{ "id": "…", "title": "…", "artist": "…", "danceability": 0.5, "energy": 0.5, "…": 0 }]
}
```

### `GET /api/similar?url=<track link>&limit=10` (limit 1–25)

```json
{
  "seed": { "id": "…", "title": "Knights of Cydonia", "artist": "Muse", "image": "https://…", "url": "…", "features": { "energy": 0.96, "…": 0 } },
  "labels": { "energy": "Energy Level", "…": "…" },
  "tracks": [{ "id": "…", "title": "Drain You", "artist": "Nirvana", "url": "…", "similarity": 96, "features": { "…": 0 } }]
}
```

## Deploy

```sh
npm i -g vercel
vercel          # preview
vercel --prod   # production
```

Optional environment variable:

| Name | Example | Default |
|------|---------|---------|
| `ALLOWED_ORIGINS` | `https://naufaldi.vercel.app,http://localhost:3000` | `*` (any origin) |

## Limitations

- The embed page lists at most ~100 tracks per playlist.
- ReccoBeats doesn't know every track, so `analyzedCount` can be lower than `trackCount`. Very new releases are the most likely to be missing.
- Audio features describe feel, not genre. A rock song can match a pop song with the same energy, mood and tempo.
- Both data sources are unofficial and could change without notice.

## Development

```sh
python test_api.py   # offline logic checks
vercel dev           # run the API + demo locally
```
