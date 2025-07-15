"""
Task: Create a simple flowsheet using the detailed EvaporationPond unit model with simple outlet variables
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

    try:
        # Try to build and solve the model again to get 'm' in scope if not already
        # If 'main' returns 'm', use it; otherwise, you may need to adjust main()
        # For now, assume 'm' is available if you run interactively
        plot_precipitation_functions(m)
    except Exception as e:
        print(f"Could not plot precipitation functions: {e}") 

def build(weather_data_path):
    m = ConcreteModel()
    m.fs = FlowsheetBlock(dynamic=False)

    props = {
        "non_volatile_solute_list": ["TDS", "Li+"],
        "mw_data": {"TDS": 31.4038218e-3, "Li+": 6.94e-3},
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

    # Set operating conditions
    set_operating_conditions(m)
    m.fs.pond.number_evaporation_ponds.fix(300)
    assert_degrees_of_freedom(m, 0)
    
    initialize_system(m)
    
    return m


def set_operating_conditions(m):
    flow_vol = 1.051 * pyunits.m**3 / pyunits.s
    fraction_outflow = 0.05
    conc_tds_inlet = 370 * pyunits.kg / pyunits.m**3
    conc_li_inlet = 1.57 * pyunits.kg / pyunits.m**3 
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
    prop_in.flow_mass_phase_comp["Liq", "Li+"].fix(flow_vol * conc_li_inlet)
    prop_in.flow_mass_phase_comp["Vap", "Air"].fix(2)
    prop_in.flow_mass_phase_comp["Vap", "H2O"].fix(0)
    
    m.fs.pond.evaporation_rate_salinity_adjustment_factor.set_value(1)
    m.fs.pond.evaporation_rate_enhancement_adjustment_factor.fix(1)

    # Add variables and expressions for the split
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
        expr=pyunits.convert(m.fs.pond.mass_flow_precipitate, to_units=pyunits.kg/pyunits.s)
    )
    m.fs.tds_outflow = pyo.Expression(
        expr=prop_in.flow_mass_phase_comp["Liq", "TDS"] - m.fs.tds_precipitated
    )
    # Add Li+ precipitation and outflow expressions for LCOLi
    m.fs.li_precipitated = pyo.Expression(
        expr=m.fs.tds_precipitated * (prop_in.flow_mass_phase_comp["Liq", "Li+"] / prop_in.flow_mass_phase_comp["Liq", "TDS"]) * 0.01 if value(prop_in.flow_mass_phase_comp["Liq", "TDS"]) > 0 else 0
    )
    m.fs.li_outflow = pyo.Expression(
        expr=prop_in.flow_mass_phase_comp["Liq", "Li+"] - m.fs.li_precipitated
    )
    
    # Handle TDS concentration calculation for zero outflow case
    m.fs.tds_concentration_outflow = pyo.Expression(
        expr=m.fs.tds_outflow / (m.fs.water_outflow + 1e-12 * pyunits.kg / pyunits.s) * rho
    )
    
    # Simple outlet variables (no state blocks needed)
    m.fs.outlet_water_flow = pyo.Var(
        initialize=value(m.fs.water_outflow),
        bounds=(0, None),
        units=pyunits.kg/pyunits.s,
        doc="Outlet water flow rate"
    )
    m.fs.outlet_tds_flow = pyo.Var(
        initialize=value(m.fs.tds_outflow),
        bounds=(0, None),
        units=pyunits.kg/pyunits.s,
        doc="Outlet TDS flow rate"
    )
    m.fs.outlet_air_flow = pyo.Var(
        initialize=2.0,
        bounds=(0, None),
        units=pyunits.kg/pyunits.s,
        doc="Outlet air flow rate"
    )
    m.fs.outlet_water_vapor_flow = pyo.Var(
        initialize=0.0,
        bounds=(0, None),
        units=pyunits.kg/pyunits.s,
        doc="Outlet water vapor flow rate"
    )
    
    # Simple mass balance constraints for outlet flows
    @m.fs.Constraint(doc="Water mass balance - outlet")
    def eq_water_mass_balance_outlet(b):
        return b.outlet_water_flow == m.fs.water_outflow
    
    @m.fs.Constraint(doc="TDS mass balance - outlet")
    def eq_tds_mass_balance_outlet(b):
        return b.outlet_tds_flow == m.fs.tds_outflow
    
    @m.fs.Constraint(doc="Air mass balance - outlet")
    def eq_air_mass_balance_outlet(b):
        return b.outlet_air_flow == prop_in.flow_mass_phase_comp["Vap", "Air"]
    
    @m.fs.Constraint(doc="Water vapor mass balance - outlet")
    def eq_water_vapor_mass_balance_outlet(b):
        return b.outlet_water_vapor_flow == prop_in.flow_mass_phase_comp["Vap", "H2O"]
    
    # Modify the pond model to only evaporate the calculated fraction
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
    
    # Li+ mass balance and reporting
    inlet_li = value(prop_in.flow_mass_phase_comp["Liq", "Li+"])
    # Assume Li+ precipitates in the same proportion as TDS
    li_precipitated = tds_precipitated * (inlet_li / inlet_tds) if inlet_tds > 0 else 0 # Assuming Li+ precipitates in the same proportion as TDS, which is not true
    li_outflow = inlet_li - li_precipitated
    print(f"Li+ inlet: {inlet_li:.4f} kg/s")
    print(f"Li+ precipitated: {li_precipitated:.4f} kg/s")
    print(f"Li+ outflow: {li_outflow:.4f} kg/s")
    if water_outflow < 1e-6:
        print("Li+ concentration in outflow: N/A (no liquid outflow)")
        print("Inlet Li+ concentration: {:.4f} kg/m³".format(value(prop_in.conc_mass_phase_comp["Liq", "Li+"])) )
    else:
        li_conc_outflow = li_outflow / water_outflow * 1227  # kg/m³, using same density as TDS
        inlet_li_conc = value(prop_in.conc_mass_phase_comp["Liq", "Li+"])
        print(f"Li+ concentration in outflow: {li_conc_outflow:.4f} kg/m³")
        print(f"Inlet Li+ concentration: {inlet_li_conc:.4f} kg/m³")
        print(f"Li+ concentration factor: {li_conc_outflow/inlet_li_conc:.2f}x")
    
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
    
    # Simple outlet stream information
    print("\n" + "-"*50)
    print("SIMPLE OUTLET STREAM INFORMATION")
    print("-"*50)
    print(f"Outlet water flow: {value(m.fs.outlet_water_flow):.2f} kg/s")
    print(f"Outlet TDS flow: {value(m.fs.outlet_tds_flow):.2f} kg/s")
    print(f"Outlet air flow: {value(m.fs.outlet_air_flow):.2f} kg/s")
    print(f"Outlet water vapor flow: {value(m.fs.outlet_water_vapor_flow):.2f} kg/s")
    
    # Calculate outlet TDS concentration
    if value(m.fs.outlet_water_flow) > 1e-6:
        outlet_tds_conc = value(m.fs.outlet_tds_flow) / value(m.fs.outlet_water_flow) * 1227  # kg/m³
        print(f"Outlet TDS concentration: {outlet_tds_conc:.0f} kg/m³")
    else:
        print("Outlet TDS concentration: N/A (no liquid outflow)")
    
    print("\n" + "="*50)
    print("SIMPLE OUTLET VARIABLES AVAILABLE")
    print("="*50)
    print("The pond now has simple outlet variables that can be used for downstream connections:")
    print("  - m.fs.outlet_water_flow")
    print("  - m.fs.outlet_tds_flow")
    print("  - m.fs.outlet_air_flow")
    print("  - m.fs.outlet_water_vapor_flow")
    print("  - m.fs.tds_concentration_outflow")
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
    # Use add_LCOW to get LCOLi in $/m³ Li outflow, then convert to $/kg
    density_concentrated_brine = 1323 * pyunits.kg / pyunits.m**3  # Li handbook pg 110
    vol_flow_li = m.fs.li_outflow / density_concentrated_brine  # m³/s
    m.fs.costing.add_LCOW(vol_flow_li, name="LCOLi") # $/m³ Li
    # # Add variable and constraint for $/kg
    # m.fs.costing.LCOLi_mass = pyo.Var(
    #     initialize=1,
    #     units=m.fs.costing.base_currency / pyunits.kg,
    #     bounds=(0, None),
    #     doc="Levelized cost of lithium by mass ($/kg)"
    # )
    # m.fs.costing.LCOLi_mass_constraint = pyo.Constraint(
    #     expr=m.fs.costing.LCOLi_mass == m.fs.costing.LCOLi * density_concentrated_brine
    # )


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
        if hasattr(m.fs.costing, 'LCOLi'):
            lcoli_vol = value(m.fs.costing.LCOLi)
            # lcoli_mass = value(m.fs.costing.LCOLi_mass)
            print(f"Levelized Cost of Lithium (LCOLi): ${lcoli_vol:.2f} per m³ Li")
            # print(f"Levelized Cost of Lithium (LCOLi): ${lcoli_mass:.2f} per kg Li")
    except Exception as e:
        print(f"Error displaying costing results: {e}")
    print("="*50)


def plot_precipitation_functions(m):
    import numpy as np
    import matplotlib.pyplot as plt
    from pyomo.environ import value

    # Get coefficients from the model
    a1 = value(m.fs.pond.solids_precipitation_rate_a1)
    a2 = value(m.fs.pond.solids_precipitation_rate_a2)
    intercept = value(m.fs.pond.solids_precipitation_rate_intercept)
    dens_solids = value(m.fs.pond.dens_solids)  # g/cm³
    area_acre = value(m.fs.pond.total_pond_area_acre)
    
    # TDS range (g/L)
    tds_range = np.linspace(0, 500, 200)  # 0 to 500 g/L
    
    # Calculate precipitation rate (ft/yr)
    precip_rate = a1 * tds_range**2 + a2 * tds_range + intercept
    
    # Calculate mass flow (kg/yr)
    # dens_solids: g/cm³ -> kg/m³ (1 g/cm³ = 1000 kg/m³)
    dens_solids_kg_m3 = dens_solids * 1000
    # 1 acre = 4046.86 m², 1 ft = 0.3048 m
    area_m2 = area_acre * 4046.86
    precip_rate_m = precip_rate * 0.3048  # ft/yr to m/yr
    mass_flow_kg_yr = area_m2 * precip_rate_m * dens_solids_kg_m3  # kg/yr
    
    # Get current model values
    current_tds_conc = value(m.fs.pond.properties_in[0].conc_mass_phase_comp['Liq', 'TDS']) 
    original_mass_flow = value(m.fs.pond.mass_flow_precipitate)  # This is the original calculation
    
    # Plot precipitation rate vs TDS
    plt.figure(figsize=(15, 10))
    
    plt.subplot(2, 2, 1)
    plt.plot(tds_range, precip_rate)
    plt.axvline(x=current_tds_conc, color='red', linestyle='--', label=f'Current TDS: {current_tds_conc:.1f} g/L')
    plt.xlabel("TDS concentration (g/L)")
    plt.ylabel("Solids precipitation rate (ft/yr)")
    plt.title("Original: Precipitation Rate vs TDS")
    plt.legend()
    plt.grid(True)
    
    # Plot mass flow vs TDS
    plt.subplot(2, 2, 2)
    plt.plot(tds_range, mass_flow_kg_yr)
    plt.axvline(x=current_tds_conc, color='red', linestyle='--', label=f'Current TDS: {current_tds_conc:.1f} g/L')
    plt.axhline(y=original_mass_flow, color='blue', linestyle=':', label=f'Original calc: {original_mass_flow:.0f} kg/yr')
    plt.xlabel("TDS concentration (g/L)")
    plt.ylabel("Mass flow of precipitate (kg/yr)")
    plt.title("Original: Mass Flow Precipitate vs TDS")
    plt.legend()
    plt.grid(True)
    
    # Current value analysis
    plt.subplot(2, 2, 3)
    # Calculate what the original would be at current TDS
    current_precip_rate = a1 * current_tds_conc**2 + a2 * current_tds_conc + intercept
    current_precip_rate_m = current_precip_rate * 0.3048  # ft/yr to m/yr
    calculated_mass_flow = area_m2 * current_precip_rate_m * dens_solids_kg_m3  # kg/yr
    
    comparison_data = ['Model\nValue', 'Calculated\nValue']
    comparison_values = [original_mass_flow, calculated_mass_flow]
    colors = ['blue', 'green']
    
    bars = plt.bar(comparison_data, comparison_values, color=colors, alpha=0.7)
    plt.ylabel("Mass flow precipitate (kg/year)")
    plt.title("Original Model: Model vs Calculated Mass Flow")
    plt.grid(True, axis='y')
    
    # Add value labels on bars
    for bar, value in zip(bars, comparison_values):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(comparison_values)*0.01, 
                f'{value:.0f}', ha='center', va='bottom', fontweight='bold')
    
    # Summary table
    plt.subplot(2, 2, 4)
    plt.axis('off')
    
    # Create summary text
    summary_text = f"""
