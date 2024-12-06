from typing import Union, Tuple, List
import numpy as np
import pandas as pd

def calculate_pace(distance_km: float, time_minutes: float) -> float:
    """Calculate pace in minutes per kilometer."""
    return time_minutes / distance_km

def pace_to_speed(pace_min_km: float) -> float:
    """Convert pace (min/km) to speed (km/h)."""
    return 60 / pace_min_km

def speed_to_pace(speed_kmh: float) -> float:
    """Convert speed (km/h) to pace (min/km)."""
    return 60 / speed_kmh

def calculate_training_load(distances: List[float], days_ago: List[int], 
                          decay_constant: float = 7) -> float:
    """
    Calculate training load with exponential decay.
    
    Args:
        distances: List of run distances
        days_ago: List of how many days ago each run was
        decay_constant: Days for load to decay by 1/e (default 7)
    """
    return np.sum(distances * np.exp(-np.array(days_ago) / decay_constant))

def estimate_race_time(recent_pace: float, 
                      target_distance: float,
                      recent_volume: float,
                      base_fitness: float) -> Tuple[float, float]:
    """
    Estimate race time using Riegel's formula with adjustments.
    
    Args:
        recent_pace: Recent training pace (min/km)
        target_distance: Race distance in km
        recent_volume: Recent weekly volume in km
        base_fitness: Base fitness score (0-1)
    """
    # Riegel's formula fatigue factor
    fatigue_factor = 1.06
    
    # Adjust fatigue factor based on training volume and fitness
    volume_adjustment = min(1, recent_volume / 50)  # Normalize to 50km/week
    fatigue_factor *= (1 - 0.02 * volume_adjustment * base_fitness)
    
    # Calculate estimated time
    estimated_pace = recent_pace * (target_distance ** (fatigue_factor - 1))
    estimated_time = estimated_pace * target_distance
    
    return estimated_time, estimated_pace 