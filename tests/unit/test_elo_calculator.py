"""
Unit tests for EloCalculator class.
Tests all functions: calculate_win_probability, calculate_rating_change, get_rating_change_amount
"""
import pytest
import math
from orchestrator.elo_calculator import EloCalculator


class TestEloCalculatorInit:
    """Tests for EloCalculator initialization."""
    
    def test_default_k_factor(self):
        """Default K-factor should be 32."""
        calc = EloCalculator()
        assert calc.k_factor == 32
    
    def test_custom_k_factor(self):
        """Custom K-factor should be set correctly."""
        calc = EloCalculator(k_factor=16)
        assert calc.k_factor == 16
    
    def test_k_factor_zero(self):
        """K-factor of zero should be allowed (no rating changes)."""
        calc = EloCalculator(k_factor=0)
        assert calc.k_factor == 0


class TestCalculateWinProbability:
    """Tests for calculate_win_probability method."""
    
    @pytest.fixture
    def calc(self):
        return EloCalculator()
    
    def test_equal_ratings_50_50(self, calc):
        """Equal ratings should give 50-50 probability."""
        prob_a, prob_b = calc.calculate_win_probability(1500, 1500)
        assert prob_a == pytest.approx(0.5, rel=1e-6)
        assert prob_b == pytest.approx(0.5, rel=1e-6)
    
    def test_probabilities_sum_to_one(self, calc):
        """Probabilities should always sum to 1."""
        test_cases = [
            (1500, 1500),
            (1600, 1400),
            (1200, 1800),
            (2400, 800),
            (1000, 2000),
        ]
        for rating_a, rating_b in test_cases:
            prob_a, prob_b = calc.calculate_win_probability(rating_a, rating_b)
            assert prob_a + prob_b == pytest.approx(1.0, rel=1e-9)
    
    def test_higher_rated_has_higher_probability(self, calc):
        """Higher rated team should have higher win probability."""
        prob_a, prob_b = calc.calculate_win_probability(1600, 1400)
        assert prob_a > prob_b
        assert prob_a > 0.5
        assert prob_b < 0.5
    
    def test_200_point_difference(self, calc):
        """200 point difference should give ~76% probability to higher rated."""
        prob_a, prob_b = calc.calculate_win_probability(1600, 1400)
        # ELO formula: 200 point diff = ~76% for higher rated
        assert prob_a == pytest.approx(0.76, rel=0.01)
        assert prob_b == pytest.approx(0.24, rel=0.01)
    
    def test_400_point_difference(self, calc):
        """400 point difference should give ~91% probability to higher rated."""
        prob_a, prob_b = calc.calculate_win_probability(1700, 1300)
        assert prob_a == pytest.approx(0.91, rel=0.01)
    
    def test_symmetric_calculation(self, calc):
        """Swapping ratings should swap probabilities."""
        prob_a1, prob_b1 = calc.calculate_win_probability(1600, 1400)
        prob_a2, prob_b2 = calc.calculate_win_probability(1400, 1600)
        assert prob_a1 == pytest.approx(prob_b2, rel=1e-9)
        assert prob_b1 == pytest.approx(prob_a2, rel=1e-9)
    
    def test_very_large_difference(self, calc):
        """Very large rating difference should approach 1.0 and 0.0."""
        prob_a, prob_b = calc.calculate_win_probability(2400, 800)
        assert prob_a > 0.99
        assert prob_b < 0.01
    
    def test_probabilities_are_floats(self, calc):
        """Probabilities should be float type."""
        prob_a, prob_b = calc.calculate_win_probability(1500, 1500)
        assert isinstance(prob_a, float)
        assert isinstance(prob_b, float)
    
    def test_probabilities_in_valid_range(self, calc):
        """Probabilities should be between 0 and 1."""
        test_ratings = [(r1, r2) for r1 in range(800, 2401, 200) for r2 in range(800, 2401, 200)]
        for rating_a, rating_b in test_ratings:
            prob_a, prob_b = calc.calculate_win_probability(rating_a, rating_b)
            assert 0 <= prob_a <= 1
            assert 0 <= prob_b <= 1


