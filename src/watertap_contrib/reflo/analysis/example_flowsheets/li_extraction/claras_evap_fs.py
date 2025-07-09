"""
Task: Create a simple flowsheet using the detailed EvaporationPond unit model
"""

import os
import pandas as pd
import numpy as np
import pyomo.environ as pyo
from pyomo.environ import (
    assert_optimal_termination,
    ConcreteModel,
    value,
    units as pyunits,
)
from idaes.core import FlowsheetBlock
from idaes.core.util.testing import initialization_tester
from idaes.core.util.model_statistics import degrees_of_freedom
from watertap_contrib.reflo.property_models import (
    AirWaterEq,
    DensityCalculation,
)
from watertap_contrib.reflo.unit_models import EvaporationPond
from watertap.core.solvers import get_solver
from watertap.core.util.initialization import assert_degrees_of_freedom

def preprocess_station34_weather_data(input_file, output_file):
    print(f"Preprocessing Station 34 weather data from {input_file}...")
    
    # Read the raw data
    df = pd.read_csv(input_file)
    
    # Rename columns to match expected format
    column_mapping = {
        "DATETIME [YYYY-MM-DD HH:MM]": "datetime",
        "AirTC [air temperature, °C]": "temperature",
        "RH [air humidity, %]": "relative_humidity", 
        "SlrW_1 [solar radiation flux density (up looking), w/m²]": "shortwave_radiation",
        "BP_mbar [barometric pressure, mbar]": "pressure_mbar"
    }
    
    # Select and rename relevant columns
    df_clean = df[list(column_mapping.keys())].copy()
    df_clean.columns = list(column_mapping.values())
    
    # Convert datetime to pandas datetime
    df_clean['datetime'] = pd.to_datetime(df_clean['datetime'])
    
    # Convert pressure from mbar to kPa
    df_clean['pressure'] = df_clean['pressure_mbar'] / 10.0  # mbar to kPa
    df_clean = df_clean.drop('pressure_mbar', axis=1)
    
    # Clean and validate data
    df_clean['temperature'] = np.maximum(df_clean['temperature'], 0.1)
    df_clean['relative_humidity'] = np.clip(df_clean['relative_humidity'], 0, 100)
    df_clean['shortwave_radiation'] = np.maximum(df_clean['shortwave_radiation'], 0)
    df_clean['pressure'] = np.clip(df_clean['pressure'], 50, 110)
    
    # Resample from 10-minute to hourly data
    df_clean.set_index('datetime', inplace=True)
    df_hourly = df_clean.resample('h').mean()
    df_hourly = df_hourly.ffill()
    
    # Ensure we have exactly 8760 hours
    if len(df_hourly) > 8760:
        df_hourly = df_hourly.head(8760)
    elif len(df_hourly) < 8760:
        last_row = df_hourly.iloc[-1]
        while len(df_hourly) < 8760:
            df_hourly = pd.concat([df_hourly, pd.DataFrame([last_row])], ignore_index=True)
    
    # Rename columns to match the expected format for EvaporationPond
    df_hourly.columns = ['Temperature', 'Relative Humidity', 'GHI', 'Pressure']
    
    # Add the expected header format for the EvaporationPond model
    header_lines = [
        "Station 34 Weather Data - Processed for EvaporationPond Model",
        "Data resampled to hourly intervals, units converted as needed",
        "Temperature,Relative Humidity,GHI,Pressure"
    ]
    
    # Write the processed data
    with open(output_file, 'w') as f:
        for line in header_lines:
            f.write(line + '\n')
        df_hourly.to_csv(f, index=False, header=False)
    
    print(f"Preprocessed Station 34 data saved to {output_file}")
    print(f"Data summary:")
    print(f"  - Temperature range: {df_hourly['Temperature'].min():.1f} to {df_hourly['Temperature'].max():.1f} °C")
    print(f"  - RH range: {df_hourly['Relative Humidity'].min():.1f} to {df_hourly['Relative Humidity'].max():.1f} %")
    print(f"  - Solar radiation range: {df_hourly['GHI'].min():.1f} to {df_hourly['GHI'].max():.1f} W/m²")
    print(f"  - Pressure range: {df_hourly['Pressure'].min():.1f} to {df_hourly['Pressure'].max():.1f} kPa")
    
    return output_file

