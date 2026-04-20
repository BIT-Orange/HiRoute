"""Generate offline embeddings for objects and queries."""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.dataset_support import load_dataset_manifest, output_path, read_jsonl
from tools.workflow_support import read_csv, write_csv


LOGGER = logging.getLogger("embed_texts")
DEFAULT_DIM = 384


def _format_embedding_vector(vector: np.ndarray) -> str:
    return "|".join(f"{float(value):.8f}" for value in vector.tolist())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/datasets/smartcity_v1.yaml", type=Path)
    parser.add_argument(
        "--backend",
        choices=["auto", "sentence-transformers", "hashing"],
        default="sentence-transformers",
    )
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--batch-size", default=32, type=int)
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def _hashing_encode(texts: list[str], dim: int = DEFAULT_DIM) -> np.ndarray:
    matrix = np.zeros((len(texts), dim), dtype=np.float32)
    for row_index, text in enumerate(texts):
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], "little") % dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            matrix[row_index, bucket] += sign
        norm = float(np.linalg.norm(matrix[row_index]))
        if norm > 0:
            matrix[row_index] /= norm
    return matrix


def _sentence_transformer_encode(texts: list[str], model_name: str, batch_size: int) -> np.ndarray:
    from sentence_transformers import SentenceTransformer  # imported lazily for fallback support

    cache_root = ROOT / "data" / "interim" / "cache" / "huggingface"
    cache_root.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(cache_root))
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(cache_root / "hub"))
    os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", str(cache_root / "sentence_transformers"))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(cache_root / "transformers"))
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    model = SentenceTransformer(model_name)
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=False,
    )
    return embeddings.astype(np.float32)


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    manifest = load_dataset_manifest(args.config)

    object_rows = read_csv(output_path(manifest, "objects_csv"))
    object_texts = {row["object_id"]: row for row in read_jsonl(output_path(manifest, "object_texts_jsonl"))}
    query_rows = read_csv(output_path(manifest, "queries_csv"))

    ordered_objects = sorted(object_rows, key=lambda row: row["object_id"])
    ordered_queries = sorted(query_rows, key=lambda row: row["query_id"])

    object_input = [
        f"{object_texts[row['object_id']]['description_text']} {object_texts[row['object_id']]['metadata_summary']}"
        for row in ordered_objects
    ]
    query_input = [row["query_text"] for row in ordered_queries]

    backend = args.backend
    if backend == "auto":
        try:
            object_embeddings = _sentence_transformer_encode(object_input, args.model, args.batch_size)
            query_embeddings = _sentence_transformer_encode(query_input, args.model, args.batch_size)
            backend = "sentence-transformers"
        except Exception as error:
            LOGGER.warning("falling back to hashing embeddings: %s", error)
            object_embeddings = _hashing_encode(object_input)
            query_embeddings = _hashing_encode(query_input)
            backend = "hashing"
    elif backend == "sentence-transformers":
        object_embeddings = _sentence_transformer_encode(object_input, args.model, args.batch_size)
        query_embeddings = _sentence_transformer_encode(query_input, args.model, args.batch_size)
    else:
        object_embeddings = _hashing_encode(object_input)
        query_embeddings = _hashing_encode(query_input)

    np.save(output_path(manifest, "object_embeddings_npy"), object_embeddings)
    np.save(output_path(manifest, "query_embeddings_npy"), query_embeddings)

    object_index_rows = [
        {
            "object_id": row["object_id"],
            "object_text_id": row["object_text_id"],
            "embedding_row": index,
        }
        for index, row in enumerate(ordered_objects)
    ]
    query_index_rows = [
        {
            "query_id": row["query_id"],
            "query_text_id": row["query_text_id"],
            "embedding_row": index,
        }
        for index, row in enumerate(ordered_queries)
    ]

    write_csv(
        output_path(manifest, "object_embeddings_csv"),
        ["object_id", "object_text_id", "embedding_row", "embedding_vector"],
        [
            {
                **index_row,
                "embedding_vector": _format_embedding_vector(object_embeddings[index]),
            }
            for index, index_row in enumerate(object_index_rows)
        ],
    )
    write_csv(
        output_path(manifest, "query_embeddings_csv"),
        ["query_id", "query_text_id", "embedding_row", "embedding_vector"],
        [
            {
                **index_row,
                "embedding_vector": _format_embedding_vector(query_embeddings[index]),
            }
            for index, index_row in enumerate(query_index_rows)
        ],
    )
    write_csv(
        output_path(manifest, "object_embedding_index_csv"),
        ["object_id", "object_text_id", "embedding_row"],
        object_index_rows,
    )
    write_csv(
        output_path(manifest, "query_embedding_index_csv"),
        ["query_id", "query_text_id", "embedding_row"],
        query_index_rows,
    )
    for bundle_id, bundle in manifest.get("topology", {}).get("query_bundles", {}).items():
        bundle_queries = read_csv(
            (ROOT / bundle["queries_csv"]) if not Path(bundle["queries_csv"]).is_absolute() else Path(bundle["queries_csv"])
        )
        query_ids = {row["query_id"] for row in bundle_queries}
        bundle_index_rows = [
            {
                "query_id": row["query_id"],
                "query_text_id": row["query_text_id"],
                "embedding_row": index,
            }
            for index, row in enumerate(ordered_queries)
            if row["query_id"] in query_ids
        ]
        bundle_index_path = (ROOT / bundle["query_embedding_index_csv"]) if not Path(bundle["query_embedding_index_csv"]).is_absolute() else Path(bundle["query_embedding_index_csv"])
        write_csv(
            bundle_index_path,
            ["query_id", "query_text_id", "embedding_row"],
            bundle_index_rows,
        )
    LOGGER.info(
        "embedded %s objects and %s queries using %s backend",
        len(ordered_objects),
        len(ordered_queries),
        backend,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
