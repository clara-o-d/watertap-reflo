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

# Import weather utilities
from weather_utils import (
    preprocess_station34_weather_data,
    preprocess_openmeteo_weather_data,
    preprocess_weather_data,
    plot_evaporation_and_weather_data,
    print_weather_statistics,
    compare_weather_datasets,
    create_comparison_plots,
    run_all_datasets_and_compare,
    test_plotting_functionality
)


def main():
    # Choose weather data source
    print("Available weather data sources:")
    print("1. Station 34 (10-minute intervals, converted to hourly)")
    print("2. Open-Meteo (hourly data, Chile location)")
    print("3. Test data (original evaporation pond test data)")
    print("4. Run all datasets and compare")
    
    choice = input("Enter your choice (1, 2, 3, or 4): ").strip()
    this_dir = os.path.dirname(os.path.abspath(__file__))
    
    if choice == "4":
        # Run all datasets and compare
        run_all_datasets_and_compare(this_dir)
        return
    
    # Single dataset processing
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
    
    print(f"\nUsing weather data: {weather_name}")
    
    # Check if this is the first time processing this dataset (BEFORE preprocessing)
    first_time_processing = False
    if choice in ["1", "2"]:
        if not os.path.exists(processed_weather_file):
            first_time_processing = True
            print(f"First time processing {weather_name} data - will run weather analysis.")
        else:
            print(f"Using existing processed weather file - skipping weather analysis.")
    
    # Preprocess the weather data if needed
    if choice in ["1", "2"]:
        if not os.path.exists(processed_weather_file):
            preprocess_weather_data(raw_weather_file, processed_weather_file, data_type)
        else:
            print(f"Using existing processed weather file: {processed_weather_file}")
    
    m = build(processed_weather_file)
    
    results = solve(m)
    assert_optimal_termination(results)
    
    display_results(m, weather_name)
    
    # Add plotting and statistics functionality only for first-time processing
    if first_time_processing:
        print_weather_statistics(m, weather_name)
        plot_evaporation_and_weather_data(m, weather_name, save_plots=True)
    else:
        print("\nSkipping weather analysis (dataset already processed).")

    # Add costing and solve again
    print("\n" + "="*50)
    print("ADDING COSTING")
    print("="*50)
    
    add_costing(m)
    assert_degrees_of_freedom(m, 0)
    # Patch: Ensure area and flows used in costing are strictly positive
    min_area = 1.0  # m², or whatever is a reasonable minimum
    min_ponds = 1
    
    # Debug: Print current values before fixing
    print(f"DEBUG: Current evaporation_pond_area: {value(m.fs.pond.evaporation_pond_area):.2f} m²")
    print(f"DEBUG: Current number_evaporation_ponds: {value(m.fs.pond.number_evaporation_ponds):.0f}")
    # print(f"DEBUG: Current water_evaporated: {value(m.fs.water_evaporated):.2f} kg/s")
    
    if value(m.fs.pond.evaporation_pond_area) < min_area:
        print(f"DEBUG: Fixing evaporation_pond_area to minimum {min_area} m²")
        m.fs.pond.evaporation_pond_area.fix(min_area)
    if value(m.fs.pond.number_evaporation_ponds) < min_ponds:
        print(f"DEBUG: Fixing number_evaporation_ponds to minimum {min_ponds}")
        m.fs.pond.number_evaporation_ponds.fix(min_ponds)
    
    # # Patch the area constraint for partial evaporation
    # if hasattr(m.fs.pond, "eq_total_evaporative_area_required"):
    #     m.fs.pond.eq_total_evaporative_area_required.deactivate()
    
    # # Remove the existing constraint if it exists to avoid replacement warning
    # if hasattr(m.fs.pond, "eq_total_evaporative_area_required_partial"):
    #     m.fs.pond.del_component("eq_total_evaporative_area_required_partial")

    # @ m.fs.pond.Constraint(doc="Total evaporative area required for partial evaporation")
    # def eq_total_evaporative_area_required_partial(b):
    #     return (
    #         b.total_evaporative_area_required * b.mass_flux_water_vapor_average
    #         == m.fs.water_evaporated
    #     )
    
    # Re-initialize the model after adding costing
    print("Initializing costing...")
    initialize_costing(m)
    process_costing(m)
    assert_degrees_of_freedom(m, 0)
    # Check degrees of freedom after costing
    dof_after_costing = degrees_of_freedom(m)
    print(f"Degrees of freedom after costing: {dof_after_costing}")
    
    if dof_after_costing != 0:
        print("WARNING: Model has non-zero degrees of freedom after costing!")
        print("This may cause issues with the solver.")
    
    # Solve with costing
    print("Solving with costing...")
    results = solve(m)
    assert_degrees_of_freedom(m, 0)
    if results.solver.termination_condition == pyo.TerminationCondition.optimal:
        print("SUCCESS: Model solved optimally with costing!")
        display_costing_results(m)
    else:
        print(f"WARNING: Solver terminated with condition: {results.solver.termination_condition}")
        print("Costing results may not be accurate.")
        # Still try to display results even if not optimal
        try:
            display_costing_results(m)
        except Exception as e:
            print(f"Could not display costing results: {e}")


def build(weather_data_path):
    m = ConcreteModel()
    m.fs = FlowsheetBlock(dynamic=False)

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

    set_operating_conditions(m)
    m.fs.pond.number_evaporation_ponds.fix(300)
    assert_degrees_of_freedom(m, 0)
    
    initialize_system(m)
    
    return m


def set_operating_conditions(m):
    flow_vol = 1.051 * pyunits.m**3 / pyunits.s
    fraction_outflow = 0
    conc_tds_inlet = 370 * pyunits.kg / pyunits.m**3
    rho = 1227 * pyunits.kg / pyunits.m**3
    
    # Calculate fraction evaporated
    fraction_evaporated_val = 1 - fraction_outflow
    print(f"Fraction of water evaporated: {fraction_evaporated_val:.3f}")
    print(f"Fraction of water as outflow: {fraction_outflow:.3f}")
    m.fs.fraction_outflow = pyo.Param(initialize=fraction_outflow, mutable=True)

    
    prop_in = m.fs.pond.properties_in[0]
    prop_in.pressure.fix(101325)
    prop_in.temperature["Liq"].fix(298)
    prop_in.temperature["Vap"].fix(293)
    prop_in.flow_mass_phase_comp["Liq", "H2O"].fix(flow_vol * rho)
    prop_in.flow_mass_phase_comp["Liq", "TDS"].fix(flow_vol * conc_tds_inlet)
    prop_in.flow_mass_phase_comp["Vap", "Air"].fix(2) # try changing
    prop_in.flow_mass_phase_comp["Vap", "H2O"].fix(0)
    
    m.fs.pond.evaporation_rate_salinity_adjustment_factor.set_value(1) # 0.75
    m.fs.pond.evaporation_rate_enhancement_adjustment_factor.fix(1) # 1.08


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
    return solver.solve(m, tee=True)


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