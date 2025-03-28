"""Utility for calculating speaking duration."""
import re
import logging
import numpy as np

class SpeakingCalculator:    
    def __init__(self):
        """Initialize the speaking calculator."""
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def calculate_duration(self, text):
        if not text.strip():
            return 1.0 
        
        cleaned_text = re.sub(r'[\"\'\(\)\[\]\{\}]', '', text)

        sentence_endings = re.findall(r'[.!?;:,]', text)
        
        rng = np.random.default_rng(seed=42)
        pause_duration = len(sentence_endings) * rng.uniform(0.1, 0.4)

        words = cleaned_text.split()
        word_count = len(words)

        words_per_second = rng.uniform(2.5, 4.5)

        duration = word_count / words_per_second

        avg_word_length = np.mean([len(word) for word in words]) if words else 5
        duration += max(0, (avg_word_length - 7) * 0.015)

        duration += pause_duration

        duration = max(duration, 0.8)

        self.logger.info("Calculated speaking duration for %d words: %.2f seconds", word_count, duration)
        
        return duration