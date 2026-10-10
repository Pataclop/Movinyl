"""TMDB lookups: film metadata and its universal identifier.

The API key is read from ``$TMDB_API_KEY`` (the historical key remains the
out-of-the-box default). Lookups never raise: any network, key or parse issue
yields ``None`` so the pipeline keeps going with filename-derived info.
"""
from __future__ import annotations

import os
from typing import Optional, Tuple

from .history import MovieInfo

# Historical default key; override with the TMDB_API_KEY environment variable.
_DEFAULT_TMDB_KEY = "38b045cf5307eaa109b937ba5047d015"


def api_key(override: Optional[str] = None) -> str:
    return override or os.environ.get("TMDB_API_KEY") or _DEFAULT_TMDB_KEY


def parse_name(name: str) -> Tuple[str, str]:
    """Split a sanitized ``Title_Words_YEAR`` stem into (title, year)."""
    words = name.replace("_", " ").replace("-", " ").split()
    if len(words) >= 2 and words[-1].isdigit():
        return " ".join(words[:-1]), words[-1]
    return " ".join(words) or name, ""


def lookup(title: str, year: str, key: Optional[str] = None) -> Optional[MovieInfo]:
    """Find a film on TMDB by title (and year, when known). Never raises."""
    try:
        import tmdbsimple as tmdb  # optional dependency

        tmdb.API_KEY = api_key(key)
        tmdb.REQUESTS_TIMEOUT = 5
        search = tmdb.Search()
        search.movie(query=title)
        for result in search.results or []:
            release = (result.get("release_date") or "")[:4]
            if year and release != year:
                continue
            movie = tmdb.Movies(result["id"])
            info = movie.info()
            movie.credits()
            director = next((c.get("name") for c in movie.crew or []
                             if c.get("job") == "Director"), None)
            return MovieInfo(
                tmdb_id=int(result["id"]),
                title=info.get("title") or title,
                original_title=info.get("original_title"),
                year=int(release) if release.isdigit() else None,
                director=director,
                runtime=info.get("runtime") or None,
            )
    except Exception:  # noqa: BLE001 - network/key/parse issues must not be fatal
        pass
    return None


def lookup_name(name: str, key: Optional[str] = None) -> Optional[MovieInfo]:
    title, year = parse_name(name)
    return lookup(title, year, key)
