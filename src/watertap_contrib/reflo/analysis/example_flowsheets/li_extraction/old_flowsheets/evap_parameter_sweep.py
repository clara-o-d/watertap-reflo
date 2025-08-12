"""Parameter sweep module for evaporation pond flowsheet.

Performs parameter sweeps on well capital cost and pumping head parameters.
"""

from parameter_sweep import parameter_sweep, LinearSample
import evap_fs_constraints as evap_fs
import os
# Build model
def build_model(**kwargs): 
    """Build the evaporation pond flowsheet model with parameter sweep capability.
    
    Args:
        **kwargs: Optional parameters to set on the model
        
    Returns:
        Pyomo model: Configured flowsheet model
    """
    this_dir = os.path.dirname(os.path.abspath(__file__))
    
    weather_data_path = os.path.join(this_dir, "station34_processed_weather.csv")
    
    if not os.path.exists(weather_data_path):
        weather_data_path = os.path.join(this_dir, "evaporation_pond_test_data.csv")
    
    m = evap_fs.build(weather_data_path)

    # Set sweep parameters if provided
    if "flow_vol" in kwargs:
        m.fs.flow_vol.set_value(kwargs["flow_vol"])
    if "conc_li_inlet" in kwargs:
        m.fs.conc_li_inlet.set_value(kwargs["conc_li_inlet"])
    if "rho" in kwargs:
        m.fs.rho.set_value(kwargs["rho"])
    if "target_li_concentration" in kwargs:
        m.fs.target_li_concentration.set_value(kwargs["target_li_concentration"])

    # Re-apply operating conditions and re-initialize after parameter changes
    evap_fs.solve(m)
    evap_fs.add_costing(m)
    evap_fs.initialize_costing(m)
    evap_fs.process_costing(m)
    return m

def build_sweep_params(m, **kwargs):
    """Define the parameters to sweep.
    
    Args:
        m: Pyomo model
        **kwargs: Additional arguments
        
    Returns:
        dict: Dictionary of sweep parameters
    """
    sweep_params = dict()
    sweep_params['well_capital_cost'] = LinearSample(
        m.fs.extraction.costing.well_capital_cost, 8.5e5, 1e6, 8
    )
    sweep_params['pumping_head'] = LinearSample(
        m.fs.extraction.pumping_head, 5e1, 1.5e2, 8
    )
    return sweep_params

# Outputs - expanded to include more relevant outputs
def build_outputs(m, **kwargs):
    """Define the outputs to track.
    
    Args:
        m: Pyomo model
        **kwargs: Additional arguments
        
    Returns:
        dict: Dictionary of output variables
    """
    outputs = dict()
    outputs['levelized cost of lithium (USD_2023/m^3)'] = m.fs.costing.LCOLi
    outputs['well_capital_cost'] = m.fs.extraction.costing.well_capital_cost
    outputs['pumping_head'] = m.fs.extraction.pumping_head
    outputs['concentrated_brine_outflow (kg/s)'] = m.fs.concentrated_brine_outflow
    return outputs

# Perform sweep
parameter_sweep(
    build_model, 
    build_sweep_params, 
    build_outputs, 
    csv_results_file_name='pond_sensitivity.csv', 
    h5_results_file_name='pond_sensitivity.h5'
)