def preprocess_openmeteo_weather_data(input_file, output_file):
    print(f"Preprocessing Open-Meteo weather data from {input_file}...")
    
    # Read the raw data - skip the first 3 lines (location info and blank line)
    df = pd.read_csv(input_file, skiprows=3)
    
    # Extract location info from filename
    filename = os.path.basename(input_file)
    location_info = filename.replace('open-meteo-', '').replace('.csv', '')
    
    # Rename columns to match expected format
    column_mapping = {
        "time": "datetime",
        "temperature_2m (°C)": "temperature",
        "relative_humidity_2m (%)": "relative_humidity", 
        "shortwave_radiation (W/m²)": "shortwave_radiation",
        "surface_pressure (hPa)": "pressure_hpa"
    }
    
    # Select and rename relevant columns
    df_clean = df[list(column_mapping.keys())].copy()
    df_clean.columns = list(column_mapping.values())
    
    # Convert datetime to pandas datetime
    df_clean['datetime'] = pd.to_datetime(df_clean['datetime'])
    
    # Convert pressure from hPa to kPa
    df_clean['pressure'] = df_clean['pressure_hpa'] / 10.0  # hPa to kPa
    df_clean = df_clean.drop('pressure_hpa', axis=1)
    
    # Clean and validate data
    df_clean['temperature'] = np.maximum(df_clean['temperature'], 0.1)
    df_clean['relative_humidity'] = np.clip(df_clean['relative_humidity'], 0, 100)
    df_clean['shortwave_radiation'] = np.maximum(df_clean['shortwave_radiation'], 0)
    df_clean['pressure'] = np.clip(df_clean['pressure'], 50, 110)
    
    # Data is already hourly, just ensure we have exactly 8760 hours
    df_clean.set_index('datetime', inplace=True)
    if len(df_clean) > 8760:
        df_clean = df_clean.head(8760)
    elif len(df_clean) < 8760:
        last_row = df_clean.iloc[-1]
        while len(df_clean) < 8760:
            df_clean = pd.concat([df_clean, pd.DataFrame([last_row])], ignore_index=True)
    
    # Rename columns to match the expected format for EvaporationPond
    df_clean.columns = ['Temperature', 'Relative Humidity', 'GHI', 'Pressure']
    
    # Add the expected header format for the EvaporationPond model
    header_lines = [
        f"Open-Meteo Weather Data - {location_info} - Processed for EvaporationPond Model",
        "Data already in hourly intervals, units converted as needed",
        "Temperature,Relative Humidity,GHI,Pressure"
    ]
    
    # Write the processed data
    with open(output_file, 'w') as f:
        for line in header_lines:
            f.write(line + '\n')
        df_clean.to_csv(f, index=False, header=False)
    
    print(f"Preprocessed Open-Meteo data saved to {output_file}")
    print(f"Data summary:")
    print(f"  - Temperature range: {df_clean['Temperature'].min():.1f} to {df_clean['Temperature'].max():.1f} °C")
    print(f"  - RH range: {df_clean['Relative Humidity'].min():.1f} to {df_clean['Relative Humidity'].max():.1f} %")
    print(f"  - Solar radiation range: {df_clean['GHI'].min():.1f} to {df_clean['GHI'].max():.1f} W/m²")
    print(f"  - Pressure range: {df_clean['Pressure'].min():.1f} to {df_clean['Pressure'].max():.1f} kPa")
    
    return output_file

def preprocess_weather_data(input_file, output_file, data_type="auto"):
    if data_type == "auto":
        filename = os.path.basename(input_file).lower()
        if "station" in filename and "34" in filename:
            data_type = "station34"
        elif "open-meteo" in filename:
            data_type = "openmeteo"
        else:
            raise ValueError(f"Could not auto-detect data type from filename: {filename}")
    
    if data_type == "station34":
        return preprocess_station34_weather_data(input_file, output_file)
    elif data_type == "openmeteo":
        return preprocess_openmeteo_weather_data(input_file, output_file)
    else:
        raise ValueError(f"Unknown data type: {data_type}")

