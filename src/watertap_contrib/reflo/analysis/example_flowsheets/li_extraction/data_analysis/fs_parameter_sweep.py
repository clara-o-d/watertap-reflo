"""
Parameter sweep for lithium extraction flowsheet (fs.py)
"""

from parameter_sweep import parameter_sweep, LinearSample
from idaes.core.util.initialization import propagate_state
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.build_flowsheet import build_flowsheet
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.solve import solve
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.add_costing import add_costing
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.process_costing import process_costing
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
    
    return m

def build_sweep_params(m, **kwargs):
    """Define the parameters to sweep."""
    sweep_params = dict()
 
    # sweep_params['Government agreements cost'] = LinearSample(
    #     m.fs.government_agreements_unit_cost, 1.2, 1.4, 3
    # )

    # sweep_params['Pond liner cost'] = LinearSample(
    #     m.fs.costing.evaporation_pond.nominal_liner_capital_cost_base, 14500, 15500, 3
    # )

    # sweep_params['Recovered solids cost'] = LinearSample(
    #     m.fs.costing.recovered_solids.cost, 0.01, 0.02, 3
    # )

    # sweep_params['Shipping cost'] = LinearSample(
    #     m.fs.shipping_unit_cost, 1.0e-4, 1.2e-4, 3
    # )

    # sweep_params['Electricity cost'] = LinearSample(
    #     m.fs.costing.electricity_cost, 0.14, 0.18, 3
    # )

    sweep_params['Inlet Li+ concentration'] = LinearSample(
        m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "Li+"], 0.4, 2.56, 25
    )
    sweep_params['Inlet TDS concentration'] = LinearSample(
        m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "TDS"], 200, 453, 25
    )

    # sweep_params['Inlet vapor temperature'] = LinearSample(
    #     m.fs.feed.properties[0].temperature["Vap"], 290, 310, 3
    # )

    # sweep_params['Evaporation rate adjustment factor'] = LinearSample(
    #     m.fs.pond.evaporation_rate_salinity_adjustment_factor, 0.69, 0.81, 5
    # )

    # sweep_params['Pipeline friction head'] = LinearSample(
    #     m.fs.friction_head, 800, 1000, 3
    # )
    sweep_params['Final Li+ concentration'] = LinearSample(
        m.fs.final_li_conc, 0.02, 0.02, 1
    )
    sweep_params['Final TDS concentration'] = LinearSample(
        m.fs.final_tds_conc, 0.315, 0.315, 1
    )
    # sweep_params['Dike height'] = LinearSample(
    #     m.fs.number_of_wells, 379, 379, 1
    # )
    # sweep_params['Pipeline length'] = LinearSample(
    #     m.fs.piping_length, 4.0, 6.0, 3
    # )
    # sweep_params['Utilization factor'] = LinearSample(
    #     m.fs.costing.utilization_factor, 0.95, 1.0, 3
    # )

    return sweep_params

def build_outputs(m, **kwargs):
    """Define the outputs to track."""
    if m is None:
        # Return dictionary with None values if model failed
        return {
            'LCOLi_mass (USD/mt)': None,
            'aggregate_capital_cost (USD)': None,
            'total_operating_cost (USD/year)': None,
            'fraction_evaporated': None,
        }
    
    outputs = dict()
    
    outputs['LCOLi (USD/t)'] = m.fs.costing.LCOLi_mass
    outputs['aggregate_capital_cost (USD)'] = m.fs.costing.aggregate_capital_cost
    outputs['aggregate_fixed_operating_cost (USD/year)'] = m.fs.costing.aggregate_fixed_operating_cost
    outputs['aggregate_variable_operating_cost (USD/year)'] = m.fs.costing.aggregate_variable_operating_cost
    outputs['total_capital_cost (USD)'] = m.fs.costing.total_capital_cost
    outputs['total_operating_cost (USD/year)'] = m.fs.costing.total_operating_cost
    outputs['fraction_evaporated'] = m.fs.fraction_evaporated
    
    # Input parameter (for verification that it matches)
    # outputs['Resultant government agreements cost'] = m.fs.government_agreements_unit_cost
    # outputs['Resultant pond liner cost'] = m.fs.costing.evaporation_pond.nominal_liner_capital_cost_base
    # outputs['Resultant recovered solids cost'] = m.fs.costing.recovered_solids.cost
    # outputs['Resultant shipping cost'] = m.fs.shipping_unit_cost
    # outputs['Resultant electricity cost'] = m.fs.costing.electricity_cost

    # outputs['Resultant evaporation rate adjustment factor'] = m.fs.pond.evaporation_rate_salinity_adjustment_factor
    outputs['Resultant inlet Li+ concentration'] = m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "Li+"]
    outputs['Resultant inlet TDS concentration'] = m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "TDS"]
    # outputs['Resultant inlet vapor temperature'] = m.fs.feed.properties[0].temperature["Vap"]
    # outputs['Resultant pipeline friction head'] = m.fs.friction_head

    outputs['Resultant final Li+ concentration'] = m.fs.final_li_conc
    outputs['Resultant final TDS concentration'] = m.fs.final_tds_conc
    # outputs['Resultant pipeline length'] = m.fs.piping_length
    # outputs['Resultant utilization factor'] = m.fs.costing.utilization_factor
    # # Additional useful outputs
    # outputs['Li outflow (kg/s)'] = m.fs.li_outflow
    # outputs['Concentrated brine outflow (kg/s)'] = m.fs.concentrated_brine_outflow
    
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
    print("Starting parameter sweep for lithium extraction flowsheet...")
    parameter_sweep(
        build_model, 
        build_sweep_params, 
        build_outputs,
        csv_results_file_name='parameter_sweep2.csv', 
        h5_results_file_name='parameter_sweep.h5',
        optimize_function=optimize_function,
    )
    print("Parameter sweep completed successfully!")
    print("Results saved to 'parameter_sweep.csv' and 'parameter_sweep.h5'") 