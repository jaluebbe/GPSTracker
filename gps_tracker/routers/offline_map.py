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
