import json
from pathlib import Path

FRAMES = [
    "gold_ring",
    "gold_platinum",
    "gold_rose",
    "dragon",
    "dragon_ice",
    "dragon_shadow",
]

_STORE_PATH = Path("instance/user_frames.json")

def _load_store():
    if _STORE_PATH.exists():
        try:
            return json.loads(_STORE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def _save_store(data):
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STORE_PATH.write_text(json.dumps(data), encoding="utf-8")

def get_user_frames(user_id):
    store = _load_store()
    entry = store.get(str(user_id)) or {}
    active = entry.get("active")
    active = active if active in FRAMES else None
    return {"active": active}

def set_user_frames(user_id, active):
    active = active if active in FRAMES else None
    store = _load_store()
    store[str(user_id)] = {"active": active}
    _save_store(store)
    return {"active": active}