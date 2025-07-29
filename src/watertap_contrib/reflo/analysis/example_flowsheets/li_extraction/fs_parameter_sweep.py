"""
Parameter sweep for lithium extraction flowsheet (fs.py)

Input parameters:
- land_cost: Land cost for evaporation ponds (9000-11000 USD/acre)
- pond_liner_cost: Pond liner capital cost base (4500-5500 USD/acre)
- solids_handling_cost: Recovered solids handling cost (-0.10 to 0.10 USD/kg)
- dye_cost: Organic dye cost (7000-9000 USD/acre)
- shipping_cost: Shipping cost per kg per km (2.5e-5 to 3.5e-5 USD/kg/km)

Output parameters:
- LCOLi_mass: Levelized cost of lithium by mass (USD/mt)
- aggregate_capital_cost: Total capital costs (USD)
- aggregate_operating_cost: Total operating costs (USD/year)
- fraction_evaporated: Fraction of water evaporated
"""

from parameter_sweep import parameter_sweep, LinearSample
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.build_flowsheet import build_flowsheet
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.define_additional_constraints import define_additional_constraints
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.solve import solve
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.add_costing import add_costing
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.process_costing import process_costing
from pyomo.environ import assert_optimal_termination, TerminationCondition
import os

def build_model(**kwargs): 
    """Build the lithium extraction flowsheet model with parameter sweep capability"""
    
    m = build_flowsheet()

    # Solve the base flowsheet
    results = solve(m)
    
    # Add costing
    add_costing(m)
    process_costing(m)
    
    return m

def build_sweep_params(m, **kwargs):
    """Define the parameters to sweep"""
    sweep_params = dict()
 
    # Create meaningful parameter ranges for costing parameters
    sweep_params['land_cost'] = LinearSample(
        m.fs.costing.evaporation_pond.land_cost, 9000, 11000, 5
    )
    
    sweep_params['pond_liner_cost'] = LinearSample(
        m.fs.costing.evaporation_pond.nominal_liner_capital_cost_base, 4500, 5500, 5
    )
    
    sweep_params['recovered_solids_revenue'] = LinearSample(
        m.fs.costing.recovered_solids.cost, 0, 0.02, 3
    )
    
    sweep_params['dye_cost'] = LinearSample(
        m.fs.costing.organic_dye.cost, 7000, 9000, 3
    )
    
    sweep_params['shipping_cost'] = LinearSample(
        m.fs.shipping_unit_cost, 2.5e-5, 3.5e-5, 5
    )
    # sweep_params['inlet_li_concentration'] = LinearSample(
    #     m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "Li+"], 1.29, 2.58, 5
    # )
    # sweep_params['inlet_vapor_temperature'] = LinearSample(
    #     m.fs.feed.properties[0].temperature, 295, 305, 5
    # )
    # sweep_params['evaporation_rate_adjustment_factor'] = LinearSample(
    #     m.fs.pond.evaporation_rate_enhancement_adjustment_factor, 1.06, 1.1, 5
    # )
    
    return sweep_params

def build_outputs(m, **kwargs):
    """Define the outputs to track"""
    if m is None:
        # Return dictionary with None values if model failed
        return {
            'LCOLi_mass (USD/mt)': None,
            'aggregate_capital_cost (USD)': None,
            'total_operating_cost (USD/year)': None,
            'fraction_evaporated': None,
        }
    
    outputs = dict()
    
    # User-specified output metrics
    outputs['LCOLi_mass (USD/mt)'] = m.fs.costing.LCOLi_mass
    outputs['aggregate_capital_cost (USD)'] = m.fs.costing.aggregate_capital_cost
    outputs['aggregate_fixed_operating_cost (USD/year)'] = m.fs.costing.aggregate_fixed_operating_cost
    outputs['aggregate_variable_operating_cost (USD/year)'] = m.fs.costing.aggregate_variable_operating_cost
    outputs['total_capital_cost (USD)'] = m.fs.costing.total_capital_cost
    outputs['total_operating_cost (USD/year)'] = m.fs.costing.total_operating_cost
    outputs['fraction_evaporated'] = m.fs.fraction_evaporated
    
    # Input parameters (for verification that they match)
    outputs['resultant land_cost (USD/acre)'] = m.fs.costing.evaporation_pond.land_cost
    outputs['resultant pond_liner_cost (USD/acre)'] = m.fs.costing.evaporation_pond.nominal_liner_capital_cost_base
    outputs['resultant recovered_solids_revenue (USD/kg)'] = m.fs.costing.recovered_solids.cost
    outputs['resultant dye_cost (USD/acre)'] = m.fs.costing.organic_dye.cost
    outputs['resultant shipping_cost (USD/kg/km)'] = m.fs.shipping_unit_cost
    # outputs['resultant inlet_li_concentration'] = m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "Li+"]
    # outputs['resultant inlet_vapor_temperature'] = m.fs.feed.properties[0].temperature
    # outputs['resultant evaporation_rate_adjustment_factor'] = m.fs.pond.evaporation_rate_enhancement_adjustment_factor

    # Additional useful outputs
    outputs['li_concentration_outflow (kg/m³)'] = m.fs.li_concentration_outflow
    outputs['total_evaporative_area (m²)'] = m.fs.pond.total_evaporative_area_required
    
    return outputs

if __name__ == "__main__":
    # Perform sweep
    print("Starting parameter sweep for lithium extraction flowsheet...")
    parameter_sweep(
        build_model, 
        build_sweep_params, 
        build_outputs, 
        csv_results_file_name='li_extraction_sensitivity.csv', 
        h5_results_file_name='li_extraction_sensitivity.h5'
    )
    print("Parameter sweep completed successfully!")
    print("Results saved to 'li_extraction_sensitivity.csv' and 'li_extraction_sensitivity.h5'") 