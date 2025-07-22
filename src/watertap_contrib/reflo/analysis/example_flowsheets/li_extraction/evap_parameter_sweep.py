from parameter_sweep import parameter_sweep, LinearSample
import claras_evap_fs_simple_outlet_simplified as claras_evap_fs
import os
# Build model
def build_model(**kwargs): 
    this_dir = os.path.dirname(os.path.abspath(__file__))
    
    weather_data_path = os.path.join(this_dir, "station34_processed_weather.csv")
    
    if not os.path.exists(weather_data_path):
        weather_data_path = os.path.join(this_dir, "evaporation_pond_test_data.csv")
    
    m = claras_evap_fs.build(weather_data_path)

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
    claras_evap_fs.solve(m)
    claras_evap_fs.add_costing(m)
    claras_evap_fs.initialize_costing(m)
    claras_evap_fs.process_costing(m)
    return m

def build_sweep_params(m, **kwargs):
    sweep_params = dict()
    # Main process parameters
    sweep_params['target_li_concentration (g/kg)'] = LinearSample(
        m.fs.target_li_concentration, 0.01, 0.1, 10
    )
    sweep_params['flow_vol (m3/s)'] = LinearSample(
        m.fs.flow_vol, 0.5, 2.0, 3
    )
    sweep_params['conc_li_inlet (kg/m3)'] = LinearSample(
        m.fs.conc_li_inlet, 0.5, 3.0, 3
    )
    sweep_params['rho (kg/m3)'] = LinearSample(
        m.fs.rho, 1100, 1400, 3
    )
    return sweep_params

# Outputs - expanded to include more relevant outputs
def build_outputs(m, **kwargs):
    outputs = dict()
    outputs['levelized cost of lithium (USD_2023/m^3)'] = m.fs.costing.LCOLi
    outputs['pond capital cost (USD_2023)'] = m.fs.pond.costing.capital_cost
    outputs['fraction evaporated'] = m.fs.fraction_evaporated
    outputs['actual Li+ concentration outflow (kg/m3)'] = m.fs.li_concentration_outflow
    outputs['actual Li+ outflow (kg/s)'] = m.fs.li_outflow
    outputs['water outflow (kg/s)'] = m.fs.water_outflow
    outputs['total evaporative area required (m2)'] = m.fs.pond.total_evaporative_area_required
    outputs['mass flow of precipitate (kg/year)'] = m.fs.pond.mass_flow_precipitate
    outputs['resultant flow_vol (m3/s)'] = m.fs.flow_vol
    outputs['resultant conc_li_inlet (kg/m3)'] = m.fs.conc_li_inlet
    outputs['resultant rho (kg/m3)'] = m.fs.rho
    outputs['resultant target_li_concentration (g/kg)'] = m.fs.target_li_concentration
    return outputs

# Perform sweep
parameter_sweep(
    build_model, 
    build_sweep_params, 
    build_outputs, 
    csv_results_file_name='pond_sensitivity.csv', 
    h5_results_file_name='pond_sensitivity.h5'
)