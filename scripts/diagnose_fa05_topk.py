from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent import CORPUS_DIR
from bootcamp_agent.documents import load_corpus
from bootcamp_agent.retrieval import retrieve


QUESTION = "Which layered defenses help against prompt injection in retrieved documents?"


def main() -> None:
    documents = load_corpus(CORPUS_DIR)

    for top_k in (3, 4, 5):
        results = retrieve(QUESTION, documents, top_k=top_k)

        print(f"\nTOP_K={top_k}")

        for rank, result in enumerate(results, 1):
            chunk = result.chunk
            preview = chunk.text[:300].replace("\n", " ")

            print(
                f"  {rank}. "
                f"doc={chunk.doc_id!r} "
                f"position={chunk.position} "
                f"score={result.score:.4f}"
            )
            print(f"     {preview}")


if __name__ == "__main__":
    main()