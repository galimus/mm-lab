

import numpy as np

class ExecutionModel:
    def __init__(self, alpha=5.0, beta=15.0, slippage_chance=0.1):
        self.alpha = alpha
        self.beta = beta
        self.slippage_chance = slippage_chance
    
    def compute_fill_probability(self, queue_position_ratio, price_distance):
        prob_queue = np.exp(-self.alpha * queue_position_ratio)
        prob_distance = np.exp(-self.beta * price_distance)
        return prob_queue * prob_distance

    def simulate_fill(self, queue_position_ratio, price_distance, price_movement):
        base_fill_prob = self.compute_fill_probability(queue_position_ratio, price_distance)

        if abs(price_movement) > 0.001:
            if np.random.rand() < self.slippage_chance:
                return "slippage"
        
        if np.random.rand() < base_fill_prob:
            return "filled"
        else:
            return "not_filled"