ORIGINAL MASS FLOW PRECIPITATE ANALYSIS

Current Conditions:
• TDS concentration: {current_tds_conc:.1f} g/L
• Total pond area: {area_acre:.1f} acres
• Solids density: {dens_solids:.2f} g/cm³

Original Function Parameters:
• a1: {a1:.2e} ft/yr/(g/L)²
• a2: {a2:.2e} ft/yr/(g/L)
• intercept: {intercept:.2e} ft/yr

Results:
• Precipitation rate: {current_precip_rate:.4f} ft/yr
• Model mass_flow_precipitate: {original_mass_flow:.0f} kg/year
• Calculated mass flow: {calculated_mass_flow:.0f} kg/year
• Difference: {original_mass_flow - calculated_mass_flow:.0f} kg/year
• Ratio (Model/Calc): {original_mass_flow/calculated_mass_flow:.2f}x

Area Calculations:
• Area in m²: {area_m2:.0f} m²
• Precipitation rate in m/yr: {current_precip_rate_m:.4f} m/yr
• Solids density in kg/m³: {dens_solids_kg_m3:.0f} kg/m³
"""
    
    plt.text(0.05, 0.95, summary_text, transform=plt.gca().transAxes, 
             fontsize=9, verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.8))
    
    plt.tight_layout()
    plt.show()
    
    # Print comparison information
    print("\n" + "="*80)
    print("ORIGINAL PRECIPITATION FUNCTION ANALYSIS")
    print("="*80)
    print(f"Original function coefficients:")
    print(f"  a1 = {a1:.2e} ft/yr/(g/L)²")
    print(f"  a2 = {a2:.2e} ft/yr/(g/L)")
    print(f"  intercept = {intercept:.2e} ft/yr")
    print(f"  dens_solids = {dens_solids:.2f} g/cm³")
    print(f"  area_acre = {area_acre:.1f} acres")
    print()
    print(f"Current model values:")
    print(f"  TDS concentration = {current_tds_conc:.1f} g/L")
    print(f"  Precipitation rate = {current_precip_rate:.4f} ft/yr")
    print(f"  Model mass_flow_precipitate = {original_mass_flow:.0f} kg/year")
    print(f"  Calculated mass flow = {calculated_mass_flow:.0f} kg/year")
    print(f"  Difference = {original_mass_flow - calculated_mass_flow:.0f} kg/year")
    print(f"  Ratio (Model/Calc) = {original_mass_flow/calculated_mass_flow:.2f}x")
    print("="*80)


if __name__ == "__main__":
    main() 