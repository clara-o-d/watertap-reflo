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
    claras_evap_fs.solve(m)
    claras_evap_fs.add_costing(m)
    claras_evap_fs.initialize_costing(m)
    claras_evap_fs.process_costing(m)
    return m

def build_sweep_params(m, **kwargs):
    sweep_params = dict()
    pond = m.fs.pond

    sweep_params['liner thickness (mil)'] = LinearSample(
        pond.liner_thickness, 40, 80, 3
    )
    sweep_params['liner replacement frequency (years)'] = LinearSample(
        pond_cost.liner_replacement_frequency, 10, 30, 3
    )
    sweep_params['land cost (USD_2001/acre)'] = LinearSample(
        pond_cost.land_cost, 2000, 10000, 3
    )
    sweep_params['recovered solids handling cost (USD_2023/kg)'] = LinearSample(
        pond_cost.recovered_solids_handling_cost, 0, 0.10, 3
    )
    sweep_params['enhancement dose basis (gallon/acre)'] = LinearSample(
        pond_cost.enhancement_dose_basis, 0.1, 1.0, 3
    )
    return sweep_params

# Outputs - expanded to include more relevant outputs
def build_outputs(m, **kwargs):
    outputs = dict()
    pond_cost = m.fs.pond.costing.costing_package.evaporation_pond

    outputs['levelized cost of lithium (USD_2023/m^3)'] = m.fs.costing.LCOLi
    outputs['pond capital cost (USD_2023)'] = m.fs.pond.costing.capital_cost

    outputs['resultant liner thickness (mil)'] = pond_cost.liner_thickness
    outputs['resultant liner replacement frequency (years)'] = pond_cost.liner_replacement_frequency
    outputs['resultant land cost (USD_2001/acre)'] = pond_cost.land_cost
    outputs['resultant recovered solids handling cost (USD_2023/kg)'] = pond_cost.recovered_solids_handling_cost
    outputs['resultant enhancement dose basis (gallon/acre)'] = pond_cost.enhancement_dose_basis

    return outputs

# Perform sweep
parameter_sweep(
    build_model, 
    build_sweep_params, 
    build_outputs, 
    csv_results_file_name='pond_sensitivity.csv', 
    h5_results_file_name='pond_sensitivity.h5'
)