def main():
    # Choose weather data source
    print("Available weather data sources:")
    print("1. Station 34 (10-minute intervals, converted to hourly)")
    print("2. Open-Meteo (hourly data, Chile location)")
    print("3. Test data (original evaporation pond test data)")
    
    choice = input("Enter your choice (1, 2, or 3): ").strip()
    this_dir = os.path.dirname(os.path.abspath(__file__))
    
    if choice == "1":
        # Station 34 data
        raw_weather_file = os.path.join(this_dir, "station[34]_2024-01-01_2024-12-31.csv")
        processed_weather_file = os.path.join(this_dir, "station34_processed_weather.csv")
        data_type = "station34"
        weather_name = "Station 34"
        
    elif choice == "2":
        # Open-Meteo data
        raw_weather_file = os.path.join(this_dir, "open-meteo-23.66S68.45W2301m.csv")
        processed_weather_file = os.path.join(this_dir, "openmeteo_processed_weather.csv")
        data_type = "openmeteo"
        weather_name = "Open-Meteo (Chile)"
        
    elif choice == "3":
        # Test data (no preprocessing needed)
        processed_weather_file = os.path.join(this_dir, "evaporation_pond_test_data.csv")
        weather_name = "Test Data"
        
    else:
        print("Invalid choice. Using Station 34 data as default.")
        raw_weather_file = os.path.join(this_dir, "station[34]_2024-01-01_2024-12-31.csv")
        processed_weather_file = os.path.join(this_dir, "station34_processed_weather.csv")
        data_type = "station34"
        weather_name = "Station 34"
    
    # Preprocess the weather data if needed
    if choice in ["1", "2"]:
        if not os.path.exists(processed_weather_file):
            preprocess_weather_data(raw_weather_file, processed_weather_file, data_type)
        else:
            print(f"Using existing processed weather file: {processed_weather_file}")
    
    print(f"\nUsing weather data: {weather_name}")
    
    # Get fraction of water to remain as outflow
    print("\nFraction of water to remain as outflow:")
    print("Enter the fraction (between 0 and 0.99) of inlet water that should leave as liquid outflow.")
    print("For example, 0.3 means 30% of inlet water leaves as liquid, 70% is evaporated.")
    print("0 means 100% evaporation (no liquid outflow).")
    print("Default is 0.3 (30% outflow, 70% evaporated)")
    fraction_outflow_input = input("Fraction of water to remain as outflow: ").strip()
    
    if fraction_outflow_input:
        try:
            fraction_outflow = float(fraction_outflow_input)
            if not (0 <= fraction_outflow < 1):
                print("Input out of range. Using default of 0.3.")
                fraction_outflow = 0.3
            else:
                print(f"Using fraction outflow: {fraction_outflow}")
        except ValueError:
            print("Invalid input. Using default of 0.3.")
            fraction_outflow = 0.3
    else:
        fraction_outflow = 0.3
        print("Using default fraction outflow: 0.3")
    
    m = build(processed_weather_file, fraction_outflow=fraction_outflow)
    
    # Set fraction of water to remain as outflow
    set_operating_conditions(m)
    m.fs.pond.number_evaporation_ponds.fix(300)
    assert_degrees_of_freedom(m, 0)
    
    initialize_system(m)
    results = solve(m)
    assert_optimal_termination(results)
    
    display_results(m, weather_name)

    add_costing(m)
    
    initialize_costing(m)
    process_costing(m)
    assert_degrees_of_freedom(m, 0)
    
    # Solve with costing
    results = solve(m)
    assert_optimal_termination(results)
    display_costing_results(m)

def build(weather_data_path, fraction_outflow=0.0):
    m = ConcreteModel()
    m.fs = FlowsheetBlock(dynamic=False)

    # Store the fraction_outflow as a flowsheet parameter
    m.fs.fraction_outflow = pyo.Param(initialize=fraction_outflow, mutable=True)

    props = {
        "non_volatile_solute_list": ["TDS"],
        "mw_data": {"TDS": 31.4038218e-3},
        "density_calculation": DensityCalculation.calculated,
    }
    m.fs.properties = AirWaterEq(**props)

    # Use the default weather data column mapping since we preprocessed the data
    weather_data_column_dict = {
        "pressure": "Pressure",
        "temperature": "Temperature", 
        "shortwave_radiation": "GHI",
        "relative_humidity": "Relative Humidity",
    }

    m.fs.pond = EvaporationPond(
        property_package=m.fs.properties,
        weather_data_path=weather_data_path,
        weather_data_column_dict=weather_data_column_dict,
        dike_height=8,  # 4, 8, or 12
        add_enhancement=True,
    )
    return m

