# Book Network Visualization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Segment a user's book library by TF-IDF similarity on descriptions + tags, cluster them, and display an interactive force-directed network graph with cluster hulls, zoom/pan, and click-to-inspect tooltips.

**Architecture:** Backend adds a segmentation service (scikit-learn TF-IDF + agglomerative clustering) and a single `GET /network` endpoint. Frontend adds a new `/network` page using D3 force layout with cluster hulls rendered as convex hull paths on SVG.

**Tech Stack:** Python/scikit-learn (backend), D3 modules: d3-force, d3-zoom, d3-selection, d3-shape, d3-scale (frontend)

---

## File Structure

### Backend — new files
- `backend/app/services/segmentation.py` — TF-IDF vectorization, clustering, graph building
- `backend/app/routers/network.py` — `GET /network` endpoint
- `backend/tests/test_segmentation.py` — unit tests for segmentation service

### Backend — modified files
- `backend/app/schemas.py` — add `NetworkNode`, `NetworkEdge`, `NetworkCluster`, `NetworkResponse`
- `backend/app/main.py` — register network router
- `backend/pyproject.toml` — add `scikit-learn` dependency

### Frontend — new files
- `frontend/src/api/network.ts` — API client + useNetwork hook
- `frontend/src/pages/Network.tsx` — page component
- `frontend/src/components/NetworkGraph.tsx` — D3 force graph with cluster hulls
- `frontend/src/components/BookTooltip.tsx` — click-locked tooltip

### Frontend — modified files
- `frontend/src/App.tsx` — add `/network` route
- `frontend/src/components/AppShell.tsx` — add "Network" nav link

---

## Task 1: Add scikit-learn dependency

**Files:**
- Modify: `backend/pyproject.toml:6-20`

- [ ] **Step 1: Add scikit-learn to dependencies**

In `backend/pyproject.toml`, add `"scikit-learn>=1.5"` to the `dependencies` list. The result should be:

```toml
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "sqlalchemy[asyncio]>=2.0.30",
    "asyncpg>=0.29",
    "alembic>=1.13",
    "pydantic>=2.7",
    "pydantic-settings>=2.3",
    "python-jose[cryptography]>=3.3",
    "passlib[bcrypt]>=1.7.4",
    "bcrypt>=4.1,<5",
    "python-multipart>=0.0.9",
    "httpx>=0.27",
    "anthropic>=0.40",
    "email-validator>=2.2",
    "scikit-learn>=1.5",
]
```

- [ ] **Step 2: Install the dependency**

Run: `cd backend && pip install -e .`
Expected: scikit-learn installs successfully.

- [ ] **Step 3: Verify import works**

Run: `python -c "from sklearn.feature_extraction.text import TfidfVectorizer; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add backend/pyproject.toml
git commit -m "chore: add scikit-learn dependency for book segmentation"
```

---

## Task 2: Add network response schemas

**Files:**
- Modify: `backend/app/schemas.py`

- [ ] **Step 1: Add the network schemas**

Append to the end of `backend/app/schemas.py`, after the `RecommendationsResponse` class:

```python
# ---------- Network / Segmentation ----------


class NetworkNode(BaseModel):
    id: UUID
    title: str
    author: str
    cluster: int
    tags: list[str]
    description: str | None
    rating: int | None
    cover_url: str | None


class NetworkEdge(BaseModel):
    source: UUID
    target: UUID
    weight: float


class NetworkCluster(BaseModel):
    id: int
    label: str
    color: str


class NetworkResponse(BaseModel):
    clusters: list[NetworkCluster]
    nodes: list[NetworkNode]
    edges: list[NetworkEdge]
```

- [ ] **Step 2: Verify the module still imports**

Run: `cd backend && python -c "from app.schemas import NetworkResponse; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas.py
git commit -m "feat(schemas): add network graph response types"
```

---

## Task 3: Write segmentation service tests

**Files:**
- Create: `backend/tests/test_segmentation.py`

- [ ] **Step 1: Write the test file**

Create `backend/tests/test_segmentation.py`:

