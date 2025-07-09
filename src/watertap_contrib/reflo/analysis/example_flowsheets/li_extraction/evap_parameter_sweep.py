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

# Parameters to sweep - using more reasonable ranges to avoid nan values
def build_sweep_params(m, num_samples=3, **kwargs):
    sweep_params = dict()
    
    # 1. Evaporation rate enhancement factor - more conservative range
    # This affects evaporation rate directly, but too high values can cause issues
    m.fs.pond.evaporation_rate_enhancement_adjustment_factor.unfix()
    sweep_params['evaporation enhancement factor'] = LinearSample(
        m.fs.pond.evaporation_rate_enhancement_adjustment_factor, 
        1.0, 1.2, num_samples  # More conservative range
    )
    
    # 2. Salinity adjustment factor - affects evaporation for high TDS
    # Higher values mean less reduction in evaporation due to salinity
    m.fs.pond.evaporation_rate_salinity_adjustment_factor.set_value(0.75)  # Reset to default
    sweep_params['salinity adjustment factor'] = LinearSample(
        m.fs.pond.evaporation_rate_salinity_adjustment_factor, 
        0.65, 0.85, num_samples  # More conservative range
    )
    
    # 3. Pond depth - affects heat storage and temperature dynamics
    # Deeper ponds have more thermal mass but may have different evaporation characteristics
    sweep_params['pond depth (inches)'] = LinearSample(
        m.fs.pond.evaporation_pond_depth, 
        16, 20, num_samples  # More conservative range around default of 18
    )
    
    # 4. Solids precipitation rate parameters - affect maintenance costs
    # These affect the rate at which solids precipitate, which impacts pond design
    sweep_params['solids precipitation a1'] = LinearSample(
        m.fs.pond.solids_precipitation_rate_a1, 
        3e-6, 5e-6, num_samples  # More conservative range around default of 4.12e-6
    )
    
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