import sqlite3
import json
from fastapi import APIRouter, HTTPException, Request, Response
from pathlib import Path

router = APIRouter(tags=["offline_map"])

osm_path = Path("../..")
natural_earth_vector_path = Path("natural_earth_vector.mbtiles")
natural_earth_shaded_relief_path = Path("natural_earth_2_shaded_relief.mbtiles")


def get_db_connection(db_file_name: Path):
    if not db_file_name.is_file():
        raise HTTPException(
            status_code=404, detail=f"File '{db_file_name}' not found."
        )
    return sqlite3.connect(f"file:{db_file_name}?mode=ro", uri=True)


def fetch_tile_data(db_connection, zoom_level, tile_column, tile_row):
    cursor = db_connection.execute(
        "SELECT tile_data FROM tiles WHERE zoom_level = ? and tile_column = ? and tile_row = ?",
        (zoom_level, tile_column, tile_row),
    )
    return cursor.fetchone()


@router.get("/api/vector/regions")
def list_vector_regions():
    mbtiles_files = sorted(
        osm_path.glob("*.mbtiles"), key=lambda f: f.stat().st_size, reverse=True
    )
    return [file.stem for file in mbtiles_files]


@router.get("/api/vector/metadata/{region}.json")
def get_vector_metadata(region: str, request: Request):
    db_file_name = osm_path / f"{region}.mbtiles"
    with get_db_connection(db_file_name) as db_connection:
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
            # metadata[key] = [float(_value) for _value in value.split(",")]
        else:
            metadata[key] = value
    return metadata


@router.get("/api/vector/tiles/{region}/{zoom_level}/{x}/{y}.pbf")
def get_vector_tiles(region: str, zoom_level: int, x: int, y: int):
    tile_column = x
    tile_row = 2**zoom_level - 1 - y
    db_file_name = osm_path / f"{region}.mbtiles"
    with get_db_connection(db_file_name) as db_connection:
        result = fetch_tile_data(
            db_connection, zoom_level, tile_column, tile_row
        )
    if result is None and zoom_level <= 7:
        with get_db_connection(natural_earth_vector_path) as db_connection:
            result = fetch_tile_data(
                db_connection, zoom_level, tile_column, tile_row
            )
    if result is None:
        raise HTTPException(status_code=404, detail="Tile not found.")
    return Response(
        content=result[0],
        media_type="application/octet-stream",
        headers={"Content-Encoding": "gzip"},
    )


@router.get("/api/vector/style/{region}/{style_name}.json")
def get_vector_style(region: str, style_name: str, request: Request):
    style_file_name = f"{style_name}_style.json"
    if not Path(style_file_name).is_file():
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
    with get_db_connection(natural_earth_shaded_relief_path) as db_connection:
        result = fetch_tile_data(
            db_connection, zoom_level, tile_column, tile_row
        )
    if result is None:
        raise HTTPException(status_code=404, detail="Tile not found.")
    return Response(content=result[0], media_type="image/webp")
