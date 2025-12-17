from rdflib import RDF, SDO, SKOS, BNode, Dataset, Literal, Namespace

from prezmanifest.event.syncer import _generate_rdf_patch_body_diff

EX = Namespace("https://example.com/")


def test_simple_blank_node_value_change():
    """Test that only the changed literal value appears in the diff, not the blank node itself."""
    # Create two datasets with the same blank node structure but different literal values
    ds1 = Dataset()
    g1 = ds1.graph(EX.graph1)
    version1 = BNode()
    g1.add((EX.resource, SDO.version, version1))
    g1.add((version1, SDO.value, Literal("commit-abc123")))
    g1.add((version1, SDO.additionalType, EX.GitCommitHash))

    ds2 = Dataset()
    g2 = ds2.graph(EX.graph1)
    version2 = BNode()
    g2.add((EX.resource, SDO.version, version2))
    g2.add((version2, SDO.value, Literal("commit-def456")))
    g2.add((version2, SDO.additionalType, EX.GitCommitHash))

    # Generate the patch
    patch = "".join(_generate_rdf_patch_body_diff(ds2, ds1))

    # The patch should show deletion of old commit and addition of new commit
    assert "D _:" in patch and '<https://schema.org/value> "commit-abc123"' in patch
    assert "A _:" in patch and '<https://schema.org/value> "commit-def456"' in patch

    # Verify both use the same blank node identifier (canonicalization ensures this)
    # Extract the blank node IDs
    import re

    delete_bnode = re.search(
        r'D (_:\w+) <https://schema\.org/value> "commit-abc123"', patch
    )
    add_bnode = re.search(
        r'A (_:\w+) <https://schema\.org/value> "commit-def456"', patch
    )

    assert delete_bnode is not None and add_bnode is not None
    assert delete_bnode.group(1) == add_bnode.group(1), (
        "Same blank node should be used for both operations"
    )


def test_multiple_blank_nodes_with_identical_structure():
    """Test that a single resource change produces minimal diff even with multiple blank nodes."""
    # Dataset 1: One resource with blank node
    ds1 = Dataset()
    g1 = ds1.graph(EX.graph1)

    # Resource with blank node
    version1 = BNode()
    g1.add((EX.resource1, SDO.version, version1))
    g1.add((version1, SDO.additionalType, EX.GitCommitHash))
    g1.add((version1, SDO.value, Literal("v1")))
    g1.add((version1, SDO.dateCreated, Literal("2024-01-01")))

    # Dataset 2: Change only the value, keep other properties
    ds2 = Dataset()
    g2 = ds2.graph(EX.graph1)

    version2 = BNode()
    g2.add((EX.resource1, SDO.version, version2))
    g2.add((version2, SDO.additionalType, EX.GitCommitHash))
    g2.add((version2, SDO.value, Literal("v2")))  # Changed
    g2.add((version2, SDO.dateCreated, Literal("2024-01-01")))  # Unchanged

    patch = "".join(_generate_rdf_patch_body_diff(ds2, ds1))

    # Should only show changes to the value
    assert "D _:" in patch and '<https://schema.org/value> "v1"' in patch
    assert "A _:" in patch and '<https://schema.org/value> "v2"' in patch

    # The dateCreated should not appear in the patch since it didn't change
    # Count changes - we should only see minimal changes
    patch_lines = [
        line
        for line in patch.split("\n")
        if line.startswith("A ") or line.startswith("D ")
    ]

    # Should have exactly 1 delete (old v1) and 1 add (new v2)
    # Other properties should not be touched
    date_changes = [line for line in patch_lines if "2024-01-01" in line]
    assert len(date_changes) == 0, (
        f"Unchanged dateCreated should not appear, but found: {date_changes}"
    )


