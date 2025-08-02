import numpy as np
import matplotlib.pyplot as plt
from pyomo.core import ConcreteModel, value
from idaes.core import FlowsheetBlock
from watertap_contrib.reflo.property_models import AirWaterEq, DensityCalculation
from idaes.models.unit_models import Feed
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.utils import compute_evaporation_fraction_for_target_li_conc

def create_test_model():
    """Create a minimal model for testing the evaporation calculation"""
    m = ConcreteModel()
    m.fs = FlowsheetBlock(dynamic=False)
    
    props = {
        "non_volatile_solute_list": ["TDS", "Li+"],
        "mw_data": {"TDS": 31.4038218e-3, "Li+": 6.94e-3},
        "density_calculation": DensityCalculation.calculated,
    }
    m.fs.prop_air = AirWaterEq(**props)
    m.fs.feed = Feed(property_package=m.fs.prop_air)
    
    # Set feed conditions (same as in build_flowsheet)
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "TDS"].fix(477)
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "Li+"].fix(2.0)
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "H2O"].fix(1290)
    m.fs.feed.properties[0].temperature.fix(300)
    m.fs.feed.properties[0].pressure.fix(101325)
    m.fs.feed.properties[0].flow_mass_phase_comp["Vap", "Air"].fix(1)
    m.fs.feed.properties[0].flow_mass_phase_comp["Vap", "H2O"].fix(0)
    
    # Set density parameter
    m.fs.rho = 1000  # kg/m³
    
    return m

