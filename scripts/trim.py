#!/usr/bin/env python3
"""Shrink raw ThaiWater API responses into the small files the website reads.

Usage: python3 scripts/trim.py RAW_DIR OUT_DIR
Reads RAW_DIR/{waterlevel,rain,main}.json and writes OUT_DIR/{waterlevel,rain,dam}.json.
A source that is missing or broken is skipped, so the previous output file is kept.
"""
import json
import os
import sys
from datetime import datetime, timezone

RAW, OUT = sys.argv[1], sys.argv[2]
FETCHED = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(name):
    path = os.path.join(RAW, name + ".json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:  # noqa: BLE001
        print(f"::warning::skip {name}: {e}")
        return None


def rows_of(j):
    """Find the first list of records called "data" anywhere in the response."""
    if isinstance(j, list):
        return j
    if isinstance(j, dict):
        if isinstance(j.get("data"), list):
            return j["data"]
        for v in j.values():
            r = rows_of(v)
            if r:
                return r
    return []


def th(o):
    return (o or {}).get("th") or (o or {}).get("en") or ""


def num(v, nd=2):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return round(x, nd)


def write(name, rows):
    path = os.path.join(OUT, name + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"v": 2, "fetched": FETCHED, "rows": rows}, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{name}: {len(rows)} rows, {os.path.getsize(path) // 1024} KB")


os.makedirs(OUT, exist_ok=True)

j = load("waterlevel")
if j is not None:
    out = []
    for d in rows_of(j):
        st = d.get("station") or {}
        name = th(st.get("tele_station_name"))
        if not name:
            continue
        out.append({
            "s": name,
            "p": th((d.get("geocode") or {}).get("province_name")),
            "m": num(d.get("waterlevel_msl")),
            "c": num(d.get("storage_percent")),
            "l": d.get("situation_level"),
            "t": d.get("waterlevel_datetime") or "",
            "y": num(st.get("tele_station_lat"), 5),
            "x": num(st.get("tele_station_long"), 5),
        })
    if out:
        write("waterlevel", out)

j = load("rain")
if j is not None:
    out = []
    for d in rows_of(j):
        v = num(d.get("rain_24h"), 1)
        if not v or v <= 0:
            continue
        st = d.get("station") or {}
        out.append({
            "s": th(st.get("tele_station_name")),
            "p": th((d.get("geocode") or {}).get("province_name")),
            "v": v,
            "t": d.get("rainfall_datetime") or "",
            "y": num(st.get("tele_station_lat"), 5),
            "x": num(st.get("tele_station_long"), 5),
        })
    out.sort(key=lambda r: -r["v"])
    if j is not None and rows_of(j):
        write("rain", out)

j = load("main")
if j is not None:
    dam = (((j.get("dam") or {}).get("data") or {}).get("data")) if isinstance(j, dict) else None
    out = []
    for d in dam or []:
        name = th((d.get("dam") or {}).get("dam_name"))
        if not name:
            continue
        out.append({
            "s": name,
            "p": th((d.get("geocode") or {}).get("province_name")),
            "c": num(d.get("dam_storage_percent")),
            "i": num(d.get("dam_inflow")),
            "o": num(d.get("dam_released")),
            "d": d.get("dam_date") or "",
        })
    if out:
        write("dam", out)
