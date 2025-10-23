"""
Parameter sweep for lithium extraction flowsheet (fs.py)
"""

from parameter_sweep import parameter_sweep, LinearSample
from idaes.core.util.initialization import propagate_state
from watertap_contrib.reflo.analysis.example_flowsheets.li_processing.pc_build_flowsheet import build_flowsheet
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.solve import solve
from watertap_contrib.reflo.analysis.example_flowsheets.li_processing.add_costing import add_costing
from watertap_contrib.reflo.analysis.example_flowsheets.li_processing.process_costing import process_costing
from pyomo.environ import TerminationCondition
from watertap.core.solvers import get_solver
import os

def build_model(**kwargs): 
    """Build the lithium extraction flowsheet model with parameter sweep capability."""
    
    m = build_flowsheet()

    # Solve the base flowsheet
    results = solve(m)
    
    # Add costing
    add_costing(m)
    process_costing(m)
    
    return m

def build_sweep_params(m, **kwargs):
    """Define the parameters to sweep."""
    sweep_params = dict()

    sweep_params['Inlet Li+ concentration'] = LinearSample(
        m.fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", "Li"], 0.2, 0.3, 3
    )
    sweep_params['Soda ash dose'] = LinearSample(
        m.fs.soda_ash_reactor.reagent_dose["Na2CO3"], 1.0e-3, 1.5e-3, 3
    )
    sweep_params['Li Dewatering Split Fraction'] = LinearSample(
        m.fs.li_dewatering.split_fraction[0, "overflow", "Li"], 0.1, 0.2, 3
    )

    return sweep_params

def build_outputs(m, **kwargs):
    """Define the outputs to track."""
    if m is None:
        # Return dictionary with None values if model failed
        return {
            'LCOLi2CO3 (USD/kg)': None,
        }
    
    outputs = dict()
    
    outputs['LCOLi2CO3 (USD/kg)'] = m.fs.costing.LCOLi2CO3_mass

    outputs['Resultant inlet Li+ concentration'] = m.fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", "Li"]
    outputs['Resultant soda ash dose'] = m.fs.soda_ash_reactor.reagent_dose["Na2CO3"]
    outputs['Resultant Li Dewatering Split Fraction'] = m.fs.li_dewatering.split_fraction[0, "overflow", "Li"]
    
    return outputs

def optimize_function(m, **kwargs):
    """Optimize the flowsheet with fallback solver options."""
    solver = get_solver()
    # m.fs.feed.initialize()
    # propagate_state(m.fs.feed_to_pond)
    # m.fs.pond.initialize()

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
    print("Starting parameter sweep for lithium processing flowsheet...")
    parameter_sweep(
        build_model, 
        build_sweep_params, 
        build_outputs,
        csv_results_file_name='processing_parameter_sweep.csv', 
        h5_results_file_name='parameter_sweep.h5',
        optimize_function=optimize_function,
    )
    print("Parameter sweep completed successfully!")
    print("Results saved to 'processing_parameter_sweep.csv'") 