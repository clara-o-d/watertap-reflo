"""
Parameter sweep for lithium extraction flowsheet (fs.py)

Input parameters:
- number_of_wells: Number of extraction wells (200 to 500)
- piping_length: Piping length from wells to pond (0.5 to 2.0 km)  
- pumping_efficiency: Pumping efficiency fraction (0.6 to 0.8)

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
from pyomo.environ import assert_optimal_termination
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
 
    sweep_params['number_of_wells'] = LinearSample(
        m.fs.number_of_wells, 200, 500, 3
    )
    
    sweep_params['piping_length'] = LinearSample(
        m.fs.piping_length, 0.5, 2.0, 3
    )
    
    sweep_params['pumping_efficiency'] = LinearSample(
        m.fs.pumping_efficiency, 0.6, 0.8, 3
    )
    
    return sweep_params

def build_outputs(m, **kwargs):
    """Define the outputs to track"""
    outputs = dict()
    
    # User-specified output metrics
    outputs['LCOLi_mass (USD/mt)'] = m.fs.costing.LCOLi_mass
    outputs['aggregate_capital_cost (USD)'] = m.fs.costing.aggregate_capital_cost
    outputs['aggregate_operating_cost (USD/year)'] = m.fs.costing.total_operating_cost
    outputs['fraction_evaporated'] = m.fs.fraction_evaporated
    
    # Input parameters (for verification that they match)
    outputs['number_of_wells'] = m.fs.number_of_wells
    outputs['piping_length'] = m.fs.piping_length
    outputs['pumping_efficiency'] = m.fs.pumping_efficiency
    
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