def test_nested_blank_nodes():
    """Test that nested blank node structures are canonicalized correctly."""
    # Dataset 1: Nested blank nodes
    ds1 = Dataset()
    g1 = ds1.graph(EX.graph1)

    outer1 = BNode()
    inner1 = BNode()
    g1.add((EX.resource, EX.metadata, outer1))
    g1.add((outer1, EX.version, inner1))
    g1.add((inner1, SDO.value, Literal("v1")))
    g1.add((inner1, SDO.dateCreated, Literal("2024-01-01")))

    # Dataset 2: Same nested structure, different inner value
    ds2 = Dataset()
    g2 = ds2.graph(EX.graph1)

    outer2 = BNode()
    inner2 = BNode()
    g2.add((EX.resource, EX.metadata, outer2))
    g2.add((outer2, EX.version, inner2))
    g2.add((inner2, SDO.value, Literal("v2")))  # Changed
    g2.add((inner2, SDO.dateCreated, Literal("2024-01-01")))  # Unchanged

    patch = "".join(_generate_rdf_patch_body_diff(ds2, ds1))

    # Should only show the changed value, not recreate the entire blank node structure
    assert "D _:" in patch and '"v1"' in patch
    assert "A _:" in patch and '"v2"' in patch

    # The dateCreated should not appear in additions/deletions since it didn't change
    patch_lines = [
        line
        for line in patch.split("\n")
        if line.startswith("A ") or line.startswith("D ")
    ]
    date_changes = [line for line in patch_lines if "2024-01-01" in line]
    assert len(date_changes) == 0, (
        f"Unchanged dateCreated should not appear, but found: {date_changes}"
    )


def test_blank_node_list_structure():
    """Test that RDF list structures using blank nodes are handled correctly."""
    # Dataset 1: A simple two-element list
    ds1 = Dataset()
    g1 = ds1.graph(EX.graph1)

    # Create an RDF list structure
    list_node1 = BNode()
    g1.add((EX.resource, EX.hasParts, list_node1))
    g1.add((list_node1, RDF.first, Literal("part1")))

    list_node2 = BNode()
    g1.add((list_node1, RDF.rest, list_node2))
    g1.add((list_node2, RDF.first, Literal("part2")))
    g1.add((list_node2, RDF.rest, RDF.nil))

    # Dataset 2: Same list structure, but we add a third element
    ds2 = Dataset()
    g2 = ds2.graph(EX.graph1)

    new_list_node1 = BNode()
    g2.add((EX.resource, EX.hasParts, new_list_node1))
    g2.add((new_list_node1, RDF.first, Literal("part1")))

    new_list_node2 = BNode()
    g2.add((new_list_node1, RDF.rest, new_list_node2))
    g2.add((new_list_node2, RDF.first, Literal("part2")))

    # Add third element
    new_list_node3 = BNode()
    g2.add((new_list_node2, RDF.rest, new_list_node3))
    g2.add((new_list_node3, RDF.first, Literal("part3")))
    g2.add((new_list_node3, RDF.rest, RDF.nil))

    patch = "".join(_generate_rdf_patch_body_diff(ds2, ds1))

    # The patch should show the structural change to the list
    # Old: node2 -> nil, New: node2 -> node3 -> nil
    assert "part3" in patch  # New element added
    assert "A _:" in patch  # Additions for new structure

    # Verify that part1 and part2 are preserved in some form
    # (they might appear in the patch as the list structure changes)
    assert "TX ." in patch and "TC ." in patch  # Valid patch structure


def test_blank_node_across_multiple_graphs():
    """Test that blank nodes in different named graphs are handled correctly."""
    # Dataset 1: Blank nodes in two different graphs
    ds1 = Dataset()

    g1a = ds1.graph(EX.graphA)
    version1a = BNode()
    g1a.add((EX.resourceA, SDO.version, version1a))
    g1a.add((version1a, SDO.value, Literal("v1")))

    g1b = ds1.graph(EX.graphB)
    version1b = BNode()
    g1b.add((EX.resourceB, SDO.version, version1b))
    g1b.add((version1b, SDO.value, Literal("v1")))

    # Dataset 2: Change value in graphA only
    ds2 = Dataset()

    g2a = ds2.graph(EX.graphA)
    version2a = BNode()
    g2a.add((EX.resourceA, SDO.version, version2a))
    g2a.add((version2a, SDO.value, Literal("v2")))  # Changed

    g2b = ds2.graph(EX.graphB)
    version2b = BNode()
    g2b.add((EX.resourceB, SDO.version, version2b))
    g2b.add((version2b, SDO.value, Literal("v1")))  # Unchanged

    patch = "".join(_generate_rdf_patch_body_diff(ds2, ds1))

    # Should show changes in graphA only
    assert "<https://example.com/graphA>" in patch
    assert '"v2"' in patch

    # Count changes - should be minimal (only the changed value)
    patch_lines = patch.split("\n")
    graphA_changes = [line for line in patch_lines if "graphA" in line]
    graphB_changes = [line for line in patch_lines if "graphB" in line]

    # GraphA should have changes (delete old v1, add new v2)
    assert len(graphA_changes) >= 2, "GraphA should show deletions and additions"
    # GraphB should have no changes
    assert len(graphB_changes) == 0, "GraphB should have no changes"


