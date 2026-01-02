"""
Unit tests for name_generator module.
Tests: generate_tournament_name, generate_match_name, generate_short_id
"""
import pytest
import re
from orchestrator.name_generator import (
    generate_tournament_name,
    generate_match_name,
    generate_short_id,
    ADJECTIVES,
    NOUNS,
    MATCH_DESCRIPTORS
)


class TestGenerateTournamentName:
    """Tests for generate_tournament_name function."""
    
    def test_returns_string(self):
        """Should return a string."""
        for _ in range(50):
            name = generate_tournament_name()
            assert isinstance(name, str)
    
    def test_follows_pattern(self):
        """Name should follow adjective-noun-descriptor pattern."""
        for _ in range(50):
            name = generate_tournament_name()
            parts = name.split('-')
            assert len(parts) == 3
    
    def test_uses_valid_adjective(self):
        """First part should be from ADJECTIVES list."""
        for _ in range(100):
            name = generate_tournament_name()
            adjective = name.split('-')[0]
            assert adjective in ADJECTIVES
    
    def test_uses_valid_noun(self):
        """Second part should be from NOUNS list."""
        for _ in range(100):
            name = generate_tournament_name()
            noun = name.split('-')[1]
            assert noun in NOUNS
    
    def test_uses_valid_descriptor(self):
        """Third part should be from MATCH_DESCRIPTORS list."""
        for _ in range(100):
            name = generate_tournament_name()
            descriptor = name.split('-')[2]
            assert descriptor in MATCH_DESCRIPTORS
    
    def test_all_lowercase(self):
        """Name should be all lowercase."""
        for _ in range(50):
            name = generate_tournament_name()
            assert name == name.lower()
    
    def test_hyphen_separated(self):
        """Parts should be separated by hyphens."""
        name = generate_tournament_name()
        assert '-' in name
        assert name.count('-') == 2
    
    def test_randomness(self):
        """Generated names should be random (not all identical)."""
        names = [generate_tournament_name() for _ in range(100)]
        unique_names = set(names)
        # With random selection, we should get many unique names
        assert len(unique_names) >= 50
    
    def test_no_spaces(self):
        """Name should not contain spaces."""
        for _ in range(50):
            name = generate_tournament_name()
            assert ' ' not in name
    
    def test_url_safe(self):
        """Name should be URL-safe."""
        for _ in range(50):
            name = generate_tournament_name()
            # Should only contain lowercase letters and hyphens
            assert re.match(r'^[a-z\-]+$', name)


class TestGenerateMatchName:
    """Tests for generate_match_name function."""
    
    def test_returns_string(self):
        """Should return a string."""
        name = generate_match_name(1, 1)
        assert isinstance(name, str)
    
    def test_includes_round_prefix(self):
        """Name should start with r{round_num}-."""
        name = generate_match_name(2, 1)
        assert name.startswith('r2-')
    
    def test_round_number_encoded(self):
        """Different rounds should produce different prefixes."""
        for round_num in range(1, 11):
            name = generate_match_name(round_num, 1)
            assert name.startswith(f'r{round_num}-')
    
    def test_follows_pattern(self):
        """Name should follow r{round}-adjective-noun-descriptor pattern."""
        name = generate_match_name(1, 1)
        parts = name.split('-')
        assert len(parts) == 4
        assert parts[0] == 'r1'
    
    def test_uses_valid_adjective(self):
        """Second part should be from ADJECTIVES list."""
        for _ in range(50):
            name = generate_match_name(1, 1)
            adjective = name.split('-')[1]
            assert adjective in ADJECTIVES
    
    def test_uses_valid_noun(self):
        """Third part should be from NOUNS list."""
        for _ in range(50):
            name = generate_match_name(1, 1)
            noun = name.split('-')[2]
            assert noun in NOUNS
    
    def test_uses_valid_descriptor(self):
        """Fourth part should be from MATCH_DESCRIPTORS list."""
        for _ in range(50):
            name = generate_match_name(1, 1)
            descriptor = name.split('-')[3]
            assert descriptor in MATCH_DESCRIPTORS
    
    def test_all_lowercase(self):
        """Name should be all lowercase."""
        name = generate_match_name(1, 1)
        assert name == name.lower()
    
    def test_randomness(self):
        """Generated names should be random."""
        names = [generate_match_name(1, i) for i in range(100)]
        unique_names = set(names)
        assert len(unique_names) >= 50
    
    def test_high_round_numbers(self):
        """Should handle high round numbers."""
        name = generate_match_name(99, 1)
        assert name.startswith('r99-')
    
    def test_match_num_not_in_name(self):
        """Match number is not included in the generated name (just round)."""
        # Note: Current implementation doesn't use match_num in the name
        name1 = generate_match_name(1, 1)
        name2 = generate_match_name(1, 2)
        # Both should have same round prefix
        assert name1.startswith('r1-')
        assert name2.startswith('r1-')


