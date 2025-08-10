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
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.solve import solve
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.add_costing import add_costing
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.process_costing import process_costing
from pyomo.environ import assert_optimal_termination, TerminationCondition
from watertap.core.solvers import get_solver
import os

def build_model(**kwargs): 
    """Build the lithium extraction flowsheet model with parameter sweep capability"""
    
    m = build_flowsheet()

    # Solve the base flowsheet
    results = solve(m)
    
    # Add costing
    # add_costing(m)
    # solve(m)
    
    return m

def build_sweep_params(m, **kwargs):
    """Define the parameters to sweep"""
    sweep_params = dict()
 
    sweep_params['Number of wells'] = LinearSample(
        m.fs.number_of_wells, 320, 330, 2
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
    # outputs['LCOLi_mass (USD/mt)'] = m.fs.costing.LCOLi_mass
    # outputs['aggregate_capital_cost (USD)'] = m.fs.costing.aggregate_capital_cost
    # outputs['aggregate_fixed_operating_cost (USD/year)'] = m.fs.costing.aggregate_fixed_operating_cost
    # outputs['aggregate_variable_operating_cost (USD/year)'] = m.fs.costing.aggregate_variable_operating_cost
    # outputs['total_capital_cost (USD)'] = m.fs.costing.total_capital_cost
    # outputs['total_operating_cost (USD/year)'] = m.fs.costing.total_operating_cost
    # outputs['fraction_evaporated'] = m.fs.fraction_evaporated
    
    # Input parameter (for verification that it matches)
    outputs['Number of wells'] = m.fs.number_of_wells
    # Additional useful outputs
    # outputs['Li outflow (kg/s)'] = m.fs.li_outflow
    # outputs['Concentrated brine outflow (kg/s)'] = m.fs.concentrated_brine_outflow
    
    return outputs

def optimize_function(m, **kwargs):
    """Optimize the flowsheet"""
    solver = get_solver()

    # Try with default settings first
    print("Attempting solve with default solver settings...")
    try:
        results = solver.solve(m, tee=True)
        tc = results.solver.termination_condition
    except Exception as e:
        print(f"Default solve failed with exception: {e}")
        results = None
        tc = None

    # If first attempt fails, try with improved settings
    if (results is None or tc != TerminationCondition.optimal):
        #input("Default solve failed. Press Enter to try with improved settings...")
        solver.options = {
            "tol": 1e-5,
            "constr_viol_tol": 1e-5,
            "acceptable_constr_viol_tol": 1e-5,
            "bound_push": 1e-5,
            "bound_frac": 1e-5,
            "max_iter": 1000,
            "linear_solver": "ma27",
            "hessian_approximation": "limited-memory",
            "mu_strategy": "adaptive",
            "mu_oracle": "probing",
            "alpha_for_y": "primal",
            "slack_bound_push": 0.01,
            "slack_bound_frac": 0.01,
            "print_level": 5,
            "warm_start_init_point": "yes",
            "warm_start_bound_push": 1e-5,
            "warm_start_mult_bound_push": 1e-5,
        }
        try:
            results = solver.solve(m, tee=True)
            tc = results.solver.termination_condition
        except Exception as e:
            print(f"Second solve failed with exception: {e}")
            results = None
            tc = None

    return results

if __name__ == "__main__":
    # Perform sweep
    print("Starting parameter sweep for lithium extraction flowsheet...")
    parameter_sweep(
        build_model, 
        build_sweep_params, 
        build_outputs,
        csv_results_file_name='extraction_sensitivity.csv', 
        h5_results_file_name='extraction_sensitivity.h5',
        optimize_function=optimize_function,
    )
    print("Parameter sweep completed successfully!")
    print("Results saved to 'extraction_sensitivity.csv' and 'extraction_sensitivity.h5'") 