def set_operating_conditions(m):
    flow_vol = 1.051 * pyunits.m**3 / pyunits.s
    conc_tds_inlet = 370 * pyunits.kg / pyunits.m**3
    rho = 1227 * pyunits.kg / pyunits.m**3
    
    # Get fraction_outflow from the flowsheet parameter
    fraction_outflow = value(m.fs.fraction_outflow)
    
    # Calculate fraction evaporated
    fraction_evaporated_val = 1 - fraction_outflow
    print(f"Fraction of water evaporated: {fraction_evaporated_val:.3f}")
    print(f"Fraction of water as outflow: {fraction_outflow:.3f}")
    
    prop_in = m.fs.pond.properties_in[0]
    prop_in.pressure.fix(101325)
    prop_in.temperature["Liq"].fix(298)
    prop_in.temperature["Vap"].fix(293)
    prop_in.flow_mass_phase_comp["Liq", "H2O"].fix(flow_vol * rho)
    prop_in.flow_mass_phase_comp["Liq", "TDS"].fix(flow_vol * conc_tds_inlet)
    prop_in.flow_mass_phase_comp["Vap", "Air"].fix(1)
    prop_in.flow_mass_phase_comp["Vap", "H2O"].fix(0)
    
    m.fs.pond.evaporation_rate_salinity_adjustment_factor.set_value(0.75)
    m.fs.pond.evaporation_rate_enhancement_adjustment_factor.fix(1.08)

    # --- Add variables and expressions for the split ---
    m.fs.fraction_evaporated = pyo.Var(initialize=fraction_evaporated_val, bounds=(0.01, 1.0))
    m.fs.fraction_evaporated.fix(fraction_evaporated_val)
    
    # Calculate evaporated and outflow water
    m.fs.water_evaporated = pyo.Expression(
        expr=prop_in.flow_mass_phase_comp["Liq", "H2O"] * m.fs.fraction_evaporated
    )
    m.fs.water_outflow = pyo.Expression(
        expr=prop_in.flow_mass_phase_comp["Liq", "H2O"] * (1 - m.fs.fraction_evaporated)
    )
    
    # Calculate TDS in outflow (accounting for precipitation)
    m.fs.tds_precipitated = pyo.Expression(
        expr=m.fs.pond.mass_flow_precipitate / (365 * 24 * 3600)  # kg/s
    )
    m.fs.tds_outflow = pyo.Expression(
        expr=prop_in.flow_mass_phase_comp["Liq", "TDS"] - m.fs.tds_precipitated
    )
    
    # Handle TDS concentration calculation for zero outflow case
    m.fs.tds_concentration_outflow = pyo.Expression(
        expr=m.fs.tds_outflow / (m.fs.water_outflow + 1e-12 * pyunits.kg / pyunits.s) * rho
    )
    
    # --- Modify the pond model to only evaporate the calculated fraction ---
    if hasattr(m.fs.pond, 'eq_total_evaporative_area_required'):
        m.fs.pond.eq_total_evaporative_area_required.deactivate()
    
    @m.fs.pond.Constraint(doc="Total evaporative area required for partial evaporation")
    def eq_total_evaporative_area_required_partial(b):
        return (
            b.total_evaporative_area_required * b.mass_flux_water_vapor_average
            == m.fs.water_evaporated
        )

def initialize_system(m):
    try:
        m.fs.pond.initialize()
    except Exception as e:
        print(f"Initialization failed: {e}")
        print("Trying alternative initialization approach...")
        # Try initializing components separately
        m.fs.pond.weather.initialize()
        m.fs.pond.properties_in.initialize()

def solve(m, solver=None):
    if solver is None:
        solver = get_solver()
    results = solver.solve(m, tee=False)
    return results

