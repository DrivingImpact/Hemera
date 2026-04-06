"""QC Sampling engine — ISO 19011 stratified random sampling."""
import math
import random
import json

Z = 1.96
P = 0.5
E = 0.05
HARD_GATE_THRESHOLD = 0.05


def calculate_sample_size(population: int) -> int:
    if population <= 0:
        return 0
    numerator = population * (Z ** 2) * P * (1 - P)
    denominator = (E ** 2) * (population - 1) + (Z ** 2) * P * (1 - P)
    n = round(numerator / denominator)
    return min(n, population)
