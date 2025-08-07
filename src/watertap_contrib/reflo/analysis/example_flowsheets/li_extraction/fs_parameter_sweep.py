"""
Parameter sweep for lithium extraction flowsheet (fs.py)

Input parameters:
- target_li_concentration: Target Li+ concentration in outflow (100-300 g/kg)

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
 
    sweep_params['Target Li+ concentration'] = LinearSample(
        m.fs.target_li_concentration, 1.736842e+00, 2, 2
    )

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
    
    # Input parameter (for verification that it matches)
    outputs['Resultant target Li+ concentration'] = m.fs.target_li_concentration
        
    # Additional useful outputs
    outputs['total_evaporative_area (m²)'] = m.fs.pond.total_evaporative_area_required
    outputs['Lithium outflow (kg/s)'] = m.fs.li_outflow
    outputs['Concentrated brine outflow (kg/s)'] = m.fs.concentrated_brine_outflow
    
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