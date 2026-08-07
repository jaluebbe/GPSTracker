import sqlite3
import json
from fastapi import APIRouter, HTTPException, Request, Response, Path
from pathlib import Path as FilePath
from typing import Annotated

router = APIRouter(tags=["offline_map"])

osm_path = FilePath("../..")
natural_earth_vector_path = FilePath("natural_earth_vector.mbtiles")
natural_earth_shaded_relief_path = FilePath(
    "natural_earth_2_shaded_relief.mbtiles"
)
# Optional worldwide fallback for zoom levels not covered by any region
# file, e.g. /home/gpstracker/planet_fallback.mbtiles.
planet_path = osm_path / "planet_fallback.mbtiles"

# Persistent read-only connections, opened once at module load time.
# check_same_thread=False is required because FastAPI uses a thread pool.
_db_connections: dict[FilePath, sqlite3.Connection] = {}


def get_db_connection(db_file_name: FilePath) -> sqlite3.Connection:
    if db_file_name not in _db_connections:
        if not db_file_name.is_file():
            raise HTTPException(
                status_code=404,
                detail=f"File '{db_file_name}' not found.",
            )
        conn = sqlite3.connect(
            f"file:{db_file_name}?mode=ro",
            uri=True,
            check_same_thread=False,
        )
        # 8 MB page cache per connection; no mmap to keep VSZ low.
        conn.execute("PRAGMA cache_size = -8192")
        conn.execute("PRAGMA mmap_size = 0")
        conn.execute("PRAGMA temp_store = MEMORY")
        _db_connections[db_file_name] = conn
    return _db_connections[db_file_name]


def fetch_tile_data(db_connection, zoom_level, tile_column, tile_row):
    cursor = db_connection.execute(
        "SELECT tile_data FROM tiles"
        " WHERE zoom_level = ? and tile_column = ? and tile_row = ?",
        (zoom_level, tile_column, tile_row),
    )
    return cursor.fetchone()


def get_mbtiles_maxzoom(path: FilePath) -> int | None:
    if not path.is_file():
        return None
    conn = get_db_connection(path)
    row = conn.execute(
        "SELECT value FROM metadata WHERE name = 'maxzoom'"
    ).fetchone()
    return int(row[0]) if row else None


# Resolved once at startup; None if no planet_fallback.mbtiles is present.
planet_max_zoom = get_mbtiles_maxzoom(planet_path)


@router.get("/api/vector/regions")
def list_vector_regions():
    mbtiles_files = sorted(
        osm_path.glob("*.mbtiles"),
        key=lambda f: f.stat().st_size,
        reverse=True,
    )
    return [
        file.stem for file in mbtiles_files if file.stem != planet_path.stem
    ]


@router.get("/api/vector/metadata/{region}.json")
def get_vector_metadata(
    region: Annotated[str, Path(pattern="^[a-zA-Z0-9_-]+$")], request: Request
):
    db_file_name = osm_path / f"{region}.mbtiles"
    db_connection = get_db_connection(db_file_name)
    cursor = db_connection.execute("SELECT * FROM metadata")
    result = cursor.fetchall()
    if result is None:
        raise HTTPException(status_code=404, detail="Metadata not found.")
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    port_suffix = f":{request.url.port}" if request.url.port else ""
    metadata = {
        "tilejson": "2.0.0",
        "scheme": "xyz",
        "tiles": [
            f"{scheme}://{request.url.hostname}{port_suffix}"
            f"/api/vector/tiles/{region}/{{z}}/{{x}}/{{y}}.pbf"
        ],
    }
    for key, value in result:
        if key == "json":
            metadata.update(json.loads(value))
        elif key in ("minzoom", "maxzoom"):
            metadata[key] = int(value)
        elif key == "center":
            continue
        elif key == "bounds":
            continue
        else:
            metadata[key] = value
    return metadata


@router.get("/api/vector/tiles/{region}/{zoom_level}/{x}/{y}.pbf")
def get_vector_tiles(
    region: Annotated[str, Path(pattern="^[a-zA-Z0-9_-]+$")],
    zoom_level: int,
    x: int,
    y: int,
):
    tile_column = x
    tile_row = 2**zoom_level - 1 - y
    db_file_name = osm_path / f"{region}.mbtiles"
    result = None

    # Prefer the planet fallback at low zoom levels to avoid visible seams
    # between neighboring region files.
    if planet_max_zoom is not None and zoom_level <= planet_max_zoom:
        result = fetch_tile_data(
            get_db_connection(planet_path), zoom_level, tile_column, tile_row
        )

    if result is None:
        result = fetch_tile_data(
            get_db_connection(db_file_name), zoom_level, tile_column, tile_row
        )

    # Legacy low-zoom fallback, kept for setups without a
    # planet_fallback.mbtiles file.
    if (
        result is None
        and zoom_level <= 7
        and natural_earth_vector_path.is_file()
    ):
        result = fetch_tile_data(
            get_db_connection(natural_earth_vector_path),
            zoom_level,
            tile_column,
            tile_row,
        )

    if result is None:
        raise HTTPException(status_code=404, detail="Tile not found.")
    return Response(
        content=result[0],
        media_type="application/octet-stream",
        headers={"Content-Encoding": "gzip"},
    )


@router.get("/api/vector/style/{region}/{style_name}.json")
def get_vector_style(
    region: Annotated[str, Path(pattern="^[a-zA-Z0-9_-]+$")],
    style_name: str,
    request: Request,
):
    style_file_name = f"{style_name}_style.json"
    if not FilePath(style_file_name).is_file():
        raise HTTPException(
            status_code=404, detail=f"Style '{style_name}' not known."
        )
    with open(style_file_name) as f:
        style = json.load(f)
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    port_suffix = f":{request.url.port}" if request.url.port else ""
    style["sources"]["openmaptiles"]["url"] = (
        f"{scheme}://{request.url.hostname}{port_suffix}"
        f"/api/vector/metadata/{region}.json"
    )
    style["glyphs"] = (
        f"{scheme}://{request.url.hostname}{port_suffix}"
        "/fonts/{fontstack}/{range}.pbf"
    )
    if style.get("sprite") is not None:
        style["sprite"] = (
            f"{scheme}://{request.url.hostname}{port_suffix}"
            f"/static/sprites/{style_name}"
        )
    return style


@router.get(
    "/api/raster/natural_earth_2_shaded_relief/{zoom_level}/{x}/{y}.webp"
)
def get_raster_natural_earth_2_shaded_relief(zoom_level: int, x: int, y: int):
    tile_column = x
    tile_row = 2**zoom_level - 1 - y
    result = fetch_tile_data(
        get_db_connection(natural_earth_shaded_relief_path),
        zoom_level,
        tile_column,
        tile_row,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Tile not found.")
    return Response(content=result[0], media_type="image/webp")