```python
from app.services.segmentation import build_network_graph, BookData


def _book(id: str, title: str, author: str, description: str, tags: list[str]) -> BookData:
    return BookData(
        id=id,
        title=title,
        author=author,
        description=description,
        tags=tags,
        rating=None,
        cover_url=None,
    )


SCIFI_A = _book("aaa", "Dune", "Herbert", "desert planet spice worms empire", ["scifi", "space-opera"])
SCIFI_B = _book("bbb", "Neuromancer", "Gibson", "cyberspace hacking matrix AI", ["scifi", "cyberpunk"])
FANTASY_A = _book("ccc", "Name of the Wind", "Rothfuss", "magic university wizard music", ["fantasy", "magic"])
FANTASY_B = _book("ddd", "Way of Kings", "Sanderson", "knights magic war stormlight", ["fantasy", "epic"])
HISTORY = _book("eee", "Sapiens", "Harari", "human history civilization evolution", ["nonfiction", "history"])


def test_similar_books_share_cluster():
    result = build_network_graph([SCIFI_A, SCIFI_B, FANTASY_A, FANTASY_B, HISTORY])
    node_clusters = {n.id: n.cluster for n in result.nodes}
    # The two sci-fi books should land in the same cluster
    assert node_clusters["aaa"] == node_clusters["bbb"]
    # The two fantasy books should land in the same cluster
    assert node_clusters["ccc"] == node_clusters["ddd"]


def test_dissimilar_books_different_clusters():
    result = build_network_graph([SCIFI_A, SCIFI_B, FANTASY_A, FANTASY_B, HISTORY])
    node_clusters = {n.id: n.cluster for n in result.nodes}
    # Sci-fi and nonfiction-history should be in different clusters
    assert node_clusters["aaa"] != node_clusters["eee"]


def test_edges_have_positive_weight():
    result = build_network_graph([SCIFI_A, SCIFI_B, FANTASY_A])
    for edge in result.edges:
        assert edge.weight > 0.0


def test_clusters_have_labels():
    result = build_network_graph([SCIFI_A, SCIFI_B, FANTASY_A, FANTASY_B])
    for cluster in result.clusters:
        assert isinstance(cluster.label, str)
        assert len(cluster.label) > 0


def test_clusters_have_colors():
    result = build_network_graph([SCIFI_A, SCIFI_B, FANTASY_A, FANTASY_B])
    for cluster in result.clusters:
        assert cluster.color.startswith("#")
        assert len(cluster.color) == 7


def test_single_book_returns_one_cluster():
    result = build_network_graph([SCIFI_A])
    assert len(result.clusters) == 1
    assert len(result.nodes) == 1
    assert len(result.edges) == 0


def test_two_books_returns_one_cluster_with_edge():
    result = build_network_graph([SCIFI_A, SCIFI_B])
    assert len(result.clusters) == 1
    assert len(result.nodes) == 2
    assert len(result.edges) == 1


def test_book_with_no_description_or_tags():
    bare = _book("fff", "Unknown", "Author", "", [])
    result = build_network_graph([SCIFI_A, SCIFI_B, bare])
    # Should still appear as a node
    ids = {n.id for n in result.nodes}
    assert "fff" in ids
    # Should be in the uncategorized cluster (-1)
    node_clusters = {n.id: n.cluster for n in result.nodes}
    assert node_clusters["fff"] == -1


def test_empty_input():
    result = build_network_graph([])
    assert len(result.clusters) == 0
    assert len(result.nodes) == 0
    assert len(result.edges) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_segmentation.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.segmentation'`

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_segmentation.py
git commit -m "test(segmentation): add unit tests for book network graph builder"
```

---

## Task 4: Implement segmentation service

**Files:**
- Create: `backend/app/services/segmentation.py`

- [ ] **Step 1: Create the segmentation service**

Create `backend/app/services/segmentation.py`:

```python
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
_EDGE_THRESHOLD = 0.15

