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
    assert node_clusters["aaa"] == node_clusters["bbb"]
    assert node_clusters["ccc"] == node_clusters["ddd"]


def test_dissimilar_books_different_clusters():
    result = build_network_graph([SCIFI_A, SCIFI_B, FANTASY_A, FANTASY_B, HISTORY])
    node_clusters = {n.id: n.cluster for n in result.nodes}
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
    ids = {n.id for n in result.nodes}
    assert "fff" in ids
    node_clusters = {n.id: n.cluster for n in result.nodes}
    assert node_clusters["fff"] == -1


def test_empty_input():
    result = build_network_graph([])
    assert len(result.clusters) == 0
    assert len(result.nodes) == 0
    assert len(result.edges) == 0
