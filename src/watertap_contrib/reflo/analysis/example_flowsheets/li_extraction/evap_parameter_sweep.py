from parameter_sweep import parameter_sweep, LinearSample
import claras_evap_fs_simple_outlet_simplified_constraints as claras_evap_fs
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

    # New brine extraction and shipping parameters
    sweep_params['number_of_wells'] = LinearSample(
        m.fs.number_of_wells, 50, 200, 3
    )
    sweep_params['piping_length (km)'] = LinearSample(
        m.fs.piping_length, 0.5, 2.0, 3
    )
    sweep_params['pumping_efficiency'] = LinearSample(
        m.fs.pumping_efficiency, 0.5, 0.9, 3
    )
    # sweep_params['pumping_head (m)'] = LinearSample(
    #     m.fs.pumping_head, 50, 200, 3
    # )
    sweep_params['well_capital_cost (USD_2023/well)'] = LinearSample(
        m.fs.well_capital_cost, 1e6, 5e6, 3
    )
    sweep_params['piping_unit_cost (USD_2023/km)'] = LinearSample(
        m.fs.piping_unit_cost, 50000, 200000, 3
    )
    return sweep_params

# Outputs - expanded to include more relevant outputs
def build_outputs(m, **kwargs):
    outputs = dict()
    outputs['levelized cost of lithium (USD_2023/m^3)'] = m.fs.costing.LCOLi

    outputs['total_well_capital_cost (USD_2023)'] = m.fs.total_well_capital_cost
    outputs['total_piping_capital_cost (USD_2023)'] = m.fs.total_piping_capital_cost
    outputs['annual_pumping_cost (USD_2023/year)'] = m.fs.annual_pumping_cost
    outputs['annual_shipping_cost (USD_2023/year)'] = m.fs.annual_shipping_cost
    outputs['concentrated_brine_outflow (kg/s)'] = m.fs.concentrated_brine_outflow
    outputs['resultant number_of_wells'] = m.fs.number_of_wells
    outputs['resultant piping_length (km)'] = m.fs.piping_length
    outputs['resultant pumping_efficiency'] = m.fs.pumping_efficiency
    outputs['resultant pumping_head (m)'] = m.fs.pumping_head
    outputs['resultant shipping_distance (km)'] = m.fs.shipping_distance
    outputs['resultant well_capital_cost (USD_2023/well)'] = m.fs.well_capital_cost
    outputs['resultant piping_unit_cost (USD_2023/km)'] = m.fs.piping_unit_cost
    outputs['resultant shipping_unit_cost (USD_2023/t/km)'] = m.fs.shipping_unit_cost
    return outputs

# Perform sweep
parameter_sweep(
    build_model, 
    build_sweep_params, 
    build_outputs, 
    csv_results_file_name='pond_sensitivity.csv', 
    h5_results_file_name='pond_sensitivity.h5'
)