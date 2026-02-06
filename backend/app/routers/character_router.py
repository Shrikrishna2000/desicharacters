# backend/app/routers/character_router.py
import os
from fastapi import APIRouter, HTTPException
from typing import List, Dict
from pydantic import BaseModel
from pathlib import Path
from app.utils.helpers import safe_truncate, normalize_and_escape
from app.utils.logger import get_logger

logger = get_logger("character_router")
router = APIRouter(prefix="/characters", tags=["Characters"])

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


def _parse_character_file(path: Path) -> Dict:
    """
    Very small parser for our character markdown files.
    Expects basic block headers like:
    # Character: Name v1

    [visual]
    ...
    [personality]
    ...
    [examples]
    ...
    [forbidden]
    ...
    """
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        logger.exception("Failed to read character file %s: %s", path, e)
        return {}

    lines = [l.rstrip() for l in text.splitlines()]
    meta = {"id": path.stem, "name": path.stem, "version": "v1", "Visual_Description": "", "Personality": "", "Roleplay_Examples": [], "description": "", "tags": []}

    current_key = None
    buffer = []
    for line in lines:
        if line.startswith("#"):
            # parse title
            title = line.lstrip("#").strip()
            if ":" in title:
                # "Character: Name v1"
                try:
                    _, name = title.split(":", 1)
                    meta["name"] = safe_truncate(normalize_and_escape(name.strip()), 80)
                except:
                    pass
            continue

        # section headers like [visual]
        if line.startswith("[") and "]" in line:
            if current_key and buffer:
                meta[current_key] = "\n".join(buffer).strip()
            key = line.strip().lower().strip("[]")
            current_key = key
            buffer = []
            continue

        if current_key:
            buffer.append(line)

    if current_key and buffer:
        meta[current_key] = "\n".join(buffer).strip()

    # ensure Roleplay_Examples is a list
    if isinstance(meta.get("examples") or meta.get("roleplay_examples"), str):
        extext = meta.get("examples") or meta.get("roleplay_examples", "")
        examples = [safe_truncate(normalize_and_escape(e.strip()), 300) for e in extext.split("\n") if e.strip()]
        meta["Roleplay_Examples"] = examples
    elif isinstance(meta.get("Roleplay_Examples"), list):
        pass

    # friendly shape
    return {
        "id": meta["id"],
        "name": meta["name"],
        "version": meta.get("version", "v1"),
        "Visual_Description": meta.get("visual", "") or meta.get("Visual_Description", ""),
        "Personality": meta.get("personality", "") or meta.get("Personality", ""),
        "Roleplay_Examples": meta.get("Roleplay_Examples", []),
        "description": meta.get("description", "") or "",
        "tags": meta.get("tags", []),
    }


@router.get("/", response_model=List[Dict])
async def list_characters():
    """List available character prompts from /prompts directory."""
    # print(f"prompt  dir : {PROMPTS_DIR}")
    if not PROMPTS_DIR.exists():
        raise HTTPException(status_code=500, detail="Prompts directory not found on server.")
    items = []
    for p in PROMPTS_DIR.glob("*.md"):
        parsed = _parse_character_file(p)
        if parsed:
            items.append(parsed)
    return items


@router.get("/{character_id}", response_model=Dict)
async def get_character(character_id: str):
    path = PROMPTS_DIR / f"{character_id}.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Character not found")
    return _parse_character_file(path)


# -----------------------------
#  Generation Endpoint
# -----------------------------

class GenerateRequest(BaseModel):
    topic: str

@router.post("/generate", response_model=Dict)
async def generate_character(request: GenerateRequest):
    """
    Generate a new character profile based on a topic or description.
    """
    from app.services.character_generation_service import generate_character_profile
    
    if not request.topic:
        raise HTTPException(status_code=400, detail="Topic is required")
        
    try:
        character = await generate_character_profile(request.topic)
        return character
    except Exception as e:
        logger.error(f"Error generating character: {e}")
        raise HTTPException(status_code=500, detail=str(e))
