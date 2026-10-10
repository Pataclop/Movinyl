"""TMDB lookups: film metadata and its universal identifier.

The API key is read from ``$TMDB_API_KEY`` (the historical key remains the
out-of-the-box default). Lookups never raise: any network, key or parse issue
yields ``None`` so the pipeline keeps going with filename-derived info.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

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


def _client(key: Optional[str]):
    import tmdbsimple as tmdb  # optional dependency

    tmdb.API_KEY = api_key(key)
    tmdb.REQUESTS_TIMEOUT = 5
    return tmdb


@dataclass
class Candidate:
    """One TMDB search hit, as listed in the GUI's match window."""
    tmdb_id: int
    title: str
    original_title: str = ""
    year: Optional[int] = None
    language: str = ""
    overview: str = ""
    popularity: float = 0.0
    votes: int = 0
    rating: float = 0.0
    poster_path: Optional[str] = None


def _candidate(result: dict) -> Candidate:
    release = (result.get("release_date") or "")[:4]
    return Candidate(
        tmdb_id=int(result["id"]),
        title=result.get("title") or result.get("original_title") or "?",
        original_title=result.get("original_title") or "",
        year=int(release) if release.isdigit() else None,
        language=result.get("original_language") or "",
        overview=result.get("overview") or "",
        popularity=float(result.get("popularity") or 0.0),
        votes=int(result.get("vote_count") or 0),
        rating=float(result.get("vote_average") or 0.0),
        poster_path=result.get("poster_path"),
    )


_IMDB_ID = re.compile(r"\b(tt\d{5,10})\b")
_TMDB_URL = re.compile(r"themoviedb\.org/movie/(\d+)")


def search(
    query: str,
    year: Optional[int] = None,
    language: str = "en-US",
    include_adult: bool = False,
    pages: int = 3,
    key: Optional[str] = None,
) -> List[Candidate]:
    """Search TMDB for films matching ``query`` (relevance order).

    ``query`` may also be an IMDb id / URL (``tt0062622``), a TMDB movie URL or
    a bare TMDB id: that exact film is returned. Raises on network/key errors
    so the caller can show them.
    """
    tmdb = _client(key)
    query = query.strip()
    imdb = _IMDB_ID.search(query)
    if imdb:
        found = tmdb.Find(imdb.group(1)).info(external_source="imdb_id",
                                              language=language)
        return [_candidate(r) for r in found.get("movie_results") or []]
    tmdb_url = _TMDB_URL.search(query)
    if tmdb_url or query.isdigit():
        movie_id = int(tmdb_url.group(1) if tmdb_url else query)
        try:
            return [_candidate(tmdb.Movies(movie_id).info(language=language))]
        except Exception:  # noqa: BLE001 - not an id after all: search the digits
            if tmdb_url:
                return []
    if not query:
        return []

    params = {"query": query, "language": language,
              "include_adult": "true" if include_adult else "false"}
    if year:
        params["year"] = year
    out: List[Candidate] = []
    seen = set()
    s = tmdb.Search()
    for page in range(1, max(1, pages) + 1):
        data = s.movie(page=page, **params)
        for result in data.get("results") or []:
            if result.get("id") not in seen:
                seen.add(result.get("id"))
                out.append(_candidate(result))
        if page >= int(data.get("total_pages") or 1):
            break
    return out


def details(tmdb_id: int, language: str = "en-US",
            key: Optional[str] = None) -> MovieInfo:
    """Full metadata (director, runtime ...) of one film. Raises on failure."""
    tmdb = _client(key)
    movie = tmdb.Movies(int(tmdb_id))
    info = movie.info(language=language)
    movie.credits()
    director = next((c.get("name") for c in movie.crew or []
                     if c.get("job") == "Director"), None)
    release = (info.get("release_date") or "")[:4]
    return MovieInfo(
        tmdb_id=int(tmdb_id),
        title=info.get("title"),
        original_title=info.get("original_title"),
        year=int(release) if release.isdigit() else None,
        director=director,
        runtime=info.get("runtime") or None,
    )


def poster_url(path: Optional[str], size: str = "w185") -> Optional[str]:
    return f"https://image.tmdb.org/t/p/{size}{path}" if path else None


def lookup(title: str, year: str, key: Optional[str] = None) -> Optional[MovieInfo]:
    """Find a film on TMDB by title (and year, when known). Never raises."""
    try:
        for hit in search(title, pages=1, key=key):
            if year and str(hit.year or "") != year:
                continue
            info = details(hit.tmdb_id, key=key)
            info.title = info.title or title
            return info
    except Exception:  # noqa: BLE001 - network/key/parse issues must not be fatal
        pass
    return None


def lookup_name(name: str, key: Optional[str] = None) -> Optional[MovieInfo]:
    title, year = parse_name(name)
    return lookup(title, year, key)