def test_complex_skos_concept_with_blank_nodes():
    """Test a realistic scenario with SKOS concepts containing blank node annotations."""
    # Dataset 1: SKOS concept with blank node for editorial note
    ds1 = Dataset()
    g1 = ds1.graph(EX.vocabulary)

    concept = EX.someConcept
    g1.add((concept, RDF.type, SKOS.Concept))
    g1.add((concept, SKOS.prefLabel, Literal("Some Concept", lang="en")))

    # Editorial note as a blank node with metadata
    note1 = BNode()
    g1.add((concept, SKOS.editorialNote, note1))
    g1.add((note1, RDF.value, Literal("This concept needs review")))
    g1.add((note1, SDO.author, Literal("Editor A")))
    g1.add((note1, SDO.dateCreated, Literal("2024-01-01")))

    # Dataset 2: Update the editorial note content
    ds2 = Dataset()
    g2 = ds2.graph(EX.vocabulary)

    g2.add((concept, RDF.type, SKOS.Concept))
    g2.add((concept, SKOS.prefLabel, Literal("Some Concept", lang="en")))

    note2 = BNode()
    g2.add((concept, SKOS.editorialNote, note2))
    g2.add((note2, RDF.value, Literal("This concept has been reviewed")))  # Changed
    g2.add((note2, SDO.author, Literal("Editor A")))  # Unchanged
    g2.add((note2, SDO.dateCreated, Literal("2024-01-01")))  # Unchanged

    patch = "".join(_generate_rdf_patch_body_diff(ds2, ds1))

    # Should only show the changed note value
    assert "D _:" in patch and '"This concept needs review"' in patch
    assert "A _:" in patch and '"This concept has been reviewed"' in patch

    # The unchanged triples (author, dateCreated) should not appear as changes
    patch_lines = [
        line
        for line in patch.split("\n")
        if line.startswith("A ") or line.startswith("D ")
    ]
    author_changes = [line for line in patch_lines if "Editor A" in line]
    date_changes = [line for line in patch_lines if "2024-01-01" in line]

    assert len(author_changes) == 0, (
        f"Unchanged author should not appear, but found: {author_changes}"
    )
    assert len(date_changes) == 0, (
        f"Unchanged dateCreated should not appear, but found: {date_changes}"
    )


def test_blank_node_identity_preservation():
    """Test that semantically identical blank nodes get the same canonical identifier.

    This demonstrates the core benefit of canonicalization: blank nodes that represent
    the same logical entity across datasets will be assigned the same identifier,
    preventing spurious diffs.
    """
    # Create two identical datasets with different blank node creation order
    ds1 = Dataset()
    g1 = ds1.graph(EX.graph1)

    # Create blank nodes in one order
    b1_v1 = BNode()  # Will get some internal ID
    b1_v2 = BNode()  # Will get a different internal ID
    g1.add((EX.res1, SDO.version, b1_v1))
    g1.add((b1_v1, SDO.value, Literal("value1")))
    g1.add((EX.res2, SDO.version, b1_v2))
    g1.add((b1_v2, SDO.value, Literal("value2")))

    ds2 = Dataset()
    g2 = ds2.graph(EX.graph1)

    # Create blank nodes in reverse order - different internal IDs
    b2_v2 = BNode()  # Different internal ID than b1_v2
    b2_v1 = BNode()  # Different internal ID than b1_v1
    g2.add((EX.res2, SDO.version, b2_v2))
    g2.add((b2_v2, SDO.value, Literal("value2")))
    g2.add((EX.res1, SDO.version, b2_v1))
    g2.add((b2_v1, SDO.value, Literal("value1")))

    # Despite different creation order and internal IDs, the graphs are semantically identical
    patch = "".join(_generate_rdf_patch_body_diff(ds2, ds1))

    # The patch should show NO changes (empty transaction)
    assert "TX ." in patch
    assert "TC ." in patch

    # Extract the body between TX and TC
    tx_pos = patch.find("TX .")
    tc_pos = patch.find("TC .")
    body = patch[tx_pos + len("TX .") : tc_pos].strip()

    # Should be empty (no additions or deletions)
    assert body == "", f"Expected empty patch body but got: {body}"
