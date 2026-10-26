# API Reference

Base URL: `https://<your-deployment>.vercel.app`

Two read-only JSON endpoints. No authentication, no API key.

| Endpoint | Purpose |
|----------|---------|
| [`GET /api/analyze`](#get-apianalyze) | Mood profile of a public playlist or album |
| [`GET /api/similar`](#get-apisimilar) | Tracks with the closest listening feel to a seed track |

## Conventions

- **Format:** all responses are `application/json`.
- **CORS:** `Access-Control-Allow-Origin` echoes the request `Origin` if it appears in the `ALLOWED_ORIGINS` environment variable (comma-separated, exact match, no wildcards). If the variable is unset, the API allows any origin (`*`). `OPTIONS` requests return `204`.
- **Caching:** successful responses send `Cache-Control: public, s-maxage=21600, stale-while-revalidate=86400`. Vercel's CDN serves repeat requests for the same URL for 6 hours without calling the upstream sources, so results for a given link stay stable during that time. Errors send `no-store`.
- **Latency:** an uncached `/api/analyze` takes a few seconds and an uncached `/api/similar` takes about 8 to 10 seconds. Set client timeouts to 30 seconds or more.
- **Accepted links:** `https://open.spotify.com/<type>/<id>`, including `?si=` suffixes, trailing slashes and locale prefixes such as `/intl-id/`, and `spotify:<type>:<id>` URIs. Always URL-encode the `url` parameter.

---

## GET /api/analyze

Averages the audio features of a public playlist or album into a mood profile.

### Query parameters

| Name | Required | Description |
|------|----------|-------------|
| `url` | yes | Spotify playlist or album link |

### Response `200`

| Field | Type | Description |
|-------|------|-------------|
| `playlist.id` | string | Spotify ID |
| `playlist.type` | `"playlist"` \| `"album"` | |
| `playlist.name` | string | |
| `playlist.owner` | string | Owner or artist name |
| `playlist.image` | string \| null | Cover image URL |
| `playlist.url` | string | Link to open it on Spotify |
| `trackCount` | number | Tracks listed on the Spotify page |
| `analyzedCount` | number | Tracks that had audio features. Can be lower than `trackCount` |
| `mood` | string | `"Happy & Energetic"`, `"Chill & Content"`, `"Intense & Restless"` or `"Sad & Mellow"` |
| `features` | array | 7 entries: `{ key, label, value }`, `value` from 0 to 1 (playlist average) |
| `tempo` | number | Average tempo in BPM |
| `loudness` | number | Average loudness in dB |
| `highlights` | object | `happiest`, `saddest`, `mostEnergetic`, `mostDanceable`: each `{ id, title, artist, value }` |
| `tracks` | array | Per-track features: `id`, `title`, `artist`, the 7 features, `tempo`, `loudness` |

`mood` is derived from average valence (below or above 0.5) and energy (below or above 0.5).

### Feature keys

| Key | Label | Meaning |
|-----|-------|---------|
| `danceability` | Danceable | Rhythmic suitability for dancing |
| `energy` | Energy Level | Intensity and activity |
| `speechiness` | Speech-like | Presence of spoken words |
| `acousticness` | Acoustic Sound | Confidence the track is acoustic |
| `instrumentalness` | Instrumental Feel | Likelihood of no vocals |
| `liveness` | Live Performance | Presence of an audience |
| `valence` | Happiness | Musical positivity |

### Example

```sh
curl "https://<your-deployment>.vercel.app/api/analyze?url=https%3A%2F%2Fopen.spotify.com%2Fplaylist%2F37i9dQZF1DXcBWIGoYBM5M"
```

```json
{
  "playlist": {
    "id": "37i9dQZF1DXcBWIGoYBM5M",
    "type": "playlist",
    "name": "Today's Top Hits",
    "owner": "Spotify",
    "image": "https://i.scdn.co/image/…",
    "url": "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
  },
  "trackCount": 50,
  "analyzedCount": 24,
  "mood": "Happy & Energetic",
  "features": [
    { "key": "danceability", "label": "Danceable", "value": 0.635 },
    { "key": "energy", "label": "Energy Level", "value": 0.621 }
  ],
  "tempo": 125,
  "loudness": -7.142,
  "highlights": {
    "happiest": { "id": "3ouNEk0tv5TTi8VWMe1xbX", "title": "Animal", "artist": "KATSEYE", "value": 0.962 },
    "saddest": {},
    "mostEnergetic": {},
    "mostDanceable": {}
  },
  "tracks": [
    { "id": "0eAuGrXyGFYwur9ARUe7LJ", "title": "Earrings", "artist": "Malcolm Todd", "danceability": 0.498, "energy": 0.505, "tempo": 79.877, "loudness": -8.644 }
  ]
}
```

(`features` and `highlights` are shortened here; real responses include all 7 features and all 4 highlights.)

---

## GET /api/similar

Finds tracks with a similar listening feel to a seed track. Matching is content-based: only audio features are compared, never listening history or other users' behavior.

### Query parameters

| Name | Required | Default | Description |
|------|----------|---------|-------------|
| `url` | yes | | Spotify track link |
| `limit` | no | `10` | Number of matches, 1 to 25 (values outside the range are clamped) |

### Response `200`

| Field | Type | Description |
|-------|------|-------------|
| `seed.id` | string | Spotify track ID |
| `seed.title` | string | |
| `seed.artist` | string | Artists joined with `, ` |
| `seed.image` | string \| null | Cover image URL |
| `seed.url` | string | Link to open it on Spotify |
| `seed.features` | object | The 7 features (0 to 1) plus `tempo` (BPM) |
| `labels` | object | Maps feature keys to display labels |
| `tracks` | array | Matches, best first. May be empty |
| `tracks[].id` | string | Spotify track ID |
| `tracks[].title` | string | |
| `tracks[].artist` | string | |
| `tracks[].url` | string | Link to open it on Spotify |
| `tracks[].similarity` | number | Integer 0 to 100, higher is closer |
| `tracks[].features` | object | Same keys as `seed.features` |

### How matching works

1. Candidate pool: ReccoBeats recommendations seeded with the track (about 100 candidates). If ReccoBeats doesn't know the track, its 30-second Spotify preview is analyzed to get the seed's features, and the pool is seeded from that artist's closest-sounding catalog tracks instead.
2. Ranking: each candidate is scored by weighted distance to the seed's features, so the recommender only supplies candidates and never decides the order. Weights: energy 1.5, valence 1.5, danceability 1.0, acousticness 1.0, tempo 1.0, instrumentalness 0.75, speechiness 0.75, loudness 0.5, liveness 0.25. Tempo is compared octave-aware, so 70 and 140 BPM count as close.
3. Refinement: the 5 best matches seed a second round of candidates, which are ranked the same way.
4. Duplicates: results with the same title as the seed or an earlier result (re-releases, remasters) are dropped.

The candidate pool is randomized upstream, so uncached results can differ slightly between requests. The CDN cache makes a given link stable for 6 hours.

### Example

```sh
curl "https://<your-deployment>.vercel.app/api/similar?url=https%3A%2F%2Fopen.spotify.com%2Ftrack%2F7ouMYWpwJ422jRcDASZB7P&limit=3"
```

```json
{
  "seed": {
    "id": "7ouMYWpwJ422jRcDASZB7P",
    "title": "Knights of Cydonia",
    "artist": "Muse",
    "image": "https://image-cdn-ak.spotifycdn.com/image/…",
    "url": "https://open.spotify.com/track/7ouMYWpwJ422jRcDASZB7P",
    "features": { "danceability": 0.366, "energy": 0.963, "valence": 0.211, "tempo": 137.114 }
  },
  "labels": { "energy": "Energy Level", "valence": "Happiness" },
  "tracks": [
    {
      "id": "…",
      "title": "Drain You",
      "artist": "Nirvana",
      "url": "https://open.spotify.com/track/…",
      "similarity": 96,
      "features": { "danceability": 0.4, "energy": 0.9, "valence": 0.2, "tempo": 133.0 }
    }
  ]
}
```

(`features` objects are shortened here; real responses include all 7 features plus `tempo`.)

---

## Errors

Failed requests return a non-2xx status and a body of `{ "error": "<message>" }`. The message is safe to show to users.

| Status | Cause |
|--------|-------|
| `400` | Missing or invalid link, wrong link type for the endpoint, or non-numeric `limit` |
| `404` | Playlist, album or track not found, or not public |
| `422` | No audio features available for the item, an empty playlist, or not enough data to find similar tracks |
| `502` | Upstream source unreachable, returned an error, or changed its page format |
| `500` | Unexpected server error |

## Client usage

```ts
type Features = Record<
  "danceability" | "energy" | "speechiness" | "acousticness" | "instrumentalness" | "liveness" | "valence" | "tempo",
  number
>;

interface SimilarResponse {
  seed: { id: string; title: string; artist: string; image: string | null; url: string; features: Features };
  labels: Record<string, string>;
  tracks: { id: string; title: string; artist: string; url: string; similarity: number; features: Features }[];
}

async function similar(trackUrl: string, limit = 10): Promise<SimilarResponse> {
  const res = await fetch(`${API}/api/similar?url=${encodeURIComponent(trackUrl)}&limit=${limit}`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error);
  return data;
}
```

## Limitations

- The Spotify embed page lists at most about 100 tracks per playlist.
- ReccoBeats doesn't have every track, so `analyzedCount` can be lower than `trackCount`. Very new releases are the most likely to be missing.
- Audio features describe how a track sounds, not its genre, language or lyrics. A rock song can match a pop song with the same energy, mood and tempo.
- Both data sources are unofficial and could change without notice.

## Configuration

| Variable | Example | Default |
|----------|---------|---------|
| `ALLOWED_ORIGINS` | `https://naufaldi.vercel.app,http://localhost:3000` | `*` |
