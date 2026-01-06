import math
from typing import Tuple

class EloCalculator:
    """
    ELO rating system for calculating win probabilities and rating changes.
    Standard K-factor of 32 for moderate rating volatility.
    """
    
    def __init__(self, k_factor: int = 32):
        self.k_factor = k_factor
    
    def calculate_win_probability(self, rating_a: int, rating_b: int) -> Tuple[float, float]:
        """
        Calculate win probabilities for two teams based on their ELO ratings.
        
        Returns:
            (prob_a_wins, prob_b_wins) as floats between 0 and 1
        """
        expected_a = 1 / (1 + math.pow(10, (rating_b - rating_a) / 400))
        expected_b = 1 - expected_a
        return (expected_a, expected_b)
    
    def calculate_rating_change(
        self, 
        winner_rating: int, 
        loser_rating: int
    ) -> Tuple[int, int]:
        """
        Calculate new ratings after a match.
        
        Args:
            winner_rating: Current ELO rating of the winner
            loser_rating: Current ELO rating of the loser
            
        Returns:
            (new_winner_rating, new_loser_rating)
        """
        # Calculate expected scores
        expected_winner = 1 / (1 + math.pow(10, (loser_rating - winner_rating) / 400))
        expected_loser = 1 - expected_winner
        
        # Actual scores (1 for win, 0 for loss)
        actual_winner = 1.0
        actual_loser = 0.0
        
        # Calculate rating changes
        winner_change = round(self.k_factor * (actual_winner - expected_winner))
        loser_change = round(self.k_factor * (actual_loser - expected_loser))
        
        # Apply changes
        new_winner_rating = winner_rating + winner_change
        new_loser_rating = loser_rating + loser_change
        
        return (new_winner_rating, new_loser_rating)
    
    def get_rating_change_amount(
        self,
        winner_rating: int,
        loser_rating: int
    ) -> Tuple[int, int]:
        """
        Get the amount of rating change without applying it.
        
        Returns:
            (winner_change, loser_change) - can be positive or negative
        """
        expected_winner = 1 / (1 + math.pow(10, (loser_rating - winner_rating) / 400))
        expected_loser = 1 - expected_winner
        
        winner_change = round(self.k_factor * (1.0 - expected_winner))
        loser_change = round(self.k_factor * (0.0 - expected_loser))
        
        return (winner_change, loser_change)
    
    def calculate_draw_rating_change(
        self,
        rating_a: int,
        rating_b: int
    ) -> Tuple[int, int]:
        """
        Calculate new ratings after a draw.
        In a draw, both players score 0.5.
        
        Returns:
            (new_rating_a, new_rating_b)
        """
        expected_a = 1 / (1 + math.pow(10, (rating_b - rating_a) / 400))
        expected_b = 1 - expected_a
        
        # Draw = 0.5 score for both
        actual_score = 0.5
        
        change_a = round(self.k_factor * (actual_score - expected_a))
        change_b = round(self.k_factor * (actual_score - expected_b))
        
        return (rating_a + change_a, rating_b + change_b)
    
    def get_draw_change_amount(
        self,
        rating_a: int,
        rating_b: int
    ) -> Tuple[int, int]:
        """
        Get the amount of rating change for a draw without applying it.
        
        Returns:
            (change_a, change_b)
        """
        expected_a = 1 / (1 + math.pow(10, (rating_b - rating_a) / 400))
        expected_b = 1 - expected_a
        
        change_a = round(self.k_factor * (0.5 - expected_a))
        change_b = round(self.k_factor * (0.5 - expected_b))
        
        return (change_a, change_b)