# Distance threshold for agglomerative clustering.
_CLUSTER_DISTANCE = 1.2


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
        all_books = [b for _, b in has_content] + uncategorized
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
            for b in all_books
        ]
        label = _label_cluster(all_books)
        clusters = [NetworkCluster(id=0, label=label, color=_CLUSTER_PALETTE[0])]

        # Pairwise edges for the content books only.
        edges: list[NetworkEdge] = []
        content_books = [b for _, b in has_content]
        if len(content_books) == 2:
            corpus = [_build_corpus(b) for b in content_books]
            vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
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
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
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
```

- [ ] **Step 2: Run the tests**

Run: `cd backend && python -m pytest tests/test_segmentation.py -v`
Expected: All 9 tests pass.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/segmentation.py
git commit -m "feat(segmentation): implement TF-IDF book clustering service"
```

---

## Task 5: Add network API endpoint

**Files:**
- Create: `backend/app/routers/network.py`
- Modify: `backend/app/main.py:10-39`

- [ ] **Step 1: Create the network router**

Create `backend/app/routers/network.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db import get_session
from ..deps import get_auth_user
from ..models import Book, User
from ..schemas import NetworkResponse
from ..services.segmentation import BookData, build_network_graph
from ..services.serializers import cover_url_for

router = APIRouter(prefix="/network", tags=["network"])


@router.get("", response_model=NetworkResponse)
async def get_network(
    user: User = Depends(get_auth_user),
    session: AsyncSession = Depends(get_session),
) -> NetworkResponse:
    result = await session.execute(
        select(Book)
        .where(Book.user_id == user.id)
        .options(selectinload(Book.tags))
    )
    books = result.scalars().unique().all()

    book_data = [
        BookData(
            id=str(b.id),
            title=b.title,
            author=b.author,
            description=b.description,
            tags=[t.name for t in b.tags],
            rating=b.rating,
            cover_url=cover_url_for(b.cover_image_path),
        )
        for b in books
    ]

    return build_network_graph(book_data)
```

- [ ] **Step 2: Register the router in main.py**

In `backend/app/main.py`, add the import alongside the other router imports (after line 17):

```python
from .routers import network as network_router
```

Then add the router registration (after line 38, the settings router line):

```python
app.include_router(network_router.router, prefix=API_V1)
```

- [ ] **Step 3: Verify the app starts**

Run: `cd backend && python -c "from app.main import app; print('routes:', [r.path for r in app.routes if hasattr(r, 'path') and 'network' in r.path])"`
Expected: Output includes `'/api/v1/network'`

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/network.py backend/app/main.py
git commit -m "feat(api): add GET /network endpoint for book graph"
```

---

## Task 6: Install D3 frontend dependencies

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install D3 modules**

Run: `cd frontend && npm install d3-force d3-zoom d3-selection d3-shape d3-scale d3-polygon`

- [ ] **Step 2: Install type definitions**

Run: `cd frontend && npm install -D @types/d3-force @types/d3-zoom @types/d3-selection @types/d3-shape @types/d3-scale @types/d3-polygon`

- [ ] **Step 3: Verify import**

Run: `cd frontend && node -e "require('d3-force'); console.log('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore: add D3 modules for network visualization"
```

---

## Task 7: Add frontend API client and types

**Files:**
- Modify: `frontend/src/api/types.ts`
- Create: `frontend/src/api/network.ts`

- [ ] **Step 1: Add network types to types.ts**

Append to the end of `frontend/src/api/types.ts`:

```typescript
export interface NetworkNode {
  id: string;
  title: string;
  author: string;
  cluster: number;
  tags: string[];
  description: string | null;
  rating: number | null;
  cover_url: string | null;
}

export interface NetworkEdge {
  source: string;
  target: string;
  weight: number;
}

export interface NetworkCluster {
  id: number;
  label: string;
  color: string;
}

export interface NetworkResponse {
  clusters: NetworkCluster[];
  nodes: NetworkNode[];
  edges: NetworkEdge[];
}
```

- [ ] **Step 2: Create the API client**

Create `frontend/src/api/network.ts`:

```typescript
import { useQuery } from "@tanstack/react-query";
import { api } from "./client";
import { NetworkResponse } from "./types";

