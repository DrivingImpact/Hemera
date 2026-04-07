"""Pedigree matrix uncertainty quantification.

Implements the ecoinvent pedigree matrix (Ciroth et al., 2016) using
Geometric Standard Deviation (GSD) under a lognormal distribution.

Reference:
    Ciroth, A., Muller, S., Weidema, B., Lesage, P. (2016).
    "Empirically based uncertainty factors for the pedigree matrix in ecoinvent."
    The International Journal of Life Cycle Assessment, 21, 1338-1348.
"""

import math
from dataclasses import dataclass


# GSD factors per indicator per score (1-5)
# These are empirically derived from the ecoinvent database.
RELIABILITY_GSD = {1: 1.00, 2: 1.54, 3: 1.61, 4: 1.69, 5: 1.69}
COMPLETENESS_GSD = {1: 1.00, 2: 1.03, 3: 1.04, 4: 1.08, 5: 1.08}
TEMPORAL_GSD = {1: 1.00, 2: 1.03, 3: 1.10, 4: 1.19, 5: 1.29}
GEOGRAPHICAL_GSD = {1: 1.00, 2: 1.04, 3: 1.08, 4: 1.11, 5: 1.11}
TECHNOLOGICAL_GSD = {1: 1.00, 2: 1.05, 3: 1.12, 4: 1.21, 5: 1.35}

# Basic uncertainty for emission factors (inherent variability)
# This is a conservative default; specific factors may have their own.
BASIC_GSD = 1.05


@dataclass
class PedigreeScore:
    reliability: int  # 1-5
    completeness: int  # 1-5
    temporal: int  # 1-5
    geographical: int  # 1-5
    technological: int  # 1-5
    gsd_total: float = 0.0  # calculated
    ci_lower_factor: float = 0.0  # multiply central estimate by this for lower bound
    ci_upper_factor: float = 0.0  # multiply central estimate by this for upper bound

    def calculate(self) -> "PedigreeScore":
        """Calculate total GSD and 95% confidence interval factors."""
        # ln(GSD_total)^2 = sum of ln(GSD_i)^2 for all indicators
        ln_sq_sum = (
            math.log(BASIC_GSD) ** 2
            + math.log(RELIABILITY_GSD[self.reliability]) ** 2
            + math.log(COMPLETENESS_GSD[self.completeness]) ** 2
            + math.log(TEMPORAL_GSD[self.temporal]) ** 2
            + math.log(GEOGRAPHICAL_GSD[self.geographical]) ** 2
            + math.log(TECHNOLOGICAL_GSD[self.technological]) ** 2
        )
        self.gsd_total = math.exp(math.sqrt(ln_sq_sum))

        # 95% CI: [central / GSD^2, central * GSD^2]
        self.ci_lower_factor = 1.0 / (self.gsd_total ** 2)
        self.ci_upper_factor = self.gsd_total ** 2

        return self


def score_emission_factor(
    ef_source: str,
    ef_level: int,
    ef_year: int,
    ef_region: str,
    current_year: int = 2024,
) -> PedigreeScore:
    """Auto-assign pedigree scores based on emission factor metadata.

    Args:
        ef_source: source database (defra, exiobase, supplier, climatiq, useeio)
        ef_level: cascade level (1=supplier-specific, 6=fallback)
        ef_year: year of the emission factor
        ef_region: region of the emission factor (UK, EU, global, etc.)
        current_year: current reporting year
    """
    age = current_year - ef_year

    # Reliability
    if ef_level == 1:  # supplier-specific verified
        reliability = 1
    elif ef_level == 2:  # activity-based DEFRA
        reliability = 2
    elif ef_level in (3, 4):  # MRIO/EEIO spend-based
        reliability = 3
    else:
        reliability = 4

    # Completeness
    if ef_source in ("defra", "supplier"):
        completeness = 2
    elif ef_source in ("exiobase", "useeio"):
        completeness = 3
    else:
        completeness = 4

    # Temporal
    if age <= 2:
        temporal = 1
    elif age <= 5:
        temporal = 2
    elif age <= 9:
        temporal = 3
    elif age <= 14:
        temporal = 4
    else:
        temporal = 5

    # Geographical
    region_lower = ef_region.lower() if ef_region else "unknown"
    if region_lower == "uk":
        geographical = 1
    elif region_lower in ("eu", "europe", "gb"):
        geographical = 2
    elif region_lower in ("oecd", "developed"):
        geographical = 3
    elif region_lower == "global":
        geographical = 4
    else:
        geographical = 5

    # Technological — this is the big one for Scope 3
    if ef_level == 1:  # supplier-specific = exact match
        technological = 1
    elif ef_level == 2:  # activity-based = good match
        technological = 2
    elif ef_level == 3:  # sector+geography MRIO = same function
        technological = 3
    elif ef_level == 4:  # broad spend-based = related
        technological = 4
    else:  # fallback = unknown
        technological = 5

    return PedigreeScore(
        reliability=reliability,
        completeness=completeness,
        temporal=temporal,
        geographical=geographical,
        technological=technological,
    ).calculate()


def aggregate_uncertainty(gsd_values: list[float], co2e_values: list[float]) -> float:
    """Aggregate line-item uncertainties into overall footprint uncertainty.

    Uses error propagation for independent lognormal variables:
    ln(GSD_total)^2 = sum_i [ (w_i * ln(GSD_i))^2 ]
    where w_i = co2e_i / sum(co2e)

    Returns the overall GSD for the total footprint.
    """
    total = sum(co2e_values)
    if total == 0 or not gsd_values:
        return 1.0

    ln_sq_sum = 0.0
    for gsd, co2e in zip(gsd_values, co2e_values):
        if gsd > 0 and co2e > 0:
            weight = co2e / total
            ln_sq_sum += (weight * math.log(gsd)) ** 2

    return math.exp(math.sqrt(ln_sq_sum))