class TestCalculateRatingChange:
    """Tests for calculate_rating_change method."""
    
    @pytest.fixture
    def calc(self):
        return EloCalculator()
    
    def test_equal_ratings_rating_change(self, calc):
        """Equal ratings: winner gains k/2, loser loses k/2."""
        new_winner, new_loser = calc.calculate_rating_change(1500, 1500)
        # Winner gains 16, loser loses 16 (with K=32)
        assert new_winner == 1516
        assert new_loser == 1484
    
    def test_expected_outcome_small_change(self, calc):
        """When higher rated wins (expected), change is smaller."""
        new_winner, new_loser = calc.calculate_rating_change(1600, 1400)
        winner_change = new_winner - 1600
        loser_change = new_loser - 1400
        # Expected outcome = smaller rating change
        assert winner_change < 16  # Less than half of K
        assert abs(loser_change) < 16
    
    def test_upset_larger_change(self, calc):
        """When lower rated wins (upset), change is larger."""
        new_winner, new_loser = calc.calculate_rating_change(1400, 1600)
        winner_change = new_winner - 1400
        loser_change = new_loser - 1600
        # Upset = larger rating change
        assert winner_change > 16  # More than half of K
        assert abs(loser_change) > 16
    
    def test_rating_points_conserved(self, calc):
        """Total rating points should be approximately conserved."""
        test_cases = [
            (1500, 1500),
            (1600, 1400),
            (1400, 1600),
            (1800, 1200),
        ]
        for winner_rating, loser_rating in test_cases:
            new_winner, new_loser = calc.calculate_rating_change(winner_rating, loser_rating)
            original_total = winner_rating + loser_rating
            new_total = new_winner + new_loser
            # Should be equal within rounding tolerance
            assert abs(original_total - new_total) <= 1
    
    def test_winner_gains_loser_loses(self, calc):
        """Winner should gain rating, loser should lose rating."""
        test_cases = [
            (1500, 1500),
            (1600, 1400),
            (1400, 1600),
        ]
        for winner_rating, loser_rating in test_cases:
            new_winner, new_loser = calc.calculate_rating_change(winner_rating, loser_rating)
            assert new_winner > winner_rating
            assert new_loser < loser_rating
    
    def test_returns_integers(self, calc):
        """New ratings should be integers."""
        new_winner, new_loser = calc.calculate_rating_change(1500, 1500)
        assert isinstance(new_winner, int)
        assert isinstance(new_loser, int)
    
    def test_custom_k_factor_affects_magnitude(self):
        """Different K-factors should produce different change magnitudes."""
        calc_32 = EloCalculator(k_factor=32)
        calc_16 = EloCalculator(k_factor=16)
        
        new_w_32, new_l_32 = calc_32.calculate_rating_change(1500, 1500)
        new_w_16, new_l_16 = calc_16.calculate_rating_change(1500, 1500)
        
        change_32 = new_w_32 - 1500
        change_16 = new_w_16 - 1500
        
        # K=32 should produce twice the change of K=16
        assert change_32 == 2 * change_16
    
    def test_zero_k_factor_no_change(self):
        """K-factor of 0 should result in no rating change."""
        calc = EloCalculator(k_factor=0)
        new_winner, new_loser = calc.calculate_rating_change(1500, 1500)
        assert new_winner == 1500
        assert new_loser == 1500


class TestGetRatingChangeAmount:
    """Tests for get_rating_change_amount method."""
    
    @pytest.fixture
    def calc(self):
        return EloCalculator()
    
    def test_returns_change_amounts(self, calc):
        """Should return the change amounts, not new ratings."""
        winner_change, loser_change = calc.get_rating_change_amount(1500, 1500)
        assert winner_change == 16  # Positive for winner
        assert loser_change == -16  # Negative for loser
    
    def test_winner_change_positive(self, calc):
        """Winner change should always be positive."""
        test_cases = [
            (1500, 1500),
            (1600, 1400),
            (1400, 1600),
        ]
        for winner_rating, loser_rating in test_cases:
            winner_change, _ = calc.get_rating_change_amount(winner_rating, loser_rating)
            assert winner_change > 0
    
    def test_loser_change_negative(self, calc):
        """Loser change should always be negative."""
        test_cases = [
            (1500, 1500),
            (1600, 1400),
            (1400, 1600),
        ]
        for winner_rating, loser_rating in test_cases:
            _, loser_change = calc.get_rating_change_amount(winner_rating, loser_rating)
            assert loser_change < 0
    
    def test_changes_are_symmetric(self, calc):
        """Winner gain should equal loser loss (in magnitude)."""
        test_cases = [
            (1500, 1500),
            (1600, 1400),
            (1400, 1600),
        ]
        for winner_rating, loser_rating in test_cases:
            winner_change, loser_change = calc.get_rating_change_amount(winner_rating, loser_rating)
            assert winner_change == pytest.approx(-loser_change, abs=1)
    
    def test_consistent_with_calculate_rating_change(self, calc):
        """Should be consistent with calculate_rating_change."""
        winner_rating, loser_rating = 1550, 1450
        
        winner_change, loser_change = calc.get_rating_change_amount(winner_rating, loser_rating)
        new_winner, new_loser = calc.calculate_rating_change(winner_rating, loser_rating)
        
        assert new_winner == winner_rating + winner_change
        assert new_loser == loser_rating + loser_change
    
    def test_returns_integers(self, calc):
        """Change amounts should be integers."""
        winner_change, loser_change = calc.get_rating_change_amount(1500, 1500)
        assert isinstance(winner_change, int)
        assert isinstance(loser_change, int)


class TestEloCalculatorEdgeCases:
    """Edge case tests for EloCalculator."""
    
    def test_negative_ratings(self):
        """Calculator should handle negative ratings (though unusual)."""
        calc = EloCalculator()
        prob_a, prob_b = calc.calculate_win_probability(-100, -200)
        assert 0 < prob_a < 1
        assert 0 < prob_b < 1
        assert prob_a + prob_b == pytest.approx(1.0)
    
    def test_very_high_ratings(self):
        """Calculator should handle very high ratings."""
        calc = EloCalculator()
        prob_a, prob_b = calc.calculate_win_probability(3000, 3000)
        assert prob_a == pytest.approx(0.5)
    
    def test_identical_extreme_ratings(self):
        """Equal extreme ratings should still give 50-50."""
        calc = EloCalculator()
        prob_a, prob_b = calc.calculate_win_probability(100, 100)
        assert prob_a == pytest.approx(0.5)
        
        prob_a, prob_b = calc.calculate_win_probability(3000, 3000)
        assert prob_a == pytest.approx(0.5)
