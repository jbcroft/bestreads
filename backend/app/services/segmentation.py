"""Book segmentation service.

Builds a network graph from a user's books using TF-IDF similarity
on descriptions + tags, with agglomerative clustering.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..schemas import NetworkCluster, NetworkEdge, NetworkNode, NetworkResponse

# 10 visually distinct colors for cluster assignment, cycling if needed.
_CLUSTER_PALETTE = [
    "#6366f1",  # indigo
    "#10b981",  # emerald
    "#f59e0b",  # amber
    "#ef4444",  # red
    "#3b82f6",  # blue
    "#8b5cf6",  # violet
    "#ec4899",  # pink
    "#14b8a6",  # teal
    "#f97316",  # orange
    "#84cc16",  # lime
]

_UNCATEGORIZED_COLOR = "#6b7280"  # gray

# Similarity threshold — only emit edges above this value.
_EDGE_THRESHOLD = 0.05

# Distance threshold for agglomerative clustering.
_CLUSTER_DISTANCE = 1.0


@dataclass
class BookData:
    id: str
    title: str
    author: str
    description: str | None
    tags: list[str]
    rating: int | None
    cover_url: str | None


def _build_corpus(book: BookData) -> str:
    """Concatenate description and tag names into a single text document."""
    parts: list[str] = []
    if book.description:
        parts.append(book.description)
    if book.tags:
        parts.append(" ".join(book.tags))
    return " ".join(parts)


def _label_cluster(books: list[BookData]) -> str:
    """Derive a human-readable label from the most frequent tags in a cluster."""
    tag_counts: Counter[str] = Counter()
    for book in books:
        for tag in book.tags:
            tag_counts[tag] += 1
    top = tag_counts.most_common(3)
    if not top:
        return "uncategorized"
    return " / ".join(tag for tag, _ in top)


def build_network_graph(books: list[BookData]) -> NetworkResponse:
    """Build a segmentation graph from a list of books.

    Returns a NetworkResponse with clusters, nodes, and similarity edges.
    """
    if not books:
        return NetworkResponse(clusters=[], nodes=[], edges=[])

    # Separate books with content from those without.
    has_content: list[tuple[int, BookData]] = []
    uncategorized: list[BookData] = []

    for i, book in enumerate(books):
        corpus = _build_corpus(book)
        if corpus.strip():
            has_content.append((i, book))
        else:
            uncategorized.append(book)

    # For fewer than 3 books with content, skip clustering — single cluster.
    if len(has_content) < 3:
        content_books = [b for _, b in has_content]
        nodes = [
            NetworkNode(
                id=b.id,
                title=b.title,
                author=b.author,
                cluster=0,
                tags=b.tags,
                description=(b.description or "")[:200] or None,
                rating=b.rating,
                cover_url=b.cover_url,
            )
            for b in content_books
        ]
        # Uncategorized books get cluster -1.
        for b in uncategorized:
            nodes.append(
                NetworkNode(
                    id=b.id,
                    title=b.title,
                    author=b.author,
                    cluster=-1,
                    tags=b.tags,
                    description=(b.description or "")[:200] or None,
                    rating=b.rating,
                    cover_url=b.cover_url,
                )
            )
        label = _label_cluster(content_books)
        clusters: list[NetworkCluster] = [NetworkCluster(id=0, label=label, color=_CLUSTER_PALETTE[0])]
        if uncategorized:
            clusters.append(
                NetworkCluster(id=-1, label="uncategorized", color=_UNCATEGORIZED_COLOR)
            )

        # Pairwise edges for the content books only.
        edges: list[NetworkEdge] = []
        if len(content_books) == 2:
            corpus = [_build_corpus(b) for b in content_books]
            vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 1))
            tfidf = vec.fit_transform(corpus)
            sim = cosine_similarity(tfidf)[0, 1]
            if sim > _EDGE_THRESHOLD:
                edges.append(
                    NetworkEdge(
                        source=content_books[0].id,
                        target=content_books[1].id,
                        weight=round(float(sim), 4),
                    )
                )

        return NetworkResponse(clusters=clusters, nodes=nodes, edges=edges)

    # --- Main path: 3+ books with content ---

    corpus = [_build_corpus(b) for _, b in has_content]
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 1))
    tfidf_matrix = vectorizer.fit_transform(corpus)

    # Cosine similarity matrix.
    sim_matrix = cosine_similarity(tfidf_matrix)

    # Agglomerative clustering with distance threshold (auto cluster count).
    # sklearn needs a distance matrix; cosine distance = 1 - similarity.
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=_CLUSTER_DISTANCE,
        metric="precomputed",
        linkage="average",
    )
    distance_matrix = 1.0 - sim_matrix
    labels = clustering.fit_predict(distance_matrix)

    # Build cluster metadata.
    cluster_ids = sorted(set(labels))
    cluster_books: dict[int, list[BookData]] = {cid: [] for cid in cluster_ids}
    for idx, (_, book) in enumerate(has_content):
        cluster_books[int(labels[idx])].append(book)

    clusters: list[NetworkCluster] = []
    for cid in cluster_ids:
        clusters.append(
            NetworkCluster(
                id=int(cid),
                label=_label_cluster(cluster_books[cid]),
                color=_CLUSTER_PALETTE[int(cid) % len(_CLUSTER_PALETTE)],
            )
        )

    # Add uncategorized cluster if needed.
    if uncategorized:
        clusters.append(
            NetworkCluster(id=-1, label="uncategorized", color=_UNCATEGORIZED_COLOR)
        )

    # Build nodes.
    nodes: list[NetworkNode] = []
    for idx, (_, book) in enumerate(has_content):
        nodes.append(
            NetworkNode(
                id=book.id,
                title=book.title,
                author=book.author,
                cluster=int(labels[idx]),
                tags=book.tags,
                description=(book.description or "")[:200] or None,
                rating=book.rating,
                cover_url=book.cover_url,
            )
        )
    for book in uncategorized:
        nodes.append(
            NetworkNode(
                id=book.id,
                title=book.title,
                author=book.author,
                cluster=-1,
                tags=book.tags,
                description=(book.description or "")[:200] or None,
                rating=book.rating,
                cover_url=book.cover_url,
            )
        )

    # Build edges — only pairs above the similarity threshold.
    edges: list[NetworkEdge] = []
    n = len(has_content)
    for i in range(n):
        for j in range(i + 1, n):
            w = float(sim_matrix[i, j])
            if w > _EDGE_THRESHOLD:
                edges.append(
                    NetworkEdge(
                        source=has_content[i][1].id,
                        target=has_content[j][1].id,
                        weight=round(w, 4),
                    )
                )

    return NetworkResponse(clusters=clusters, nodes=nodes, edges=edges)