export async function fetchNetwork(): Promise<NetworkResponse> {
  const r = await api.get<NetworkResponse>("/network");
  return r.data;
}

export function useNetwork() {
  return useQuery({ queryKey: ["network"], queryFn: fetchNetwork });
}
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/api/network.ts
git commit -m "feat(api): add network graph API client and types"
```

---

## Task 8: Build BookTooltip component

**Files:**
- Create: `frontend/src/components/BookTooltip.tsx`

- [ ] **Step 1: Create the tooltip component**

Create `frontend/src/components/BookTooltip.tsx`:

```tsx
import { Link } from "react-router-dom";
import type { NetworkNode } from "../api/types";

interface Props {
  node: NetworkNode;
  x: number;
  y: number;
  onClose: () => void;
}

export default function BookTooltip({ node, x, y, onClose }: Props) {
  return (
    <div
      className="pointer-events-auto absolute z-50 w-72 rounded-lg border border-zinc-200 bg-white p-4 shadow-lg dark:border-zinc-700 dark:bg-zinc-900"
      style={{ left: x + 12, top: y - 12 }}
    >
      <button
        type="button"
        onClick={onClose}
        className="absolute right-2 top-2 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
        aria-label="Close"
      >
        &times;
      </button>
      <h3 className="pr-6 font-serif text-lg font-semibold leading-tight">
        {node.title}
      </h3>
      <p className="mt-0.5 text-sm text-zinc-500">{node.author}</p>

      {node.rating != null && (
        <p className="mt-1 text-sm text-amber-500">
          {"★".repeat(node.rating)}
          {"☆".repeat(5 - node.rating)}
        </p>
      )}

      {node.tags.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {node.tags.map((tag) => (
            <span
              key={tag}
              className="rounded-full bg-zinc-100 px-2 py-0.5 text-xs text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {node.description && (
        <p className="mt-2 text-xs leading-relaxed text-zinc-600 dark:text-zinc-400">
          {node.description.length > 150
            ? node.description.slice(0, 150) + "…"
            : node.description}
        </p>
      )}

      <Link
        to={`/books/${node.id}`}
        className="mt-3 inline-block text-xs font-medium text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
      >
        View details &rarr;
      </Link>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/BookTooltip.tsx
git commit -m "feat(ui): add BookTooltip component for network graph"
```

---

## Task 9: Build NetworkGraph component

**Files:**
- Create: `frontend/src/components/NetworkGraph.tsx`

- [ ] **Step 1: Create the NetworkGraph component**

Create `frontend/src/components/NetworkGraph.tsx`:

```tsx
import { useEffect, useRef, useState } from "react";
import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  type SimulationLinkDatum,
  type SimulationNodeDatum,
} from "d3-force";
import { select } from "d3-selection";
import { zoom, zoomIdentity } from "d3-zoom";
import { polygonHull } from "d3-polygon";
import type {
  NetworkCluster,
  NetworkEdge,
  NetworkNode,
  NetworkResponse,
} from "../api/types";
import BookTooltip from "./BookTooltip";

interface SimNode extends SimulationNodeDatum {
  id: string;
  data: NetworkNode;
  cluster: number;
}

interface SimLink extends SimulationLinkDatum<SimNode> {
  weight: number;
}

interface Props {
  data: NetworkResponse;
}

export default function NetworkGraph({ data }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const gRef = useRef<SVGGElement>(null);
  const [tooltip, setTooltip] = useState<{
    node: NetworkNode;
    x: number;
    y: number;
  } | null>(null);

  useEffect(() => {
    const svg = svgRef.current;
    const g = gRef.current;
    if (!svg || !g) return;

    const width = svg.clientWidth;
    const height = svg.clientHeight;

    // Build simulation data.
    const clusterMap = new Map(data.clusters.map((c) => [c.id, c]));

    const nodes: SimNode[] = data.nodes.map((n) => ({
      id: n.id,
      data: n,
      cluster: n.cluster,
    }));

    const nodeMap = new Map(nodes.map((n) => [n.id, n]));

    const links: SimLink[] = data.edges
      .filter((e) => nodeMap.has(e.source) && nodeMap.has(e.target))
      .map((e) => ({
        source: e.source,
        target: e.target,
        weight: e.weight,
      }));

    // Force simulation.
    const sim = forceSimulation(nodes)
      .force(
        "link",
        forceLink<SimNode, SimLink>(links)
          .id((d) => d.id)
          .strength((d) => d.weight * 0.5)
      )
      .force("charge", forceManyBody().strength(-120))
      .force("center", forceCenter(width / 2, height / 2))
      .force("collide", forceCollide(14));

    // Zoom behavior.
    const zoomBehavior = zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.3, 5])
      .on("zoom", (event) => {
        select(g).attr("transform", event.transform);
      });

    select(svg)
      .call(zoomBehavior)
      .call(zoomBehavior.transform, zoomIdentity)
      .on("click", (event) => {
        // Click on background dismisses tooltip.
        if (event.target === svg) {
          setTooltip(null);
        }
      });

    const gSel = select(g);

    // Clear previous render.
    gSel.selectAll("*").remove();

    // Cluster hull layer (behind everything).
    const hullGroup = gSel.append("g").attr("class", "hulls");

    // Edge layer.
    const linkSel = gSel
      .append("g")
      .attr("class", "links")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", "#94a3b8")
      .attr("stroke-opacity", (d) => Math.min(d.weight, 0.8))
      .attr("stroke-width", (d) => 1 + d.weight * 2);

    // Node layer.
    const nodeSel = gSel
      .append("g")
      .attr("class", "nodes")
      .selectAll("circle")
      .data(nodes)
      .join("circle")
      .attr("r", 8)
      .attr("fill", (d) => clusterMap.get(d.cluster)?.color ?? "#6b7280")
      .attr("stroke", "#fff")
      .attr("stroke-width", 1.5)
      .attr("cursor", "pointer")
      .on("mouseenter", function (_, d) {
        select(this).attr("r", 11).attr("stroke-width", 2.5);
        // Highlight connected edges.
        linkSel
          .attr("stroke", (l) => {
            const s = typeof l.source === "object" ? l.source.id : l.source;
            const t = typeof l.target === "object" ? l.target.id : l.target;
            return s === d.id || t === d.id
              ? clusterMap.get(d.cluster)?.color ?? "#6366f1"
              : "#94a3b8";
          })
          .attr("stroke-opacity", (l) => {
            const s = typeof l.source === "object" ? l.source.id : l.source;
            const t = typeof l.target === "object" ? l.target.id : l.target;
            return s === d.id || t === d.id ? 1 : 0.15;
          });
      })
      .on("mouseleave", function () {
        select(this).attr("r", 8).attr("stroke-width", 1.5);
        linkSel
          .attr("stroke", "#94a3b8")
          .attr("stroke-opacity", (d) => Math.min(d.weight, 0.8));
      })
      .on("click", (event, d) => {
        event.stopPropagation();
        const rect = svg.getBoundingClientRect();
        setTooltip({
          node: d.data,
          x: event.clientX - rect.left,
          y: event.clientY - rect.top,
        });
      });

    // Tick handler — update positions every frame.
    sim.on("tick", () => {
      linkSel
        .attr("x1", (d) => (d.source as SimNode).x!)
        .attr("y1", (d) => (d.source as SimNode).y!)
        .attr("x2", (d) => (d.target as SimNode).x!)
        .attr("y2", (d) => (d.target as SimNode).y!);

      nodeSel.attr("cx", (d) => d.x!).attr("cy", (d) => d.y!);

      // Update cluster hulls.
      hullGroup.selectAll("path").remove();
      const clusterIds = [...new Set(nodes.map((n) => n.cluster))];
      for (const cid of clusterIds) {
        const members = nodes.filter((n) => n.cluster === cid);
        if (members.length < 3) continue;
        const points: [number, number][] = members.map((n) => [n.x!, n.y!]);
        const hull = polygonHull(points);
        if (!hull) continue;
        const color = clusterMap.get(cid)?.color ?? "#6b7280";
        hullGroup
          .append("path")
          .attr("d", `M${hull.map((p) => p.join(",")).join("L")}Z`)
          .attr("fill", color)
          .attr("fill-opacity", 0.08)
          .attr("stroke", color)
          .attr("stroke-opacity", 0.25)
          .attr("stroke-width", 1.5)
          .attr("stroke-linejoin", "round");
      }
    });

    return () => {
      sim.stop();
    };
  }, [data]);

  return (
    <div className="relative h-[calc(100vh-8rem)] w-full overflow-hidden rounded-lg border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
      <svg ref={svgRef} className="h-full w-full">
        <g ref={gRef} />
      </svg>
      {tooltip && (
        <BookTooltip
          node={tooltip.node}
          x={tooltip.x}
          y={tooltip.y}
          onClose={() => setTooltip(null)}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/NetworkGraph.tsx
git commit -m "feat(ui): add NetworkGraph D3 force visualization component"
```

---

## Task 10: Build Network page and wire into app

**Files:**
- Create: `frontend/src/pages/Network.tsx`
- Modify: `frontend/src/App.tsx:1-42`
- Modify: `frontend/src/components/AppShell.tsx:8-13`

- [ ] **Step 1: Create the Network page**

Create `frontend/src/pages/Network.tsx`:

```tsx
import { useNetwork } from "../api/network";
import NetworkGraph from "../components/NetworkGraph";

export default function Network() {
  const { data, isLoading } = useNetwork();

  if (isLoading || !data) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-800 dark:border-zinc-700 dark:border-t-zinc-200" />
      </div>
    );
  }

  if (data.nodes.length < 2) {
    return (
      <div className="space-y-4 animate-fade-in">
        <h1 className="font-serif text-3xl">Network</h1>
        <p className="text-zinc-500">
          Add more books to see your network. You need at least 2 books with
          descriptions or tags.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="flex items-center justify-between">
        <h1 className="font-serif text-3xl">Network</h1>
        <div className="flex gap-2">
          {data.clusters.map((c) => (
            <span
              key={c.id}
              className="flex items-center gap-1.5 rounded-full bg-zinc-100 px-2.5 py-1 text-xs dark:bg-zinc-800"
            >
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: c.color }}
              />
              {c.label}
            </span>
          ))}
        </div>
      </div>
      <NetworkGraph data={data} />
    </div>
  );
}
```

- [ ] **Step 2: Add the route in App.tsx**

In `frontend/src/App.tsx`, add the import after the Settings import (line 9):

```typescript
import Network from "./pages/Network";
```

Then add the route inside the protected Routes block, after the `/stats` route (after line 33):

```tsx
<Route path="/network" element={<Network />} />
```

- [ ] **Step 3: Add nav link in AppShell.tsx**

In `frontend/src/components/AppShell.tsx`, change the `navLinks` array (lines 8-13) to:

```typescript
const navLinks = [
  { to: "/", label: "Home", end: true },
  { to: "/library", label: "Library" },
  { to: "/network", label: "Network" },
  { to: "/stats", label: "Stats" },
  { to: "/settings", label: "Settings" },
];
```

- [ ] **Step 4: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors.

- [ ] **Step 5: Verify the build succeeds**

Run: `cd frontend && npm run build`
Expected: Build completes without errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Network.tsx frontend/src/App.tsx frontend/src/components/AppShell.tsx
git commit -m "feat(ui): add Network page with route and nav link"
```

---

## Task 11: Run full test suite and verify

**Files:** None (verification only)

- [ ] **Step 1: Run backend tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests pass, including the new `test_segmentation.py` tests.

- [ ] **Step 2: Run frontend build**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

- [ ] **Step 3: Final commit (if any fixups needed)**

If any tests failed and required fixes, commit those fixes now.
