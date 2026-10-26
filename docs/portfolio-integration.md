# Portfolio integration brief

Prompt for an agent adding a live "Spotify Vibe Analyzer" demo to a Next.js portfolio. Replace `<API_URL>` with the deployed Vercel URL first.

---

## Task
Add a new project entry to the projects page and a live, interactive demo that calls the deployed API. Match the existing project entries (numbered list, title, one-line description, tech tags, status) and the site's design system and conventions. Set the status to "Live API". Do not add new UI libraries if the repo already has a chart or UI solution.

## Project summary
Two features Spotify no longer offers:
1. **Playlist mood:** paste a public playlist or album link and get a mood profile (radar chart, mood label, tempo, standout tracks).
2. **Similar vibes:** paste a track link and get songs with the same listening feel. Matching is content-based, on audio features only (energy, valence, danceability, acousticness, tempo). No collaborative filtering, no listening history.

Tags: Python, Vercel Serverless, REST API, Audio Features, Content-based Similarity
Source: https://github.com/thisisaldi/spotify-playlist-analyzer

How similar vibes works (for the case-study blurb):
- Spotify's Web API no longer exposes audio features or playlist items to new apps, so track lists come from public embed pages and audio features from ReccoBeats.
- ReccoBeats recommendations are used only as a candidate pool. Each candidate is re-ranked by weighted audio-feature distance to the seed track. Valence and energy weigh most, and tempo is octave-aware (70 and 140 BPM count as close).
- A second round re-seeds from the best matches to pull the pool closer to the original vibe.
- If a track is missing from the feature database, its 30-second preview is analyzed instead.

## API
Base URL: `<API_URL>`
Both endpoints are `GET`, return JSON, and allow CORS only for the origins listed in the `ALLOWED_ORIGINS` env var (`https://naufaldi.vercel.app` and `http://localhost:3000`), so they can be called directly from the browser.

### GET /api/analyze?url=<playlist or album link>
```json
{
  "playlist": { "id": "", "type": "playlist", "name": "", "owner": "", "image": "https://…", "url": "https://open.spotify.com/…" },
  "trackCount": 50,
  "analyzedCount": 24,
  "mood": "Happy & Energetic",
  "features": [{ "key": "danceability", "label": "Danceable", "value": 0.635 }],
  "tempo": 125,
  "loudness": -7.14,
  "highlights": {
    "happiest": { "id": "", "title": "", "artist": "", "value": 0.96 },
    "saddest": {}, "mostEnergetic": {}, "mostDanceable": {}
  },
  "tracks": [{ "id": "", "title": "", "artist": "", "danceability": 0.5, "energy": 0.5 }]
}
```
- `features` always has 7 entries with values from 0 to 1. Use them for a radar chart.
- `mood` is one of: "Happy & Energetic", "Chill & Content", "Intense & Restless", "Sad & Mellow".
- `image` can be null.

### GET /api/similar?url=<track link>&limit=10
`limit` is optional, from 1 to 25, default 10.
```json
{
  "seed": { "id": "", "title": "", "artist": "", "image": "https://…", "url": "", "features": { "energy": 0.96, "valence": 0.21 } },
  "labels": { "energy": "Energy Level", "valence": "Happiness" },
  "tracks": [{ "id": "", "title": "", "artist": "", "url": "", "similarity": 96, "features": { "energy": 0.9 } }]
}
```
- `similarity` is an integer from 0 to 100, higher means a closer vibe.
- Each track's `features` has the same keys as `seed.features` (the 7 radar features plus `tempo`). Plot the seed and the selected match on one radar chart to compare them.
- `seed.image` can be null.
- `tracks` can be empty. Show "No close matches found."

### Errors
Non-2xx responses return `{ "error": "<human-readable message>" }`. Show the message as-is.
- 400: invalid link or parameter
- 404: not found or private
- 422: no audio data for this item
- 502: upstream data source unavailable

## Behavior requirements
- Accept Spotify web links (`https://open.spotify.com/...`, including `?si=` suffixes and locale prefixes like `/intl-id/`) and `spotify:` URIs. Validate type client-side: playlist or album for analyze, track for similar.
- **Latency:** uncached `/api/similar` takes about 8 to 10 seconds, and `/api/analyze` a few seconds. Show a clear loading state with a note like "Analyzing audio features, this can take a few seconds". Do not time out before 30 seconds.
- Results are cached at the CDN for 6 hours. Repeat requests for the same link are fast and return the same results.
- Provide one-click example inputs:
  - Playlist: https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
  - Track: https://open.spotify.com/track/7ouMYWpwJ422jRcDASZB7P
- Make each result track a link to its `url`, opening in a new tab.
- Be honest in the UI about the limits: `analyzedCount` can be lower than `trackCount` (show "24 of 50 tracks analyzed"), and matching is by sound, not genre.
- Responsive layout, keyboard accessible, works in light and dark mode if the site supports both.
- Call the API directly from the browser; no Next.js proxy route is needed. Keep the API URL in one constant or in `NEXT_PUBLIC_VIBE_API_URL`.

## Acceptance checklist
- [ ] Project entry appears on /projects in the same style as the others, with status "Live API"
- [ ] Both demos work end to end against `<API_URL>` from the production domain and from localhost:3000
- [ ] Loading, error, empty and success states all handled
- [ ] No CORS errors in the console
- [ ] Source link and a short "how it works" section included

## CORS note
Preview domains (e.g. `*.vercel.app` branch URLs) are blocked unless added to `ALLOWED_ORIGINS` in the API project's Vercel settings. It is an exact match, with no wildcards.
