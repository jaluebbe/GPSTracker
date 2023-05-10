import os
import sqlite3
import json
from fastapi import APIRouter, HTTPException, Request, Response

router = APIRouter()


@router.get("/api/vector/metadata/{region}.json")
def get_vector_metadata(region: str, request: Request):
    db_file_name = f"{region}.mbtiles"
    if not os.path.isfile(db_file_name):
        raise HTTPException(
            status_code=404, detail=f"Region '{region}' not found."
        )
    db_connection = sqlite3.connect(f"file:{db_file_name}?mode=ro", uri=True)
    cursor = db_connection.execute("SELECT * FROM metadata")
    result = cursor.fetchall()
    cursor.close()
    db_connection.close()
    if result is None:
        raise HTTPException(status_code=404, detail="Metadata not found.")
    if request.url.port is None:
        port_suffix = ""
    else:
        port_suffix = f":{request.url.port}"
    metadata = {
        "tilejson": "2.0.0",
        "scheme": "xyz",
        "tiles": [
            f"{request.url.scheme}://{request.url.hostname}{port_suffix}"
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
            metadata[key] = [float(_value) for _value in value.split(",")]
        else:
            metadata[key] = value
    return metadata


@router.get("/api/vector/tiles/{region}/{zoom_level}/{x}/{y}.pbf")
def get_vector_tiles(region: str, zoom_level: int, x: int, y: int):
    tile_column = x
    tile_row = 2**zoom_level - 1 - y
    db_file_name = f"{region}.mbtiles"
    if not os.path.isfile(db_file_name):
        raise HTTPException(
            status_code=404, detail=f"Region '{region}' not found."
        )
    db_connection = sqlite3.connect(f"file:{db_file_name}?mode=ro", uri=True)
    cursor = db_connection.execute(
        "SELECT tile_data FROM tiles "
        "WHERE zoom_level = ? and tile_column = ? and tile_row = ?",
        (zoom_level, tile_column, tile_row),
    )
    result = cursor.fetchone()
    cursor.close()
    db_connection.close()
    if result is None:
        raise HTTPException(status_code=404, detail="Tile not found.")
    return Response(
        content=result[0],
        media_type="application/octet-stream",
        headers={"Content-Encoding": "gzip"},
    )


@router.get("/api/vector/style/{style_name}.json")
def get_vector_style(style_name: str, request: Request):
    style_file_name = f"{style_name}_style.json"
    if not os.path.isfile(style_file_name):
        raise HTTPException(
            status_code=404, detail=f"Style '{style_name}' not known."
        )
    with open(style_file_name) as f:
        style = json.load(f)
    scheme = request.url.scheme
    if request.url.port is None:
        port_suffix = ""
    else:
        port_suffix = f":{request.url.port}"
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
    db_file_name = f"natural_earth_2_shaded_relief.mbtiles"
    db_connection = sqlite3.connect(f"file:{db_file_name}?mode=ro", uri=True)
    cursor = db_connection.execute(
        "SELECT tile_data FROM tiles "
        "WHERE zoom_level = ? and tile_column = ? and tile_row = ?",
        (zoom_level, tile_column, tile_row),
    )
    result = cursor.fetchone()
    cursor.close()
    db_connection.close()
    if result is None:
        raise HTTPException(status_code=404, detail="Tile not found.")
    return Response(content=result[0], media_type="image/webp")
