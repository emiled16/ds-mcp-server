"""Unit tests for Note model."""

import pytest

from src.models.note import Note


@pytest.mark.unit
class TestNote:
    """Tests for Note model."""

    def test_create_note(self) -> None:
        """Test Note can be created with required fields."""
        note = Note(title="Test Note")

        assert note.entity_id.startswith("note_")
        assert note.type == "note"
        assert note.title == "Test Note"
        assert note.content == ""
        assert note.tags == []
        assert note.references == []
        assert note.version == 1

    def test_create_note_with_content(self) -> None:
        """Test Note creation with all fields."""
        note = Note(
            title="Analysis Note",
            content="# Overview\n\nInitial findings...",
            tags=["analysis", "q4"],
            references=["tr_123", "tr_456"],
        )

        assert note.title == "Analysis Note"
        assert "Initial findings" in note.content
        assert note.tags == ["analysis", "q4"]
        assert note.references == ["tr_123", "tr_456"]

    def test_append(self) -> None:
        """Test appending content to a note."""
        note = Note(title="Test", content="First line")

        note.append("Second line")

        assert "First line" in note.content
        assert "Second line" in note.content

    def test_add_reference(self) -> None:
        """Test adding references."""
        note = Note(title="Test")

        note.add_reference("tr_123")
        assert "tr_123" in note.references

        # Should not add duplicates
        note.add_reference("tr_123")
        assert note.references.count("tr_123") == 1

    def test_add_tag(self) -> None:
        """Test adding tags."""
        note = Note(title="Test")

        note.add_tag("analysis")
        assert "analysis" in note.tags

        # Should not add duplicates
        note.add_tag("analysis")
        assert note.tags.count("analysis") == 1

    def test_word_count(self) -> None:
        """Test word count property."""
        note = Note(title="Test", content="")
        assert note.word_count == 0

        note.content = "One two three four five"
        assert note.word_count == 5

    def test_preview(self) -> None:
        """Test preview property."""
        # Short content
        note = Note(title="Test", content="Short content")
        assert note.preview == "Short content"

        # Long content
        long_content = "x" * 300
        note.content = long_content
        assert len(note.preview) < len(long_content)
        assert note.preview.endswith("...")

    def test_to_dict_and_from_dict(self) -> None:
        """Test serialization roundtrip."""
        original = Note(
            title="Test Note",
            content="Some content here",
            tags=["tag1", "tag2"],
            references=["ref1"],
            metadata={"source": "test"},
        )

        data = original.to_dict()
        restored = Note.from_dict(data)

        assert restored.entity_id == original.entity_id
        assert restored.title == original.title
        assert restored.content == original.content
        assert restored.tags == original.tags
        assert restored.references == original.references
        assert restored.metadata == original.metadata