def display_results(m, weather_name="Unknown"):
    print("\n" + "="*50)
    print(f"EVAPORATION POND RESULTS ({weather_name} Weather Data)")
    print("="*50)
    print(f"Total evaporative area required: {value(m.fs.pond.total_evaporative_area_required):.1f} m²")
    print(f"Number of evaporation ponds: {value(m.fs.pond.number_evaporation_ponds):.0f}")
    print(f"Evaporative area per pond: {value(m.fs.pond.evaporative_area_per_pond):.1f} m²")
    print(f"Evaporation pond area: {value(m.fs.pond.evaporation_pond_area):.1f} m²")
    print(f"Solids precipitation rate: {value(m.fs.pond.solids_precipitation_rate):.4f} ft/yr")
    print(f"Mass flow of precipitate: {value(m.fs.pond.mass_flow_precipitate):.0f} kg/yr")
    print(f"Water activity: {value(m.fs.pond.water_activity):.4f}")
    print(f"Area correction factor: {value(m.fs.pond.area_correction_factor):.4f}")
    print(f"Average mass flux of water vapor: {value(m.fs.pond.mass_flux_water_vapor_average):.2e} kg/(m²·s)")
    print("\n" + "-"*50)
    print("PARTIAL EVAPORATION RESULTS")
    print("-"*50)
    print(f"Fraction of water evaporated: {value(m.fs.fraction_evaporated):.3f}")
    print(f"Water evaporated: {value(m.fs.water_evaporated):.2f} kg/s")
    print(f"Water outflow: {value(m.fs.water_outflow):.2f} kg/s")
    
    # TDS mass balance
    prop_in = m.fs.pond.properties_in[0]
    inlet_tds = value(prop_in.flow_mass_phase_comp["Liq", "TDS"])
    tds_precipitated = value(m.fs.tds_precipitated)
    tds_outflow = value(m.fs.tds_outflow)
    water_outflow = value(m.fs.water_outflow)
    
    print(f"TDS inlet: {inlet_tds:.2f} kg/s")
    print(f"TDS precipitated: {tds_precipitated:.2f} kg/s")
    print(f"TDS outflow: {tds_outflow:.2f} kg/s")
    
    # Handle zero outflow case in display
    if water_outflow < 1e-6:
        print("TDS concentration in outflow: N/A (no liquid outflow)")
        print("Inlet TDS concentration: {:.0f} kg/m³".format(value(prop_in.conc_mass_phase_comp["Liq", "TDS"])))
        print("Concentration factor: N/A (no liquid outflow)")
    else:
        tds_conc_outflow = value(m.fs.tds_concentration_outflow)
        inlet_tds_conc = value(prop_in.conc_mass_phase_comp["Liq", "TDS"])
        concentration_factor = tds_conc_outflow / inlet_tds_conc
        print(f"TDS concentration in outflow: {tds_conc_outflow:.0f} kg/m³")
        print(f"Inlet TDS concentration: {inlet_tds_conc:.0f} kg/m³")
        print(f"Concentration factor: {concentration_factor:.1f}x")
    
    # TDS mass balance check
    tds_balance = inlet_tds - tds_precipitated - tds_outflow
    print(f"TDS mass balance check (should be ~0): {tds_balance:.6f} kg/s")
    print("="*50)

def add_costing(m):
    from idaes.core import UnitModelCostingBlock
    # Import REFLOCosting inside the function to avoid linter errors
    from watertap_contrib.reflo.costing.watertap_reflo_costing_package import REFLOCosting
    
    m.fs.costing = REFLOCosting()
    m.fs.pond.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)

    # Fix global costing parameters
    m.fs.costing.plant_lifetime.fix(25)
    m.fs.costing.wacc.fix(0.10)
    m.fs.costing.electricity_cost.fix(0.16)
    m.fs.costing.electrical_carbon_intensity.fix(0.229)
    m.fs.costing.utilization_factor.fix(0.99)


def initialize_costing(m):
    m.fs.pond.costing.initialize()
    m.fs.costing.cost_process()
    m.fs.costing.initialize()

def process_costing(m):
    pass
    # LCOLi Option 1 (RO_with_energy_recovery.py)
    # Assume solution density = 1226 kg/m³ (Li handbook)
    # density_concentrated_brine = 1323 * pyunits.kg / pyunits.m**3 # Li handbook pg 110
    # # Use outlet flow instead of LCOLi calculation
    # vol_flow_li = m.fs.pond.treated.flow_mass_comp[0, "lithium"] / density_concentrated_brine 
    
    # m.fs.pond.properties_treated[0.0].dens_mass[...]
    # m.fs.pond.properties_treated[0.0].pprint()
    # # print(f"vol_flow_li: {value(vol_flow_li)}")
    # m.fs.costing.add_LCOW(vol_flow_li, name="LCOLi")
    # m.fs.costing.LCOLi_mass = pyo.Var(

    # )
    # @m.fs.costing.Constraint(
    #     doc="Levelized cost of lithium by mass constraint"
    # )
    # def eq_lcoli_mass(b):
    #     return b.LCOLi_mass == b.LCOLi * m.fs.pond.properties_treated[0.0].dens_mass
    
    # lcoli = value(m.fs.costing.LCOLi)

def display_costing_results(m):
    print("\n" + "="*50)
    print("COSTING RESULTS")
    print("="*50)
    try:
        if hasattr(m.fs.pond.costing, 'capital_cost'):
            print(f"Pond capital cost: ${value(m.fs.pond.costing.capital_cost):,.0f}")
        if hasattr(m.fs.pond.costing, 'fixed_operating_cost'):
            print(f"Pond fixed operating cost: ${value(m.fs.pond.costing.fixed_operating_cost):,.0f}/year")
        if hasattr(m.fs.costing, 'total_capital_cost'):
            print(f"Total capital cost: ${value(m.fs.costing.total_capital_cost):,.0f}")
        if hasattr(m.fs.costing, 'total_operating_cost'):
            print(f"Total operating cost: ${value(m.fs.costing.total_operating_cost):,.0f}/year")
    except Exception as e:
        print(f"Error displaying costing results: {e}")
    print("="*50)

if __name__ == "__main__":
    main() 