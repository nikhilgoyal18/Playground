"""
Parses newsletter and Twitter summary files into chunks and loads them into ChromaDB.
Can be run standalone to pre-build the index, or imported by search.py for auto-indexing.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).parent
PLAYGROUND_ROOT = BASE_DIR.parent
DATA_FILE = BASE_DIR / "data" / "indexed.json"
DB_PATH = BASE_DIR / "db" / "chroma"

COLLECTION_NAME = "summaries"
EMBED_MODEL = "all-MiniLM-L6-v2"

SUMMARY_SOURCES = [
    ("newsletter", PLAYGROUND_ROOT / "newsletter-insights" / "summaries"),
    ("twitter", PLAYGROUND_ROOT / "twitter-insights" / "summaries"),
]

_model = None
_collection = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL)
    return _model


def get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(DB_PATH))
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def load_indexed_state():
    if not DATA_FILE.exists():
        return {"indexed_files": [], "last_run": None}
    return json.loads(DATA_FILE.read_text())


def save_indexed_state(state):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    DATA_FILE.write_text(json.dumps(state, indent=2))


def discover_summary_files():
    """Returns list of (relative_path, source_type, date_str)."""
    found = []
    for source_type, dir_path in SUMMARY_SOURCES:
        if not dir_path.exists():
            continue
        for f in sorted(dir_path.glob("*.md")):
            rel = str(f.relative_to(PLAYGROUND_ROOT))
            date_str = f.stem  # YYYY-MM-DD
            found.append((rel, source_type, date_str))
    return found


def extract_tag_from_heading(text):
    """Extract last backtick-tagged word from a heading. Returns (clean_title, tag)."""
    match = re.search(r"`([^`]+)`\s*$", text)
    if match:
        tag = match.group(1)
        title = text[: match.start()].strip()
        return title, tag
    return text.strip(), ""


def extract_author(text):
    """Extract author name from ## heading text (after stripping ## prefix)."""
    # Remove all trailing backtick tags like `AI/ML` `Business`
    cleaned = re.sub(r"(`[^`]+`\s*)+$", "", text).strip()
    return cleaned


def parse_summary_file(filepath, source_type, date_str, rel_path):
    """Parse a summary markdown file into a list of chunk dicts."""
    chunks = []
    lines = filepath.read_text(encoding="utf-8").splitlines()

    current_author = None
    current_title = None
    current_tag = ""
    current_bullets = []
    chunk_index = 0

    def flush_chunk():
        nonlocal chunk_index
        if current_title and current_bullets:
            text = (
                f"{current_title}\n"
                f"{current_author or ''}\n"
                + "\n".join(f"- {b}" for b in current_bullets)
            )
            doc_id = f"{rel_path}::{chunk_index}"
            chunks.append(
                {
                    "id": doc_id,
                    "text": text,
                    "metadata": {
                        "source_type": source_type,
                        "date": date_str,
                        "author": current_author or "",
                        "title": current_title,
                        "tag": current_tag,
                        "file": rel_path,
                    },
                }
            )
            chunk_index += 1

    for line in lines:
        if line.startswith("## "):
            flush_chunk()
            current_author = extract_author(line[3:])
            current_title = None
            current_tag = ""
            current_bullets = []
        elif line.startswith("### "):
            flush_chunk()
            current_title, current_tag = extract_tag_from_heading(line[4:])
            current_bullets = []
        elif line.startswith("- ") and current_title is not None:
            current_bullets.append(line[2:].strip())

    flush_chunk()
    return chunks


def index_new_files(verbose=True):
    """
    Discover and index any summary files not yet tracked in indexed.json.
    Returns (new_file_count, new_chunk_count).
    """
    state = load_indexed_state()
    indexed_set = set(state["indexed_files"])

    all_files = discover_summary_files()
    new_files = [(rel, src, date) for rel, src, date in all_files if rel not in indexed_set]

    if not new_files:
        return 0, 0

    all_chunks = []
    for rel, source_type, date_str in new_files:
        filepath = PLAYGROUND_ROOT / rel
        chunks = parse_summary_file(filepath, source_type, date_str, rel)
        all_chunks.extend(chunks)

    if all_chunks:
        model = get_model()
        embeddings = model.encode(
            [c["text"] for c in all_chunks], show_progress_bar=False
        ).tolist()

        collection = get_collection()
        collection.upsert(
            ids=[c["id"] for c in all_chunks],
            embeddings=embeddings,
            documents=[c["text"] for c in all_chunks],
            metadatas=[c["metadata"] for c in all_chunks],
        )

    state["indexed_files"].extend(rel for rel, _, _ in new_files)
    save_indexed_state(state)

    if verbose:
        nl = sum(1 for _, s, _ in new_files if s == "newsletter")
        tw = sum(1 for _, s, _ in new_files if s == "twitter")
        print(
            f"Indexed {len(new_files)} new file(s) "
            f"({nl} newsletter, {tw} twitter) → {len(all_chunks)} chunks"
        )

    return len(new_files), len(all_chunks)


if __name__ == "__main__":
    print("Building index...")
    files, chunks = index_new_files(verbose=True)
    if files == 0:
        state = load_indexed_state()
        total = get_collection().count()
        print(
            f"No new files. Index contains {total} chunk(s) "
            f"across {len(state['indexed_files'])} file(s)."
        )
    else:
        total = get_collection().count()
        print(f"Done. Index now contains {total} total chunk(s).")
