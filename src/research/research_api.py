"""
Read-only local research API. Lists export packs and previews manifests.
Does not execute trades or start the ALPHA runner.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

RESEARCH_ROOT = Path(os.environ.get("FXG_RESEARCH_ROOT", Path.home() / "fxg-research")).expanduser()
EXPORT_ROOT = Path(
    os.environ.get("FXG_RESEARCH_EXPORTS_DIR", RESEARCH_ROOT / "ARTIFACTS" / "exports")
).expanduser()

app = FastAPI(title="FXG Research API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("RESEARCH_API_CORS", "http://localhost:3000,http://127.0.0.1:5000").split(","),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _safe_manifests() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not EXPORT_ROOT.is_dir():
        return out
    for child in sorted(EXPORT_ROOT.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not child.is_dir():
            continue
        mf = child / "manifest.json"
        if not mf.is_file():
            continue
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        data["_pack_path"] = str(child)
        out.append(data)
    return out


@app.get("/api/health")
async def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "service": "research-api",
        "research_root": str(RESEARCH_ROOT),
        "exports_dir": str(EXPORT_ROOT),
    }


@app.get("/api/research/packs")
async def research_packs() -> Dict[str, Any]:
    packs = _safe_manifests()
    return {"ok": True, "packs": packs, "count": len(packs)}


@app.get("/api/research/latest")
async def research_latest() -> Dict[str, Any]:
    packs = _safe_manifests()
    if not packs:
        return {"ok": True, "pack": None, "empty": True}
    return {"ok": True, "pack": packs[0], "empty": False}


def build_compare_payload(pack_id: Optional[str] = None) -> Dict[str, Any]:
    packs = _safe_manifests()
    local_pack: Optional[Dict[str, Any]] = None
    if pack_id:
        for p in packs:
            if p.get("pack_id") == pack_id:
                local_pack = p
                break
        if local_pack is None:
            raise ValueError("pack_id not found")
    elif packs:
        local_pack = packs[0]

    alpha_path = os.environ.get("FXG_ALPHA_CHAMPIONS_JSON", "").strip()
    alpha_champions: Any = None
    if alpha_path:
        ap = Path(alpha_path).expanduser()
        if ap.is_file():
            try:
                alpha_champions = json.loads(ap.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                alpha_champions = {"empty": True, "reason": "invalid_json"}
        else:
            alpha_champions = {"empty": True, "reason": "path_not_found"}
    else:
        alpha_champions = {"empty": True, "reason": "FXG_ALPHA_CHAMPIONS_JSON unset"}

    return {
        "ok": True,
        "local_pack": local_pack,
        "alpha_champions": alpha_champions,
        "note": "Read-only comparison; no execution side effects.",
    }


@app.get("/api/research/compare/alpha-vs-local")
async def research_compare_alpha_vs_local(pack_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    try:
        return build_compare_payload(pack_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="pack_id not found")
