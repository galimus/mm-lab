import random
import numpy as np

class ExecutionModel:
    def __init__(self, alpha=5.0, beta=15.0, slippage_chance=0.15):
        self.alpha = alpha  
        self.beta = beta    
        self.slippage_chance = slippage_chance  

    def compute_fill_probability(self, queue_position_ratio, price_distance, order_size_ratio=1.0):
       
        prob_queue = np.exp(-self.alpha * queue_position_ratio)
        prob_distance = np.exp(-self.beta * price_distance)
        prob_size = np.exp(-2.0 * order_size_ratio)  
        return prob_queue * prob_distance * prob_size

    def simulate_fill(self, queue_position_ratio, price_distance, price_movement, order_size_ratio=1.0):
        
        base_fill_prob = self.compute_fill_probability(queue_position_ratio, price_distance, order_size_ratio)

        if price_movement * (1 if queue_position_ratio < 0.5 else -1) > 0:
            base_fill_prob += 0.1

        base_fill_prob = max(0.0, min(1.0, base_fill_prob))

        r = random.random()
        if r < base_fill_prob:
            return "filled"
        elif r < base_fill_prob + self.slippage_chance:
            return "slippage"
        else:
            return "not_filled"
