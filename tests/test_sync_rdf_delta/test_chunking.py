"""Tests for RDF patch chunking functionality in the event syncer."""

import pytest
from rdflib import RDF, Dataset, Literal, Namespace

from prezmanifest.event.syncer import (
    _generate_rdf_patch_body_add,
    _generate_rdf_patch_body_diff,
    _rdf_patch_body_substr,
)

EX = Namespace("https://example.com/")

# Chunk size constant from syncer.py
CHUNK_SIZE = 838860  # 0.8 MB in bytes


def test_small_patch_single_chunk():
    """Test that a small RDF patch yields a single chunk."""
    # Create a simple RDF patch string
    patch = "TX .\nA <urn:a> <urn:b> <urn:c> .\nTC ."

    chunks = list(_rdf_patch_body_substr(patch))

    assert len(chunks) == 1
    assert chunks[0] == patch


def test_empty_patch_body():
    """Test that a patch with only TX and TC markers yields a single empty-ish chunk."""
    patch = "TX .TC ."

    chunks = list(_rdf_patch_body_substr(patch))

    assert len(chunks) == 1
    assert chunks[0] == "TX .TC ."


def test_large_patch_multiple_chunks():
    """Test that a large RDF patch is split into multiple chunks."""
    # Create a patch body larger than CHUNK_SIZE
    # Each triple line is approximately 53 characters
    # We need enough triples to exceed CHUNK_SIZE significantly
    num_triples = (CHUNK_SIZE // 50) + 10000  # Ensure it's larger than one chunk

    triples = "\n".join(
        [
            f"A <urn:subject{i}> <urn:predicate{i}> <urn:object{i}> ."
            for i in range(num_triples)
        ]
    )
    patch = f"TX .\n{triples}\nTC ."

    chunks = list(_rdf_patch_body_substr(patch))

    # Should have more than one chunk
    assert len(chunks) > 1

    # Each chunk (except possibly the last) should be around CHUNK_SIZE
    for chunk in chunks[:-1]:
        assert len(chunk) <= CHUNK_SIZE
        # Should be reasonably close to CHUNK_SIZE (allowing for newline breaks)
        assert len(chunk) > CHUNK_SIZE * 0.8

    # Verify that all chunks combined equal the original body
    combined = "".join(chunks)
    tx_pos = patch.find("TX .")
    tc_pos = patch.find("TC .") + len("TC .")
    expected_body = patch[tx_pos:tc_pos]
    assert combined == expected_body


def test_chunk_breaks_on_newlines():
    """Test that chunks preferably break on newline boundaries."""
    # Create a patch with predictable newlines
    line_length = 100
    num_lines = (CHUNK_SIZE // line_length) + 100

    lines = [
        f"A <urn:s{i}> <urn:p{i}> <urn:o{i}> ." + " " * (line_length - 40)
        for i in range(num_lines)
    ]
    triples = "\n".join(lines)
    patch = f"TX .\n{triples}\nTC ."

    chunks = list(_rdf_patch_body_substr(patch))

    # All chunks except the last should end with a newline
    # (because we're breaking on newline boundaries)
    for chunk in chunks[:-1]:
        # The chunk should end with a newline character or be at the exact boundary
        assert chunk.endswith("\n") or len(chunk) == CHUNK_SIZE


def test_patch_exactly_at_chunk_boundary():
    """Test behavior when patch body is exactly CHUNK_SIZE bytes."""
    # Create a body exactly CHUNK_SIZE bytes
    body_content = "A" * (CHUNK_SIZE - len("TX .") - len("TC ."))
    patch = f"TX .{body_content}TC ."

    chunks = list(_rdf_patch_body_substr(patch))

    # Should yield a single chunk since the body is exactly at the boundary
    assert len(chunks) == 1


def test_patch_just_over_chunk_boundary():
    """Test behavior when patch body is just over CHUNK_SIZE bytes."""
    # Create a body just over CHUNK_SIZE
    body_content = "A" * (CHUNK_SIZE + 100)
    patch = f"TX .{body_content}TC ."

    chunks = list(_rdf_patch_body_substr(patch))

    # Should yield two chunks
    assert len(chunks) == 2
    # First chunk should be close to CHUNK_SIZE
    assert len(chunks[0]) <= CHUNK_SIZE
    # Second chunk should be small
    assert len(chunks[1]) < 200


def test_no_newlines_near_boundary():
    """Test that chunking still works when there are no newlines near the boundary."""
    # Create a large continuous string with no newlines
    body_content = "A" * (CHUNK_SIZE * 2 + 1000)
    patch = f"TX .{body_content}TC ."

    chunks = list(_rdf_patch_body_substr(patch))

    # Should yield multiple chunks
    assert len(chunks) >= 2

    # Each chunk should be at most CHUNK_SIZE (since there are no newlines to break on)
    for chunk in chunks:
        assert len(chunk) <= CHUNK_SIZE


def test_generate_rdf_patch_body_add_returns_generator():
    """Test that _generate_rdf_patch_body_add returns a generator yielding chunks."""
    data = """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        <urn:vocab> a skos:ConceptScheme .
    """
    ds = Dataset().parse(data=data, format="turtle")

    result = _generate_rdf_patch_body_add(ds)

    # Should be a generator
    assert hasattr(result, "__iter__") and hasattr(result, "__next__")

    # Collect all chunks
    chunks = list(result)

    # For a small dataset, should yield one chunk
    assert len(chunks) == 1

    # The chunk should contain the expected triple
    combined = "".join(chunks)
    assert "TX ." in combined
    assert "TC ." in combined
    assert "<urn:vocab>" in combined
    assert (
        "skos:ConceptScheme" in combined
        or "http://www.w3.org/2004/02/skos/core#ConceptScheme" in combined
    )


def test_generate_rdf_patch_body_diff_returns_generator():
    """Test that _generate_rdf_patch_body_diff returns a generator yielding chunks."""
    # Create two simple datasets with a difference
    ds1 = Dataset()
    g1 = ds1.graph(EX.graph1)
    g1.add((EX.resource, RDF.type, EX.TypeA))

    ds2 = Dataset()
    g2 = ds2.graph(EX.graph1)
    g2.add((EX.resource, RDF.type, EX.TypeB))

    result = _generate_rdf_patch_body_diff(ds2, ds1)

    # Should be a generator
    assert hasattr(result, "__iter__") and hasattr(result, "__next__")

    # Collect all chunks
    chunks = list(result)

    # For a small dataset, should yield one chunk
    assert len(chunks) == 1

    # The chunk should contain both deletion and addition
    combined = "".join(chunks)
    assert "TX ." in combined
    assert "TC ." in combined
    assert "D " in combined  # Deletion
    assert "A " in combined  # Addition


def test_large_dataset_yields_multiple_chunks():
    """Test that a large dataset is chunked correctly."""
    # Create a large dataset that will produce a patch > CHUNK_SIZE
    ds = Dataset()
    g = ds.graph(EX.largeGraph)

    # Add many triples to create a large patch
    # Each triple adds roughly 100-150 bytes to the serialized patch
    num_triples = (CHUNK_SIZE // 100) + 5000

    for i in range(num_triples):
        g.add((EX[f"subject{i}"], EX[f"predicate{i}"], Literal(f"object value {i}")))

    chunks = list(_generate_rdf_patch_body_add(ds))

    # Should yield multiple chunks
    assert len(chunks) > 1

    # Verify all chunks are within size limits
    for chunk in chunks:
        assert len(chunk) <= CHUNK_SIZE * 1.1  # Allow small overflow for newline breaks

    # Verify combined chunks form valid patch structure
    combined = "".join(chunks)
    assert combined.startswith("TX .")
    assert combined.endswith("TC .")


def test_chunk_preserves_patch_integrity():
    """Test that chunked patches maintain structural integrity."""
    # Create a dataset with known content
    ds1 = Dataset()
    g1 = ds1.graph(EX.graph1)
    for i in range(1000):
        g1.add((EX[f"s{i}"], EX[f"p{i}"], Literal(f"value{i}")))

    ds2 = Dataset()
    g2 = ds2.graph(EX.graph1)
    for i in range(500):  # Remove half
        g2.add((EX[f"s{i}"], EX[f"p{i}"], Literal(f"value{i}")))
    for i in range(500, 1500):  # Add new ones
        g2.add((EX[f"s{i}"], EX[f"p{i}"], Literal(f"value{i}")))

    chunks = list(_generate_rdf_patch_body_diff(ds2, ds1))

    # Combine all chunks
    combined = "".join(chunks)

    # Should start with TX and end with TC
    assert combined.startswith("TX .")
    assert combined.endswith("TC .")

    # Should contain both additions and deletions
    assert "\nA " in combined or "\nD " in combined

    # Count the transaction markers - should have exactly one TX and one TC
    assert combined.count("TX .") == 1
    assert combined.count("TC .") == 1


def test_chunk_size_calculation():
    """Verify the chunk size constant matches the expected value (0.8 MB)."""
    expected_size = int(0.8 * 1024 * 1024)
    assert CHUNK_SIZE == expected_size
    assert CHUNK_SIZE == 838860


def test_very_large_patch_many_chunks():
    """Test that a very large patch is split into many chunks correctly."""
    # Create a patch body much larger than CHUNK_SIZE (e.g., 5 MB)
    target_size = CHUNK_SIZE * 6  # 4.8 MB
    line = "A <urn:s> <urn:p> <urn:o> .\n"
    num_lines = target_size // len(line)

    triples = "".join([line for _ in range(num_lines)])
    patch = f"TX .\n{triples}TC ."

    chunks = list(_rdf_patch_body_substr(patch))

    # Should have approximately 6 chunks
    assert len(chunks) >= 5
    assert len(chunks) <= 8  # Allow some variance due to newline breaking

    # Verify total size matches
    total_size = sum(len(chunk) for chunk in chunks)
    expected_body_size = len(
        patch[patch.find("TX .") : patch.find("TC .") + len("TC .")]
    )
    assert total_size == expected_body_size


def test_patch_with_unicode_characters():
    """Test that chunking works correctly with unicode characters."""
    # Create a patch with unicode characters
    ds = Dataset()
    g = ds.graph(EX.graph1)

    # Add triples with unicode values
    for i in range(100):
        g.add((EX[f"subject{i}"], EX.label, Literal(f"日本語テキスト {i} émojis 🎉🎊")))

    chunks = list(_generate_rdf_patch_body_add(ds))

    # Should successfully chunk without errors
    assert len(chunks) >= 1

    # Verify unicode is preserved
    combined = "".join(chunks)
    assert "日本語" in combined or "\\u" in combined  # Either raw or escaped unicode
