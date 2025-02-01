from pathlib import Path

from typer.testing import CliRunner

from prezmanifest import validate
from prezmanifest.cli import app

runner = CliRunner()


def test_validator_valid():
    assert validate(Path(__file__).parent / "demo-vocabs" / "manifest.ttl")


def test_validator_invalid_01():
    try:
        validate(Path(__file__).parent / "demo-vocabs" / "manifest-invalid-01.ttl")
    except ValueError as e:
        assert "Manifest Shapes invalid:" in str(e)


def test_validator_invalid_03():
    try:
        validate(Path(__file__).parent / "demo-vocabs" / "manifest-invalid-02.ttl")
    except ValueError as e:
        assert str(e) == "The content link vocabz/*.ttl is not a directory"


def test_validator_invalid_02():
    try:
        validate(Path(__file__).parent / "demo-vocabs" / "manifest-invalid-03.ttl")
    except ValueError as e:
        assert (
            str(e)
            == "Remote content link non-resolving: https://github.com/RDFLib/prez/blob/main/prez/reference_data/profiles/ogc_records_profile.ttlx"
        )


def test_validator_valid_multi():
    assert validate(Path(__file__).parent / "demo-vocabs" / "manifest-multi.ttl")


def test_validator_valid_main_entity():
    assert validate(Path(__file__).parent / "demo-vocabs" / "manifest-mainEntity.ttl")


def test_validator_invalid_main_entity():
    try:
        validate(
            Path(__file__).parent / "demo-vocabs" / "manifest-mainEntity-invalid.ttl"
        )
    except ValueError as e:
        assert "N04" in str(e)


def test_validator_invalid_main_entity2():
    try:
        validate(
            Path(__file__).parent / "demo-vocabs" / "manifest-mainEntity-invalid2.ttl"
        )
    except ValueError as e:
        assert "N04" in str(e)


def test_validator_valid_conformance():
    assert validate(Path(__file__).parent / "demo-vocabs" / "manifest-conformance.ttl")


def test_validator_valid_conformance_local():
    assert validate(
        Path(__file__).parent / "demo-vocabs" / "manifest-conformance-local.ttl"
    )


def test_validator_invalid_conformance_local():
    try:
        validate(
            Path(__file__).parent
            / "demo-vocabs"
            / "manifest-conformance-local-invalid.ttl"
        )
    except ValueError as e:
        assert "Message: Requirement 2.1.4, 2.2.1 or 2.3.1" in str(e)


def test_validator_valid_conformance_all():
    try:
        validate(Path(__file__).parent / "demo-vocabs" / "manifest-conformance-all.ttl")
    except ValueError as e:
        assert "Results (6)" in str(e)

    # language-test.ttl is known to have 6 errors according to VocPub 4.10, image-test.ttl none


def test_validator_invalid_conformance_all():
    try:
        validate(
            Path(__file__).parent
            / "demo-vocabs"
            / "manifest-conformance-all-local-invalid.ttl"
        )
    except ValueError as e:
        assert "Results (1)" in str(e)


def test_validator_cli():
    try:
        result = runner.invoke(
            app,
            [
                "validate",
                str(Path(__file__).parent / "demo-vocabs" / "manifest-invalid-01.ttl"),
            ],
        )
    except ValueError as e:
        assert "MinCountConstraintComponent" in str(e)
