"""
Parameter sweep for lithium extraction flowsheet (fs.py)
"""

from parameter_sweep import parameter_sweep, LinearSample
from watertap_contrib.reflo.analysis.example_flowsheets.li_processing.pc_build_flowsheet import build_flowsheet
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.solve import solve
from watertap_contrib.reflo.analysis.example_flowsheets.li_processing.add_costing import add_costing
from watertap_contrib.reflo.analysis.example_flowsheets.li_processing.process_costing import process_costing
from pyomo.environ import TerminationCondition
from watertap.core.solvers import get_solver

def build_model(**kwargs): 
    """Build the lithium extraction flowsheet model with parameter sweep capability."""
    
    m = build_flowsheet(stage=5)
    add_costing(m)
    process_costing(m)
    results = solve(m)

    return m

def build_sweep_params(m, **kwargs):
    """Define the parameters to sweep."""
    sweep_params = dict()

    # sweep_params['Annual soda ash (kg/year)'] = LinearSample(
    #     m.fs.annual_soda_ash_input, 100000000, 200000000, 3
    # )
    
    # sweep_params['Annual lime (kg/year)'] = LinearSample(
    #     m.fs.annual_lime_input, 2000000, 5000000, 3
    # )
    
    # sweep_params['Soda ash molality (mol/kg)'] = LinearSample(
    #     m.fs.soda_ash_solution_molality, 20, 40, 3
    # )
    
    # sweep_params['Lime molality (mol/kg)'] = LinearSample(
    #     m.fs.lime_solution_molality, 1.0, 5.0, 5
    # )
    
    # sweep_params['Mg removal fraction (soda ash)'] = LinearSample(
    #     m.fs.magnesium_removal_fraction_soda_ash_reactor, 0.20, 0.70, 3
    # )
    
    # sweep_params['Mg removal fraction (lime)'] = LinearSample(
    #     m.fs.magnesium_removal_fraction_lime_reactor, 0.7, 0.99, 3
    # )
    
    # sweep_params['Ca removal fraction (soda ash)'] = LinearSample(
    #     m.fs.calcium_removal_fraction_soda_ash_reactor, 0.1, 0.4, 3
    # )
    
    # sweep_params['Ca removal fraction (lime)'] = LinearSample(
    #     m.fs.calcium_removal_fraction_lime_reactor, 0.3, 0.7, 3
    # )
    
    # sweep_params['SO4 removal fraction (lime)'] = LinearSample(
    #     m.fs.sulfate_removal_fraction_lime_reactor, 0.7, 0.99, 3
    # )
    
    # sweep_params['Li removal fraction'] = LinearSample(
    #     m.fs.lithium_removal_fraction_lithium_reactor, 0.3, 0.7, 5
    # )

    sweep_params['Pump efficiency'] = LinearSample(
        m.fs.brine_pump.efficiency_pump[0], 0.7, 0.8, 3
    )

    sweep_params['Inlet Li+ flow'] = LinearSample(
        m.fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", "Li"], 100, 150, 5
    )

    sweep_params['Soda ash waste mass fraction'] = LinearSample(
        m.fs.soda_ash_reactor.waste_mass_frac_precipitate, 0.3, 0.7, 3
    )

    return sweep_params

def build_outputs(m, **kwargs):
    """Define the outputs to track."""
    outputs = dict()
    
    # outputs['Output annual soda ash (kg/year)'] = m.fs.annual_soda_ash_input
    # outputs['Output annual lime (kg/year)'] = m.fs.annual_lime_input
    # outputs['Output soda ash molality (mol/kg)'] = m.fs.soda_ash_solution_molality
    # outputs['Output lime molality (mol/kg)'] = m.fs.lime_solution_molality
    # outputs['Output magnesium removal fraction (soda ash)'] = m.fs.magnesium_removal_fraction_soda_ash_reactor_param
    # outputs['Output magnesium removal fraction (lime)'] = m.fs.magnesium_removal_fraction_lime_reactor
    # outputs['Output calcium removal fraction (soda ash)'] = m.fs.calcium_removal_fraction_soda_ash_reactor
    # outputs['Output calcium removal fraction (lime)'] = m.fs.calcium_removal_fraction_lime_reactor
    # outputs['Output sulfate removal fraction (lime)'] = m.fs.sulfate_removal_fraction_lime_reactor
    # outputs['Output lithium removal fraction'] = m.fs.lithium_removal_fraction_lithium_reactor
    
    outputs['Pump efficiency'] = m.fs.brine_pump.efficiency_pump[0]
    outputs['Inlet Li+ flow'] = m.fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", "Li"]
    outputs['Soda ash waste mass fraction'] = m.fs.soda_ash_reactor.waste_mass_frac_precipitate

    outputs['Li2CO3 production (kg/s)'] = m.fs.lithium_carbonate_reactor.flow_mass_precipitate["Li2CO3"]
    outputs['Capital cost (USD)'] = m.fs.costing.total_capital_cost
    outputs['Operating cost (USD/year)'] = m.fs.costing.total_operating_cost
    outputs['LCOLi (USD/t)'] = m.fs.costing.LCOLi_mass
    outputs['Specific energy consumption (kWh/t)'] = m.fs.costing.specific_energy_consumption
    
    return outputs

def optimize_function(m, **kwargs):
    """Optimize the flowsheet with fallback solver options."""
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
    print("Starting parameter sweep for lithium processing flowsheet...")
    parameter_sweep(
        build_model, 
        build_sweep_params, 
        build_outputs,
        csv_results_file_name='parameter_sweep011426_1.csv', 
        h5_results_file_name='parameter_sweep.h5',
        optimize_function=optimize_function,
    )
    print("Parameter sweep completed successfully!")