class TestGenerateShortId:
    """Tests for generate_short_id function."""
    
    def test_returns_string(self):
        """Should return a string."""
        short_id = generate_short_id()
        assert isinstance(short_id, str)
    
    def test_default_length(self):
        """Without prefix, ID should be 8 characters."""
        short_id = generate_short_id()
        assert len(short_id) == 8
    
    def test_hexadecimal(self):
        """ID should be hexadecimal (0-9, a-f)."""
        short_id = generate_short_id()
        assert re.match(r'^[0-9a-f]+$', short_id)
    
    def test_with_prefix(self):
        """With prefix, ID should start with prefix."""
        short_id = generate_short_id(prefix="team-")
        assert short_id.startswith("team-")
    
    def test_prefix_length(self):
        """Total length should be prefix + 8."""
        prefix = "test-"
        short_id = generate_short_id(prefix=prefix)
        assert len(short_id) == len(prefix) + 8
    
    def test_empty_prefix(self):
        """Empty prefix should work same as no prefix."""
        short_id = generate_short_id(prefix="")
        assert len(short_id) == 8
    
    def test_uniqueness(self):
        """Generated IDs should be unique."""
        ids = [generate_short_id() for _ in range(1000)]
        unique_ids = set(ids)
        assert len(unique_ids) == 1000
    
    def test_various_prefixes(self):
        """Various prefixes should work correctly."""
        prefixes = ["t-", "match-", "user_", "abc123-"]
        for prefix in prefixes:
            short_id = generate_short_id(prefix=prefix)
            assert short_id.startswith(prefix)
            # Part after prefix should be 8 hex chars
            suffix = short_id[len(prefix):]
            assert len(suffix) == 8
            assert re.match(r'^[0-9a-f]+$', suffix)


class TestWordLists:
    """Tests for the word list constants."""
    
    def test_adjectives_not_empty(self):
        """ADJECTIVES list should not be empty."""
        assert len(ADJECTIVES) > 0
    
    def test_nouns_not_empty(self):
        """NOUNS list should not be empty."""
        assert len(NOUNS) > 0
    
    def test_descriptors_not_empty(self):
        """MATCH_DESCRIPTORS list should not be empty."""
        assert len(MATCH_DESCRIPTORS) > 0
    
    def test_adjectives_lowercase(self):
        """All adjectives should be lowercase."""
        for adj in ADJECTIVES:
            assert adj == adj.lower()
    
    def test_nouns_lowercase(self):
        """All nouns should be lowercase."""
        for noun in NOUNS:
            assert noun == noun.lower()
    
    def test_descriptors_lowercase(self):
        """All descriptors should be lowercase."""
        for desc in MATCH_DESCRIPTORS:
            assert desc == desc.lower()
    
    def test_no_spaces_in_adjectives(self):
        """Adjectives should not contain spaces."""
        for adj in ADJECTIVES:
            assert ' ' not in adj
    
    def test_no_spaces_in_nouns(self):
        """Nouns should not contain spaces."""
        for noun in NOUNS:
            assert ' ' not in noun
    
    def test_no_spaces_in_descriptors(self):
        """Descriptors should not contain spaces."""
        for desc in MATCH_DESCRIPTORS:
            assert ' ' not in desc
    
    def test_sufficient_variety(self):
        """Lists should have enough variety for randomness."""
        # Should have enough combinations for unique tournament names
        combinations = len(ADJECTIVES) * len(NOUNS) * len(MATCH_DESCRIPTORS)
        assert combinations >= 10000
