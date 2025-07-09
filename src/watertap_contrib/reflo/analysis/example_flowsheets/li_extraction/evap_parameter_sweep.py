from parameter_sweep import parameter_sweep, LinearSample
import claras_evap_fs as claras_evap_fs
import os


# Build model
def build_model(**kwargs):
    # Get the directory where this script is located
    this_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Use the processed weather data file (choose one that exists)
    weather_data_path = os.path.join(this_dir, "station34_processed_weather.csv")
    
    # Check if the file exists, otherwise try alternative
    if not os.path.exists(weather_data_path):
        weather_data_path = os.path.join(this_dir, "evaporation_pond_test_data.csv")
    
    # Build the model with the weather data
    m = claras_evap_fs.build(weather_data_path)
    claras_evap_fs.set_operating_conditions(m)
    claras_evap_fs.initialize_system(m)
    claras_evap_fs.solve(m)
    # Add and initialize costing
    claras_evap_fs.add_costing(m)
    claras_evap_fs.initialize_costing(m)
    claras_evap_fs.process_costing(m)
    return m

# Parameters to sweep - tighter bounds and a few more parameters
def build_sweep_params(m, num_samples=3, **kwargs):
    sweep_params = dict()
    # 1. Evaporation rate enhancement factor (default ~1.08)
    m.fs.pond.evaporation_rate_enhancement_adjustment_factor.unfix()
    sweep_params['evaporation enhancement factor'] = LinearSample(
        m.fs.pond.evaporation_rate_enhancement_adjustment_factor, 
        1.0, 1.15, num_samples  # Tighter range
    )
    # 2. Salinity adjustment factor (default ~0.75)
    m.fs.pond.evaporation_rate_salinity_adjustment_factor.set_value(0.75)
    sweep_params['salinity adjustment factor'] = LinearSample(
        m.fs.pond.evaporation_rate_salinity_adjustment_factor, 
        0.7, 0.8, num_samples  # Tighter range
    )
    # 3. Pond depth (default 18 inches)
    sweep_params['pond depth (inches)'] = LinearSample(
        m.fs.pond.evaporation_pond_depth, 
        17, 19, num_samples  # Tighter range
    )
    # # 4. Solids precipitation a1 (default 4.12e-6)
    # sweep_params['solids precipitation a1'] = LinearSample(
    #     m.fs.pond.solids_precipitation_rate_a1, 
    #     3.5e-6, 4.5e-6, num_samples  # Tighter range
    # )
    # # 5. Area correction factor base (default depends on dike height, e.g. 2.0512 for 8 ft)
    # sweep_params['area correction factor base'] = LinearSample(
    #     m.fs.pond.area_correction_factor_base, 
    #     2.0, 2.1, num_samples
    # )
    # # 6. Water activity param1 (default -0.00056678)
    # sweep_params['water activity param1'] = LinearSample(
    #     m.fs.pond.water_activity_param1, 
    #     -0.0006, -0.0005, num_samples
    # )
    # # 7. Shortwave albedo (default 0.05)
    # sweep_params['shortwave albedo'] = LinearSample(
    #     m.fs.pond.shortwave_albedo, 
    #     0.04, 0.06, num_samples
    # )
    return sweep_params

# Outputs - only pond capital cost
def build_outputs(m, **kwargs):
    outputs = dict()
    outputs['pond capital cost (USD_2023)'] = m.fs.pond.costing.capital_cost
    return outputs

# Perform sweep
parameter_sweep(
    build_model, 
    build_sweep_params, 
    build_outputs, 
    csv_results_file_name='pond_sensitivity.csv', 
    h5_results_file_name='pond_sensitivity.h5'
)