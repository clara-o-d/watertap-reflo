"""
Reaction packages for lithium processing operations.

This module defines reaction packages for:
1. Li2CO3 precipitation reactions
2. LiOH conversion reactions

These packages are used with CSTR unit models with rate reactions.
"""

from idaes.models.properties.modular_properties.base.generic_reaction import GenericReactionParameterBlock
from idaes.models.properties.modular_properties.reactions.rate_forms import power_law_rate
from idaes.models.properties.modular_properties.base.generic_reaction import ConcentrationForm
from idaes.core.base.components import Solute
from pyomo.environ import units as pyunits


def get_li2co3_precipitation_config():
    """
    Configuration for Li2CO3 precipitation reactions.
    
    Main reaction: 2Li+ + CO3-2 → Li2CO3(s)
    
    Returns:
        dict: Reaction configuration dictionary
    """
    
    reaction_config = {
        "base_units": {
            "time": pyunits.s,
            "length": pyunits.m,
            "mass": pyunits.kg,
            "amount": pyunits.mol,
            "temperature": pyunits.K,
        },
        "concentration_form": ConcentrationForm.moleFraction,
        "rate_reactions": {
            "R1": {
                "stoichiometry": {
                    ("Liq", "li+"): -2,
                    ("Liq", "CO3-2"): -1,
                    ("Liq", "Li2CO3"): 1,
                },
                "rate_constant": 1e-3,  # Rate constant (1/s)
                "rate_form": power_law_rate,
            }
        }
    }
    
    return reaction_config


def get_lioh_conversion_config():
    """
    Configuration for LiOH conversion reactions.
    
    Main reaction: Li2CO3 + Ca(OH)2 → 2LiOH + CaCO3(s)
    Simplified as: Li2CO3 + Ca_2+ + 2OH- → 2li+ + 2OH- + CaCO3
    
    Additional components needed: Ca_2+, OH-
    
    Returns:
        dict: Reaction configuration dictionary
    """
    
    reaction_config = {
        "base_units": {
            "time": pyunits.s,
            "length": pyunits.m,
            "mass": pyunits.kg,
            "amount": pyunits.mol,
            "temperature": pyunits.K,
        },
        "concentration_form": ConcentrationForm.moleFraction,
        "rate_reactions": {
            "R1": {
                "stoichiometry": {
                    ("Liq", "Li2CO3"): -1,
                    ("Liq", "Ca_2+"): -1,
                    ("Liq", "li+"): 2,      # Li from Li2CO3 converted to LiOH
                    ("Liq", "CaCO3"): 1,    # CaCO3 precipitate
                },
                "rate_constant": 1e-2,  # Rate constant (1/s)
                "rate_form": power_law_rate,
            }
        }
    }
    
    return reaction_config


def get_enhanced_property_config():
    """
    Enhanced property configuration that includes additional components
    needed for the reaction packages.
    
    Returns:
        dict: Enhanced property configuration with additional components
    """
    
    enhanced_config = {
        "solute_list": [
            "li+", "boron", "borate", "Ca_2+", "Mg_2+", "Na+", "Cl-", 
            "CO3-2", "HCO3-", "tss", "tds", "Alkalinity_2-", "Li2CO3",
            "OH-", "H+", "CaCO3"  # Additional components for reactions
        ],
        "mw_data": {
            "li+": 6.94e-3,
            "boron": 10.81e-3,
            "borate": 61.83e-3,  # MW for B(OH)4-
            "Ca_2+": 40.08e-3,
            "Mg_2+": 24.31e-3,
            "Na+": 22.99e-3,
            "Cl-": 35.45e-3,
            "CO3-2": 60.01e-3,
            "HCO3-": 61.02e-3,
            "tss": 1.0,
            "tds": 31.4e-3,
            "Alkalinity_2-": 61.02e-3,  # Placeholder MW
            "Li2CO3": 73.89e-3,
            "OH-": 17.01e-3,
            "H+": 1.01e-3,
            "CaCO3": 100.09e-3,
        }
    }
    
    return enhanced_config 