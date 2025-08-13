"""Utility functions for lithium extraction flowsheet."""

from pyomo.environ import value
import numpy as np

def compute_evaporation_fraction_for_target_li_conc(m, target_li_conc):
    """Compute evaporation fraction needed to achieve target lithium concentration.
    
    Args:
        m: Pyomo model
        target_li_conc: Target lithium concentration in g/kg
        
    Returns:
        float: Optimal evaporation fraction
    """
    prop_in = m.fs.feed.properties[0]
    li_inlet_flow = value(prop_in.flow_mass_phase_comp["Liq", "Li+"])
    water_inlet_flow = value(prop_in.flow_mass_phase_comp["Liq", "H2O"])
    tds_inlet_flow = value(prop_in.flow_mass_phase_comp["Liq", "TDS"])
    # # Quadratic approximation: mass_fraction = 88.1606 * x² + -169.2358 * x + 81.4783
    # a = 88.1606
    # b_ = -169.2358
    # c = 81.4783

    def li_conc_at_evap(evap_frac):
        li_mass_frac = -25 * evap_frac + 25
        li_outflow = li_inlet_flow * li_mass_frac
        water_outflow = water_inlet_flow * (1 - evap_frac)
        
        # Calculate TDS outflow using the same methodology as the flowsheet
        # Quadratic fit from flowsheet:
        # precipitate_concentration = a*(1-evap_frac)^2 + b*(1-evap_frac) + c
        precipitate_a = 1.517e03  # kg/m³
        precipitate_b = -9.406e02 # kg/m³
        precipitate_c = 4.294e02  # kg/m³
        precipitate_concentration = (
            precipitate_a * (1 - evap_frac)**2
            + precipitate_b * (1 - evap_frac)
            + precipitate_c
        )
        
        # Calculate precipitate mass flow (same as flowsheet)
        original_water_volume = water_inlet_flow / 1000  # m³/s (assuming density = 1000 kg/m³)
        tds_precipitated = precipitate_concentration * original_water_volume  # kg/s

        # TDS outflow = TDS inlet - TDS precipitated
        tds_outflow = tds_inlet_flow - tds_precipitated
        if tds_outflow < 0:
            print(f"TDS outflow is negative: {tds_outflow:.2f} kg/s at evap_frac: {evap_frac:.4f}")
            return 0, 0, 0
        # Calculate total mass outflow
        total_mass_outflow = water_outflow + tds_outflow
        
        if total_mass_outflow < 1e-12:
            print(f"Total mass outflow is too low: {total_mass_outflow:.2f} kg/s at evap_frac: {evap_frac:.4f}")
            return 0, 0, 0

        # Lithium concentration in g/kg
        return li_outflow / total_mass_outflow * 1000, li_outflow, total_mass_outflow

    evap_fractions = np.linspace(0.87, 0.99, 200)
    concentrations = []
    li_outflows = []
    total_mass_outflows = []
    
    for evap_frac in evap_fractions:
        conc, li_outflow, total_mass_outflow = li_conc_at_evap(evap_frac)
        concentrations.append(conc)
        li_outflows.append(li_outflow)
        total_mass_outflows.append(total_mass_outflow)
    
    # Find the evaporation fraction that gives the closest concentration to target
    objective_values = [abs(conc - target_li_conc) for conc in concentrations]
    best_idx = np.argmin(objective_values)
    best_evap_frac = evap_fractions[best_idx]
    best_conc = concentrations[best_idx]
    best_li_outflow = li_outflows[best_idx]
    best_total_mass_outflow = total_mass_outflows[best_idx]

    # Check if the solution is reasonable
    tolerance = 0.1
    if abs(best_conc - target_li_conc) > tolerance:
        print(f"Warning: Best achievable concentration is {best_conc:.3f} g/kg, target was {target_li_conc:.3f} g/kg")
    print(f"Using evaporation fraction: {best_evap_frac:.4f}")
    print(f"Total mass outflow: {best_total_mass_outflow:.2f} kg/s")
    print(f"Li+ outflow: {best_li_outflow:.2f} kg/s")
    
    return best_evap_frac