def analyze_evaporation_function():
    """Analyze the evaporation function to understand feasible ranges"""
    m = create_test_model()
    
    # Extract parameters from the model
    prop_in = m.fs.feed.properties[0]
    li_inlet_flow = value(prop_in.flow_mass_phase_comp["Liq", "Li+"])
    water_inlet_flow = value(prop_in.flow_mass_phase_comp["Liq", "H2O"])
    tds_inlet_flow = value(prop_in.flow_mass_phase_comp["Liq", "TDS"])
    rho_val = value(m.fs.rho)
    
    print(f"Inlet Li+ flow: {li_inlet_flow} kg/s")
    print(f"Inlet water flow: {water_inlet_flow} kg/s")
    print(f"Inlet TDS flow: {tds_inlet_flow} kg/s")
    print(f"Density: {rho_val} kg/m³")
    
    # Define the polynomial coefficients
    a = 88.1606
    b_ = -169.2358
    c = 81.4783
    
    # Precipitate concentration model parameters
    precipitate_a = -3.1473e02  # kg/m³, from the model
    precipitate_b = 3.5704e02   # kg/m³, from the model
    
    def li_conc_at_evap(evap_frac):
        """Calculate Li+ concentration at given evaporation fraction"""
        li_mass_frac = max(0, min(a * evap_frac**2 + b_ * evap_frac + c, 1))
        li_outflow = li_inlet_flow * li_mass_frac
        water_outflow = water_inlet_flow * (1 - evap_frac)
        
        # Calculate TDS outflow using the same methodology as the flowsheet
        precipitate_concentration = precipitate_a * (1 - evap_frac) + precipitate_b
        original_water_volume = water_inlet_flow / 1000  # m³/s (assuming density = 1000 kg/m³)
        tds_precipitated = precipitate_concentration * original_water_volume  # kg/s
        
        # TDS outflow = TDS inlet - TDS precipitated
        tds_outflow = max(0, tds_inlet_flow - tds_precipitated)
        
        # Calculate total mass outflow (excluding Li+ for concentration calculation)
        total_mass_outflow = water_outflow + tds_outflow
        
        if total_mass_outflow < 1e-12:
            return 0
        
        # Lithium concentration in g/kg
        return li_outflow / total_mass_outflow * 1000
    
    def objective_function(evap_frac, target_conc):
        """Objective function for root finding"""
        return li_conc_at_evap(evap_frac) - target_conc
    
    # Test different evaporation fractions
    evap_fractions = np.linspace(0.01, 0.99, 100)
    concentrations = []
    mass_fractions = []
    
    for evap_frac in evap_fractions:
        conc = li_conc_at_evap(evap_frac)
        concentrations.append(conc)
        
        # Calculate mass fraction
        mass_frac = max(0, min(a * evap_frac**2 + b_ * evap_frac + c, 1))
        mass_fractions.append(mass_frac)
    
    # Find the range of achievable concentrations
    min_conc = min(concentrations)
    max_conc = max(concentrations)
    
    print(f"\nAchievable Li+ concentration range: {min_conc:.3f} to {max_conc:.3f} g/kg")
    
    # Test the current target
    target_conc = 20  # g/kg (from the model)
    print(f"Current target: {target_conc} g/kg")
    
    # Check if target is achievable
    if target_conc < min_conc or target_conc > max_conc:
        print(f"WARNING: Target concentration {target_conc} g/kg is outside achievable range!")
        print(f"Target must be between {min_conc:.3f} and {max_conc:.3f} g/kg")
    else:
        print(f"Target concentration {target_conc} g/kg is achievable")
    
    # Test root finding at bracket endpoints
    f_a = objective_function(0.01, target_conc)
    f_b = objective_function(0.99, target_conc)
    print(f"\nRoot finding test:")
    print(f"f(0.01) = {f_a:.6f}")
    print(f"f(0.99) = {f_b:.6f}")
    print(f"Signs different: {np.sign(f_a) != np.sign(f_b)}")
    
    # Detailed analysis of the root finding issue
    print(f"\n=== DETAILED ROOT FINDING ANALYSIS ===")
    print(f"The root_scalar function requires f(a) and f(b) to have different signs.")
    print(f"This means the function must cross zero between the bracket endpoints.")
    print(f"Let's analyze what's happening:")
    
    # Test multiple target values to see the pattern
    test_targets = [1.5, 10, 25, 50, 52]
    print(f"\nTesting different target concentrations:")
    for target in test_targets:
        f_a = objective_function(0.01, target)
        f_b = objective_function(0.99, target)
        signs_different = np.sign(f_a) != np.sign(f_b)
        print(f"  Target {target:5.1f} g/kg: f(0.01)={f_a:8.3f}, f(0.99)={f_b:8.3f}, signs_different={signs_different}")
    
    # Find where the function crosses zero
    print(f"\nFinding where the function crosses zero:")
    # Test more granular points to find the crossing
    fine_evap = np.linspace(0.01, 0.99, 1000)
    fine_obj_values = [objective_function(evap, target_conc) for evap in fine_evap]
    
    # Find sign changes
    sign_changes = []
    for i in range(1, len(fine_obj_values)):
        if np.sign(fine_obj_values[i-1]) != np.sign(fine_obj_values[i]):
            sign_changes.append((fine_evap[i-1], fine_evap[i], fine_obj_values[i-1], fine_obj_values[i]))
    
    if sign_changes:
        print(f"  Found {len(sign_changes)} sign change(s):")
        for i, (evap1, evap2, val1, val2) in enumerate(sign_changes):
            print(f"    Between evap_frac={evap1:.4f} and {evap2:.4f}")
            print(f"    Values: {val1:.6f} and {val2:.6f}")
    else:
        print(f"  No sign changes found in the bracket [0.01, 0.99]")
        print(f"  This means the target concentration {target_conc} g/kg cannot be achieved")
        print(f"  with any evaporation fraction in this range.")
    
    # Create visualization
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6))
    
    # Plot 1: Concentration vs Evaporation Fraction
    ax1.plot(evap_fractions, concentrations, 'b-', linewidth=2, label='Li+ Concentration')
    ax1.axhline(y=target_conc, color='r', linestyle='--', label=f'Target ({target_conc} g/kg)')
    ax1.axhline(y=min_conc, color='g', linestyle=':', label=f'Min ({min_conc:.3f} g/kg)')
    ax1.axhline(y=max_conc, color='g', linestyle=':', label=f'Max ({max_conc:.3f} g/kg)')
    ax1.set_xlabel('Evaporation Fraction')
    ax1.set_ylabel('Li+ Concentration (g/kg)')
    ax1.set_title('Li+ Concentration vs Evaporation Fraction (with TDS)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Mass Fraction vs Evaporation Fraction
    ax2.plot(evap_fractions, mass_fractions, 'r-', linewidth=2, label='Li+ Mass Fraction')
    ax2.set_xlabel('Evaporation Fraction')
    ax2.set_ylabel('Li+ Mass Fraction')
    ax2.set_title('Li+ Mass Fraction vs Evaporation Fraction')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Objective Function vs Evaporation Fraction
    obj_values = [objective_function(evap, target_conc) for evap in evap_fractions]
    ax3.plot(evap_fractions, obj_values, 'purple', linewidth=2, label=f'Objective (target={target_conc})')
    ax3.axhline(y=0, color='k', linestyle='-', alpha=0.5, label='Zero line')
    ax3.set_xlabel('Evaporation Fraction')
    ax3.set_ylabel('Objective Function Value')
    ax3.set_title('Root Finding Objective Function')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('evaporation_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # Find feasible target range
    print(f"\nFeasible target Li+ concentration range:")
    print(f"  Minimum: {min_conc:.3f} g/kg")
    print(f"  Maximum: {max_conc:.3f} g/kg")
    
    # Test different inlet conditions
    print(f"\nTesting different inlet Li+ concentrations:")
    inlet_concentrations = [0.5, 1.0, 2.0, 5.0, 10.0]  # kg/s
    
    for li_in in inlet_concentrations:
        # Update the model
        m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "Li+"].fix(li_in)
        
        # Recalculate
        concentrations_test = []
        for evap_frac in evap_fractions:
            conc = li_conc_at_evap(evap_frac)
            concentrations_test.append(conc)
        
        min_conc_test = min(concentrations_test)
        max_conc_test = max(concentrations_test)
        
        print(f"  Inlet Li+: {li_in} kg/s -> Range: {min_conc_test:.3f} to {max_conc_test:.3f} g/kg")
    
    return m, evap_fractions, concentrations, mass_fractions

if __name__ == "__main__":
    analyze_evaporation_function() 