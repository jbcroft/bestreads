# Book Network Visualization — Design Spec

## Overview

Segment a user's book library algorithmically using TF-IDF similarity on descriptions and tags, group books into clusters, and display them in an interactive force-directed network graph with cluster hulls, zoom/pan, and click-to-inspect tooltips.

## Architecture

### Backend

**New files:**
- `backend/app/services/segmentation.py` — segmentation service
- `backend/app/routers/network.py` — API endpoint
- `backend/tests/test_segmentation.py` — unit tests

**New dependency:** `scikit-learn` added to `pyproject.toml`

### Frontend

**New files:**
- `frontend/src/pages/Network.tsx` — page component
- `frontend/src/components/NetworkGraph.tsx` — D3 force graph
- `frontend/src/components/BookTooltip.tsx` — click-locked tooltip

**New dependencies:** `d3-force`, `d3-zoom`, `d3-selection`, `d3-shape`, `d3-scale` (individual modules, not full d3)

## Backend: Segmentation Service

`services/segmentation.py` — pure function, no database access. Receives a list of books with their tags, returns graph data.

### Algorithm

1. **Build corpus** — for each book, concatenate `description` (or empty string) with tag names joined by spaces. This gives TF-IDF both the rich prose from descriptions and the structured vocabulary from tags.

2. **TF-IDF vectorize** — `TfidfVectorizer` from scikit-learn with English stop words, 1-2 word n-grams. Produces a sparse matrix of book vectors.

3. **Cosine similarity matrix** — compute pairwise cosine similarity from the TF-IDF matrix. Only emit edges where similarity > 0.15.

4. **Agglomerative clustering** — `AgglomerativeClustering` with `distance_threshold=1.2`, `n_clusters=None`. Adapts to library size: a 10-book library might get 2-3 clusters, a 100-book library 8-12.

5. **Cluster labeling** — for each cluster, find the top 2-3 most frequent tags across its member books and join them as the label (e.g. "sci-fi / dystopia").

6. **Cluster coloring** — assign from a fixed palette of 10 distinguishable colors, cycling if more clusters exist.

### Edge Cases

- **Books with no description and no tags:** Assign to a special "uncategorized" cluster (id: -1). They appear as nodes but won't have meaningful edges.
- **Fewer than 3 books:** Skip clustering, return all books in a single cluster with all pairwise edges.

### Function Signature

```python
def build_network_graph(books: list[BookData]) -> NetworkGraph:
    """Build segmentation graph from a list of books.

    BookData is a simple dataclass/TypedDict with: id, title, author,
    description, tags (list[str]), rating, cover_url.

    Returns NetworkGraph with clusters, nodes, edges.
    """
```

## Backend: API Endpoint

`routers/network.py` — single endpoint.

### `GET /network`

- Authenticated (same `get_auth_user` dependency).
- Fetches all books for the user with tags eagerly loaded.
- Passes them to the segmentation service.
- Returns `NetworkResponse`.

No pagination — operates on the full user library (bounded, typically < a few hundred books). Computation is lightweight (TF-IDF + clustering on < 1000 docs is milliseconds), so no caching needed initially.

### Response Schema

```python
class NetworkNode(BaseModel):
    id: UUID
    title: str
    author: str
    cluster: int
    tags: list[str]
    description: str | None  # truncated to 200 chars
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

## Frontend: Network Page

`pages/Network.tsx` — route `/network`, nav label "Network".

- `useQuery` to fetch `GET /network`.
- Loading spinner while fetching.
- Empty state if fewer than 2 books: "Add more books to see your network."
- Passes graph data to `NetworkGraph` component.

### Navigation

Add "Network" entry to the main nav alongside Library, Stats, etc.

## Frontend: NetworkGraph Component

`components/NetworkGraph.tsx` — the D3 force-directed visualization.

### Canvas

- SVG element filling available page area (full width, `calc(100vh - nav height)`).
- Zoom/pan via `d3-zoom`: scroll to zoom, drag to pan. Bounded 0.3x–5x.

### Force Simulation

- `forceLink` — edges pull connected books together, strength scaled by similarity weight.
- `forceManyBody` — repulsion keeps nodes from overlapping.
- `forceCenter` — keeps graph centered in the viewport.
- `forceCollide` — prevents node overlap with a radius buffer.

### Visual Elements

- **Cluster hulls** — for each cluster with 3+ nodes, compute convex hull via `d3-shape polygonHull`. Render as `<path>` with translucent cluster-colored fill and subtle border. Hulls update each simulation tick.
- **Edges** — `<line>` elements, opacity scaled by weight (stronger similarity = more visible), light gray default color.
- **Nodes** — `<circle>` elements, radius ~8px, filled with cluster color, slight border. Hover brightens the node and highlights its connected edges.

### Click Behavior

- Clicking a node locks the tooltip open at that position.
- Clicking the canvas background or another node dismisses the current tooltip.

## Frontend: BookTooltip Component

`components/BookTooltip.tsx` — positioned near the clicked node.

Contents:
- Title (bold)
- Author
- Star rating (if present)
- Tag chips
- Description excerpt (first 150 chars with ellipsis)
- "View details →" link to `/books/:id`

Styled with existing Tailwind theme to match the app.

## Testing

### Backend

- **Unit tests for segmentation service:** Test with fake books that have known overlapping tags/descriptions. Verify cluster assignments group similar books together and edges exist between them.
- **Edge case tests:** Single book, two books, books with no description/tags.
- **Integration test for `GET /network`:** Verify it returns valid `NetworkResponse` shape for an authenticated user.

### Frontend

- Smoke test that `Network.tsx` renders without crashing given mock graph data.
- No unit tests for D3 internals — the force simulation is D3's responsibility.
