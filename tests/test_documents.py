"""Reading what an FDE is actually handed.

Briefs arrive as PDFs and Word documents far more often than as plain text.
Refusing them politely is fine; failing with a decoding error is not, and
silently reading the binary as text is worse -- that produces facts from noise.
"""


import pytest

from fde.intake.documents import UnreadableDocument, read_document


def test_plain_text_is_read(tmp_path):
    path = tmp_path / "brief.txt"
    path.write_text("Data cannot leave the client environment.")
    assert "cannot leave" in read_document(path)


def test_markdown_is_read(tmp_path):
    path = tmp_path / "brief.md"
    path.write_text("# Brief\n\nData cannot leave.")
    assert "cannot leave" in read_document(path)


def test_a_binary_file_is_refused_rather_than_decoded_as_text(tmp_path):
    """Reading a PDF's bytes as text produces tokens that look like words and
    are not. Facts parsed from that are worse than no facts."""
    path = tmp_path / "brief.pdf"
    path.write_bytes(b"%PDF-1.7\n\x00\x01binary garbage\xff\xfe")
    with pytest.raises(UnreadableDocument) as exc:
        read_document(path)
    assert "pdf" in str(exc.value).lower()


def test_the_refusal_says_how_to_proceed(tmp_path):
    """An FDE with a PDF and a deadline needs the next step, not a diagnosis."""
    path = tmp_path / "brief.pdf"
    path.write_bytes(b"%PDF-1.7\n\x00")
    with pytest.raises(UnreadableDocument) as exc:
        read_document(path)
    message = str(exc.value)
    assert "--text" in message or "paste" in message.lower()


def test_a_word_document_is_refused_by_name(tmp_path):
    path = tmp_path / "brief.docx"
    path.write_bytes(b"PK\x03\x04binary")
    with pytest.raises(UnreadableDocument, match="docx"):
        read_document(path)


def test_a_missing_file_says_so_plainly(tmp_path):
    with pytest.raises(UnreadableDocument, match="does not exist"):
        read_document(tmp_path / "nothing.txt")


def test_an_empty_file_is_reported_rather_than_parsed_as_silence(tmp_path):
    """Nothing extracted from an empty file looks identical to nothing
    extracted from a full one the parser could not read."""
    path = tmp_path / "brief.txt"
    path.write_text("   \n\n")
    with pytest.raises(UnreadableDocument, match="empty"):
        read_document(path)


def test_a_text_file_with_an_odd_encoding_still_reads(tmp_path):
    path = tmp_path / "brief.txt"
    path.write_bytes("Data cannot leave — ever.".encode())
    assert "cannot leave" in read_document(path)


def test_pdf_extraction_is_used_when_a_reader_is_available(tmp_path, monkeypatch):
    """The refusal is a missing dependency, not a policy. Where a reader is
    installed it is used."""
    import fde.intake.documents as documents

    monkeypatch.setattr(
        documents, "_extract_pdf", lambda path: "Data cannot leave the client environment."
    )
    path = tmp_path / "brief.pdf"
    path.write_bytes(b"%PDF-1.7\n")
    assert "cannot leave" in read_document(path)


def test_frame_refuses_a_pdf_with_a_useful_message(tmp_path):
    from typer.testing import CliRunner

    from fde.cli import app

    runner = CliRunner()
    runner.invoke(app, ["start", "acme", "--base", str(tmp_path)])
    brief = tmp_path / "rfp.pdf"
    brief.write_bytes(b"%PDF-1.7\n\x00binary")

    result = runner.invoke(app, ["frame", str(tmp_path / "acme"), "--file", str(brief)])
    assert result.exit_code != 0
    assert "--text" in result.output


def test_frame_records_nothing_from_a_file_it_could_not_read(tmp_path):
    """The important half. A refusal that still wrote a session would have
    recorded facts nobody can trace to anything."""
    from typer.testing import CliRunner

    from fde.cli import app

    runner = CliRunner()
    runner.invoke(app, ["start", "acme", "--base", str(tmp_path)])
    brief = tmp_path / "rfp.pdf"
    brief.write_bytes(b"%PDF-1.7\n\x00binary")
    runner.invoke(app, ["frame", str(tmp_path / "acme"), "--file", str(brief)])
    assert list((tmp_path / "acme" / "facts").iterdir()) == []
