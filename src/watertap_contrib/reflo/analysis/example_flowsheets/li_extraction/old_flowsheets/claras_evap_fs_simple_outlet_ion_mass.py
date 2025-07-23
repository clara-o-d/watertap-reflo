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
    TerminationCondition,
)
from idaes.core import FlowsheetBlock
from idaes.core.util.testing import initialization_tester
from idaes.core.util.model_statistics import degrees_of_freedom
from idaes.core.util import DiagnosticsToolbox
from watertap_contrib.reflo.property_models import (
    AirWaterEq,
    DensityCalculation,
)
from watertap_contrib.reflo.unit_models import EvaporationPond
from watertap.core.solvers import get_solver
from watertap.core.util.initialization import assert_degrees_of_freedom

# Add scaling import
import idaes.core.util.scaling as iscale

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
    
    # Analyze achievable Li+ concentration range before solving
    calculate_achievable_li_concentration_range(m)

    # dt = DiagnosticsToolbox(m)
    # dt.report_structural_issues()
    # dt.display_underconstrained_set()
    results = solve(m)
    
    display_results(m, weather_name)

    # Add a pause so user can review results before proceeding to costing
    input("\nPress Enter to continue to costing...")

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
    
    # Set lower bound for fixed_operating_cost if it exists
    if hasattr(m.fs.pond, 'costing') and hasattr(m.fs.pond.costing, 'fixed_operating_cost'):
        m.fs.pond.costing.fixed_operating_cost.setlb(0)
        print("Set lower bound for pond.costing.fixed_operating_cost to 0.")

    # Print and assert degrees of freedom after costing
    dof_after_costing = degrees_of_freedom(m)
    print(f"Degrees of freedom after costing (assert): {dof_after_costing}")
    if dof_after_costing != 0:
        raise RuntimeError(f"Model has {dof_after_costing} degrees of freedom after costing. The model should be square (dof=0) before solving.")
    
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

    try:
        plot_precipitation_functions(m)
    except Exception as e:
        print(f"Could not plot precipitation functions: {e}") 

def build(weather_data_path):
    m = ConcreteModel()
    m.fs = FlowsheetBlock(dynamic=False)

    props = {
        "non_volatile_solute_list": ["TDS", "Li+", "Na+", "K+", "Mg+2", "Ca+2", "Cl-", "SO4-2", "B(OH)3", "HCO3-"],
        "mw_data": {
            "TDS": 31.4038218e-3, 
            "Li+": 6.94e-3,
            "Na+": 22.99e-3,
            "K+": 39.10e-3,
            "Mg+2": 24.31e-3,
            "Ca+2": 40.08e-3,
            "Cl-": 35.45e-3,
            "SO4-2": 96.06e-3,
            "B(OH)3": 61.83e-3,
            "HCO3-": 61.02e-3,
        },
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
    # assert_degrees_of_freedom(m, 0)
    
    #iscale.calculate_scaling_factors(m)
    initialize_system(m)
    
    # Add a pause after initialization so user can review results
    input("\nPress Enter to continue to solve...")
    
    return m

def set_operating_conditions(m):
    flow_vol = 1.051 * pyunits.m**3 / pyunits.s
    fraction_outflow = 0.05
    rho = 1227 * pyunits.kg / pyunits.m**3
    
    # Initial concentrations from precipitation_analysis.py (g/kg water)
    initial_concentrations_g_per_kg = {
        'Li+': 0.65,
        'Na+': 82.1,
        'K+': 12.3,
        'Mg+2': 13.1,
        'Ca+2': 2.6,
        'Cl-': 171.2,
        'SO4-2': 16.6, 
        'B(OH)3': 3.5,   
        'HCO3-': 0.22,
    }
    
    # Convert g/kg to kg/m³ (multiply by density)
    initial_concentrations_kg_per_m3 = {}
    for ion, conc_g_kg in initial_concentrations_g_per_kg.items():
        initial_concentrations_kg_per_m3[ion] = conc_g_kg * 1e-3 * rho  # g/kg * 1e-3 kg/g * kg/m³
    
    # Calculate total TDS concentration
    conc_tds_inlet = sum(initial_concentrations_kg_per_m3.values())
    conc_li_inlet = initial_concentrations_kg_per_m3['Li+']
    
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
    
    # Set inlet flow rates for all ions
    for ion, conc_kg_m3 in initial_concentrations_kg_per_m3.items():
        prop_in.flow_mass_phase_comp["Liq", ion].fix(flow_vol * conc_kg_m3)
    
    prop_in.flow_mass_phase_comp["Vap", "Air"].fix(1)
    prop_in.flow_mass_phase_comp["Vap", "H2O"].fix(0)
    
    m.fs.pond.evaporation_rate_salinity_adjustment_factor.set_value(1)
    m.fs.pond.evaporation_rate_enhancement_adjustment_factor.fix(1)

    # Add variables and expressions for the split
    m.fs.fraction_evaporated = pyo.Var(
        initialize=fraction_evaporated_val, bounds=(0.01, 0.99), units=pyunits.dimensionless
    ) # make dimensionless
    # m.fs.fraction_evaporated.fix(fraction_evaporated_val)
    
    # Calculate evaporated and outflow water
    m.fs.water_evaporated = pyo.Expression(
        expr=prop_in.flow_mass_phase_comp["Liq", "H2O"] * m.fs.fraction_evaporated
    )
    m.fs.water_outflow = pyo.Expression(
        expr=prop_in.flow_mass_phase_comp["Liq", "H2O"] * (1 - m.fs.fraction_evaporated)
    )
    # Overwrite mass_flow_precipitate with annual_solid_precipitate
    # precipitate concentration [kg/m³] = a * (V_remaining/V_original) + b [kg/m³]
    m.fs.pond.annual_solid_precipitate_a = pyo.Param(
        initialize=-3.1473e02, mutable=True, doc="Linear fit coefficient a [kg/m³]",
        units=pyunits.kg/pyunits.m**3
    )
    m.fs.pond.annual_solid_precipitate_b = pyo.Param(
        initialize=3.5704e02, mutable=True, doc="Linear fit intercept b [kg/m³]",
        units=pyunits.kg/pyunits.m**3
    )
    
    # precipitate concentration = a * (1-evaporation_ratio) + b
    precipitate_concentration = m.fs.pond.annual_solid_precipitate_a * (1 - m.fs.fraction_evaporated) + m.fs.pond.annual_solid_precipitate_b  # kg/m³
    
    # Convert precipitate concentration to annual mass flow rate
    original_water_volume = prop_in.flow_mass_phase_comp["Liq", "H2O"] / rho  # m³/s
    annual_mass_flow_precipitate = pyunits.convert(
        precipitate_concentration * original_water_volume, 
        to_units=pyunits.kg/pyunits.year
    )
    

    
    # Remove the original mass_flow_precipitate Expression and replace it with the new one
    if hasattr(m.fs.pond, 'mass_flow_precipitate'):
        m.fs.pond.del_component('mass_flow_precipitate')
    m.fs.pond.mass_flow_precipitate = pyo.Expression(
        expr=annual_mass_flow_precipitate,
        doc="Annual mass flow of precipitate (kg/year) from precipitate concentration per original water volume"
    )
    
    # Calculate TDS in outflow (accounting for precipitation)
    m.fs.tds_precipitated = pyo.Expression(
        expr=pyunits.convert(m.fs.pond.mass_flow_precipitate, to_units=pyunits.kg/pyunits.s)
    )
    m.fs.tds_outflow = pyo.Expression(
        expr=prop_in.flow_mass_phase_comp["Liq", "TDS"] - m.fs.tds_precipitated
    )
    
    # Handle TDS concentration calculation for zero outflow case
    m.fs.tds_concentration_outflow = pyo.Expression(
        expr=m.fs.tds_outflow / (m.fs.water_outflow + 1e-12 * pyunits.kg / pyunits.s) * rho,
        doc="TDS concentration in outflow (kg/m³)"
    )
    
    # Add ion tracking based on mass fraction analysis results
    # Define the fitted equations for each ion from mass_fraction_analysis.py
    # Note: Li+ changed from threshold to sigmoid for solver compatibility
    ion_equations = {
        'Na+': {'model': 'sigmoid', 'params': [-0.1072, 1.1024, 4.1251, 0.3065]},  # y_min, y_max, k, x0
        'K+': {'model': 'sigmoid', 'params': [-0.0756, 1.0045, 16.2259, 0.7940]},
        'Ca+2': {'model': 'sigmoid', 'params': [-0.0104, 0.1867, 5.3639, 0.2419]},
        'Cl-': {'model': 'exponential', 'params': [7.8761, -0.1093, -6.9872]},  # a, b, c
        'Li+': {'model': 'sigmoid', 'params': [0.3271, 1.0001, 120.1276, 0.8920]},  # y_min, y_max, k, x0
        'B(OH)3': {'model': 'sigmoid', 'params': [0.1643, 1.0043, 16.9895, 0.8168]},
        'Mg+2': {'model': 'sigmoid', 'params': [-0.2910, 1.0008, 23.5737, 0.9462]},
    }

    ion_list = list(ion_equations.keys())
    m.fs.ion_mass_fraction_remaining = pyo.Var(
        ion_list, bounds=(0.01, 1.0), initialize=0.5, units=pyunits.dimensionless
    )
    m.fs.ion_outflow = pyo.Var(
        ion_list, bounds=(-10.0, 1000.0), initialize=10.0, units=pyunits.kg/pyunits.s 
    )
    m.fs.ion_precipitated = pyo.Var(
        ion_list, bounds=(-10.0, 1000.0), initialize=10.0, units=pyunits.kg/pyunits.s
    )
    m.fs.ion_concentration_outflow = pyo.Var(
        ion_list, bounds=(-10.0, 10000.0), initialize=10.0, units=pyunits.kg/pyunits.m**3  
    )

    def mass_fraction_rule(b, ion):
        eq_info = ion_equations[ion]
        if eq_info['model'] == 'sigmoid':
            y_min, y_max, k, x0 = eq_info['params']
            return b.ion_mass_fraction_remaining[ion] == y_min + (y_max - y_min) / (1 + pyo.exp(k * (b.fraction_evaporated - x0)))
        elif eq_info['model'] == 'exponential':
            a, b_, c = eq_info['params']
            return b.ion_mass_fraction_remaining[ion] == a * pyo.exp(b_ * b.fraction_evaporated) + c
    m.fs.ion_mass_fraction_remaining_constraint = pyo.Constraint(ion_list, rule=mass_fraction_rule)

    def outflow_rule(b, ion):
        return b.ion_outflow[ion] == prop_in.flow_mass_phase_comp["Liq", ion] * b.ion_mass_fraction_remaining[ion]
    m.fs.ion_outflow_constraint = pyo.Constraint(ion_list, rule=outflow_rule)

    def precipitated_rule(b, ion):
        return b.ion_precipitated[ion] == prop_in.flow_mass_phase_comp["Liq", ion] - b.ion_outflow[ion]
    m.fs.ion_precipitated_constraint = pyo.Constraint(ion_list, rule=precipitated_rule)

    def concentration_rule(b, ion):
        return b.ion_concentration_outflow[ion] == b.ion_outflow[ion] / (b.water_outflow + 1e-12) * 1227
    m.fs.ion_concentration_outflow_constraint = pyo.Constraint(ion_list, rule=concentration_rule)

    # Add constraint to calculate evaporation fraction from final li concentration
    m.fs.target_li_concentration = pyo.Param(
        initialize=0.005 * 1227,  # 6.135 kg/m³
        mutable=True,
        units=pyunits.kg / pyunits.m**3,
        doc="Target Li+ concentration in outflow"
    )
    
    # Constraint: Li+ concentration in outflow should equal target concentration (using Var)
    @m.fs.Constraint(doc="Li+ concentration constraint (Var version)")
    def eq_li_concentration_target(b):
        return b.ion_concentration_outflow['Li+'] == m.fs.target_li_concentration
    
    # Alternative: Constraint to achieve a specific Li+ recovery factor
    # target_li_recovery = 0.8  # 80% Li+ recovery
    # @m.fs.Constraint(doc="Li+ recovery constraint")
    # def eq_li_recovery_target(b):
    #     return m.fs.ion_outflow['Li+'] == target_li_recovery * prop_in.flow_mass_phase_comp["Liq", "Li+"]
    
    # Alternative: Constraint to achieve a specific evaporation fraction
    # target_evaporation_fraction = 0.95  # 95% evaporation
    # @m.fs.Constraint(doc="Evaporation fraction constraint")
    # def eq_evaporation_fraction_target(b):
    #     return m.fs.fraction_evaporated == target_evaporation_fraction
    
    # # Simple outlet variables (no state blocks needed)
    # m.fs.outlet_water_flow = pyo.Var(
    #     initialize=value(m.fs.water_outflow),
    #     bounds=(0, None),
    #     units=pyunits.kg/pyunits.s,
    #     doc="Outlet water flow rate"
    # )
    # m.fs.outlet_tds_flow = pyo.Var(
    #     initialize=value(m.fs.tds_outflow),
    #     bounds=(0, None),
    #     units=pyunits.kg/pyunits.s,
    #     doc="Outlet TDS flow rate"
    # )
    # m.fs.outlet_air_flow = pyo.Var(
    #     initialize=2.0,
    #     bounds=(0, None),
    #     units=pyunits.kg/pyunits.s,
    #     doc="Outlet air flow rate"
    # )
    # m.fs.outlet_water_vapor_flow = pyo.Var(
    #     initialize=0.0,
    #     bounds=(0, None),
    #     units=pyunits.kg/pyunits.s,
    #     doc="Outlet water vapor flow rate"
    # )
    
    # # Simple mass balance constraints for outlet flows
    # @m.fs.Constraint(doc="Water mass balance - outlet")
    # def eq_water_mass_balance_outlet(b):
    #     return b.outlet_water_flow == m.fs.water_outflow
    
    # @m.fs.Constraint(doc="TDS mass balance - outlet")
    # def eq_tds_mass_balance_outlet(b):
    #     return b.outlet_tds_flow == m.fs.tds_outflow
    
    # @m.fs.Constraint(doc="Air mass balance - outlet")
    # def eq_air_mass_balance_outlet(b):
    #     return b.outlet_air_flow == prop_in.flow_mass_phase_comp["Vap", "Air"]
    
    # @m.fs.Constraint(doc="Water vapor mass balance - outlet")
    # def eq_water_vapor_mass_balance_outlet(b):
    #     return b.outlet_water_vapor_flow == prop_in.flow_mass_phase_comp["Vap", "H2O"]
    
    # Modify the pond model to only evaporate the calculated fraction
    if hasattr(m.fs.pond, 'eq_total_evaporative_area_required'):
        m.fs.pond.eq_total_evaporative_area_required.deactivate()
    
    @m.fs.pond.Constraint(doc="Total evaporative area required for partial evaporation")
    def eq_total_evaporative_area_required_partial(b):
        return (
            b.total_evaporative_area_required * b.mass_flux_water_vapor_average
            == m.fs.water_evaporated
        )





    # --- Set bounds for evaporation pond variables from within flowsheet ---
    # Salar de Atacama scale bounds (much higher than default)
    m.fs.pond.total_evaporative_area_required.setlb(1000)  # 1,000 m² minimum
    m.fs.pond.total_evaporative_area_required.setub(100000000)  # 100 km² maximum
    
    m.fs.pond.evaporative_area_per_pond.setlb(100)  # 100 m² minimum per pond
    m.fs.pond.evaporative_area_per_pond.setub(100000000)  # 100 km² maximum per pond
    
    m.fs.pond.evaporation_pond_area.setlb(100)  # 100 m² minimum
    m.fs.pond.evaporation_pond_area.setub(100000000)  # 100 km² maximum
    
    m.fs.pond.number_evaporation_ponds.setlb(1)  # At least 1 pond
    m.fs.pond.number_evaporation_ponds.setub(10000)  # Up to 10,000 ponds
    
    # Tighter bounds for numerical stability
    m.fs.pond.area_correction_factor.setlb(0.5)  # Much tighter than original (0.99, 10)
    m.fs.pond.area_correction_factor.setub(5.0)
    
    m.fs.pond.solids_precipitation_rate.setlb(1e-4)  # Much tighter than original (0, None)
    m.fs.pond.solids_precipitation_rate.setub(1.0)
    
    m.fs.pond.mass_flux_water_vapor.setlb(1e-8)  # Tighter than original (1e-12, 1e-3)
    m.fs.pond.mass_flux_water_vapor.setub(1e-4)
    
    m.fs.pond.net_radiation.setlb(0.1)  # Tighter than original (0, None)
    m.fs.pond.net_radiation.setub(50)


def initialize_system(m):
    print(f"Degrees of freedom before initialization: {degrees_of_freedom(m)}")
    
    try:
        m.fs.pond.initialize()
        print("Initialization successful!")
    except Exception as e:
        print(f"Standard initialization failed: {e}")
        print("Trying with relaxed constraints...")
        
        # Try to relax eq_net_radiation constraint which can cause circular dependencies
        original_constraint_states = {}
        pond_constraints_to_relax = ['eq_net_radiation']
        
        for constraint_name in pond_constraints_to_relax:
            if hasattr(m.fs.pond, constraint_name):
                constraint = getattr(m.fs.pond, constraint_name)
                if hasattr(constraint, 'deactivate'):
                    original_constraint_states[f'pond.{constraint_name}'] = constraint.active
                    constraint.deactivate()
        
        try:
            m.fs.pond.initialize()
            print("Initialization successful with relaxed constraints!")
            
            # Reactivate constraints
            for constraint_name in pond_constraints_to_relax:
                if hasattr(m.fs.pond, constraint_name):
                    constraint = getattr(m.fs.pond, constraint_name)
                    if hasattr(constraint, 'activate') and f'pond.{constraint_name}' in original_constraint_states:
                        if original_constraint_states[f'pond.{constraint_name}']:
                            constraint.activate()
        except Exception as e:
            print(f"Relaxed constraint initialization also failed: {e}")
            raise e

def solve(m, solver=None):
    if solver is None:
        solver = get_solver()
    
    print(f"Degrees of freedom: {degrees_of_freedom(m)}")
    print(f"Using solver: {solver.name}")
    
    try:
        results = solver.solve(m, tee=True)
        return results
    except Exception as e:
        print(f"Solver failed: {e}")
        raise e

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
    li_precipitated = tds_precipitated * (inlet_li / (inlet_tds + 1e-12)) if inlet_tds > 1e-12 else 0 # Assuming Li+ precipitates in the same proportion as TDS, which is not true
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
    
    # Display ion tracking results
    print("\n" + "-"*50)
    print("ION TRACKING RESULTS")
    print("-"*50)
    print(f"{'Ion':<8} {'Inlet (kg/s)':<12} {'Outflow (kg/s)':<14} {'Precipitated (kg/s)':<18} {'Mass Fraction':<12} {'Conc Out (kg/m³)':<15}")
    print("-" * 85)
    
    # Calculate ion tracking results manually to avoid expression evaluation issues
    for ion in ['Li+', 'Na+', 'K+', 'Ca+2', 'Mg+2', 'Cl-', 'B(OH)3']:
        if ion in m.fs.ion_outflow:
            inlet_flow = value(prop_in.flow_mass_phase_comp["Liq", ion])
            
            # Calculate mass fraction remaining based on fitted equations
            fraction_evap = value(m.fs.fraction_evaporated)
            
            if ion == 'Na+':
                y_min, y_max, k, x0 = -0.1072, 1.1024, 4.1251, 0.3065
                mass_fraction = y_min + (y_max - y_min) / (1 + np.exp(k * (fraction_evap - x0)))
            elif ion == 'K+':
                y_min, y_max, k, x0 = -0.0756, 1.0045, 16.2259, 0.7940
                mass_fraction = y_min + (y_max - y_min) / (1 + np.exp(k * (fraction_evap - x0)))
            elif ion == 'Ca+2':
                y_min, y_max, k, x0 = -0.0104, 0.1867, 5.3639, 0.2419
                mass_fraction = y_min + (y_max - y_min) / (1 + np.exp(k * (fraction_evap - x0)))
            elif ion == 'Cl-':
                a, b, c = 7.8761, -0.1093, -6.9872
                mass_fraction = a * np.exp(b * fraction_evap) + c
            elif ion == 'Li+':
                y_min, y_max, k, x0 = 0.3271, 1.0001, 120.1276, 0.8920
                mass_fraction = y_min + (y_max - y_min) / (1 + np.exp(k * (fraction_evap - x0)))
            elif ion == 'B(OH)3':
                y_min, y_max, k, x0 = 0.1643, 1.0043, 16.9895, 0.8168
                mass_fraction = y_min + (y_max - y_min) / (1 + np.exp(k * (fraction_evap - x0)))
            elif ion == 'Mg+2':
                y_min, y_max, k, x0 = -0.2910, 1.0008, 23.5737, 0.9462
                mass_fraction = y_min + (y_max - y_min) / (1 + np.exp(k * (fraction_evap - x0)))
            
            outflow_flow = inlet_flow * mass_fraction
            precipitated_flow = inlet_flow - outflow_flow
            conc_out = outflow_flow / (water_outflow + 1e-12) * 1227 if water_outflow > 1e-12 else 0
            
            print(f"{ion:<8} {inlet_flow:<12.4f} {outflow_flow:<14.4f} {precipitated_flow:<18.4f} {mass_fraction:<12.3f} {conc_out:<15.1f}")
    
    # Calculate total ion mass balance
    total_inlet_ions = sum(value(prop_in.flow_mass_phase_comp["Liq", ion]) for ion in ['Li+', 'Na+', 'K+', 'Ca+2', 'Mg+2', 'Cl-', 'B(OH)3'])
    total_outflow_ions = 0
    total_precipitated_ions = 0
    
    for ion in ['Li+', 'Na+', 'K+', 'Ca+2', 'Mg+2', 'Cl-', 'B(OH)3']:
        inlet_flow = value(prop_in.flow_mass_phase_comp["Liq", ion])
        fraction_evap = value(m.fs.fraction_evaporated)
        
        # Calculate mass fraction for each ion
        if ion == 'Na+':
            y_min, y_max, k, x0 = -0.1072, 1.1024, 4.1251, 0.3065
            mass_fraction = y_min + (y_max - y_min) / (1 + np.exp(k * (fraction_evap - x0)))
        elif ion == 'K+':
            y_min, y_max, k, x0 = -0.0756, 1.0045, 16.2259, 0.7940
            mass_fraction = y_min + (y_max - y_min) / (1 + np.exp(k * (fraction_evap - x0)))
        elif ion == 'Ca+2':
            y_min, y_max, k, x0 = -0.0104, 0.1867, 5.3639, 0.2419
            mass_fraction = y_min + (y_max - y_min) / (1 + np.exp(k * (fraction_evap - x0)))
        elif ion == 'Cl-':
            a, b, c = 7.8761, -0.1093, -6.9872
            mass_fraction = a * np.exp(b * fraction_evap) + c
        elif ion == 'Li+':
            y_min, y_max, k, x0 = 0.3271, 1.0001, 120.1276, 0.8920
            mass_fraction = y_min + (y_max - y_min) / (1 + np.exp(k * (fraction_evap - x0)))
        elif ion == 'B(OH)3':
            y_min, y_max, k, x0 = 0.1643, 1.0043, 16.9895, 0.8168
            mass_fraction = y_min + (y_max - y_min) / (1 + np.exp(k * (fraction_evap - x0)))
        elif ion == 'Mg+2':
            y_min, y_max, k, x0 = -0.2910, 1.0008, 23.5737, 0.9462
            mass_fraction = y_min + (y_max - y_min) / (1 + np.exp(k * (fraction_evap - x0)))
        
        outflow_flow = inlet_flow * mass_fraction
        precipitated_flow = inlet_flow - outflow_flow
        
        total_outflow_ions += outflow_flow
        total_precipitated_ions += precipitated_flow
    
    print("-" * 85)
    print(f"{'TOTAL':<8} {total_inlet_ions:<12.4f} {total_outflow_ions:<14.4f} {total_precipitated_ions:<18.4f}")
    print(f"Ion mass balance check: {total_inlet_ions - total_outflow_ions - total_precipitated_ions:.6f} kg/s")
    
    # # Simple outlet stream information
    # print("\n" + "-"*50)
    # print("SIMPLE OUTLET STREAM INFORMATION")
    # print("-"*50)
    # print(f"Outlet water flow: {value(m.fs.outlet_water_flow):.2f} kg/s")
    # print(f"Outlet TDS flow: {value(m.fs.outlet_tds_flow):.2f} kg/s")
    # print(f"Outlet air flow: {value(m.fs.outlet_air_flow):.2f} kg/s")
    # print(f"Outlet water vapor flow: {value(m.fs.outlet_water_vapor_flow):.2f} kg/s")
    
    # # Calculate outlet TDS concentration
    # if value(m.fs.outlet_water_flow) > 1e-6:
    #     outlet_tds_conc = value(m.fs.outlet_tds_flow) / value(m.fs.outlet_water_flow) * 1227  # kg/m³
    #     print(f"Outlet TDS concentration: {outlet_tds_conc:.0f} kg/m³")
    # else:
    #     print("Outlet TDS concentration: N/A (no liquid outflow)")
    
    # print("\n" + "="*50)
    # print("SIMPLE OUTLET VARIABLES AVAILABLE")
    # print("="*50)
    # print("The pond now has simple outlet variables that can be used for downstream connections:")
    # print("  - m.fs.outlet_water_flow")
    # print("  - m.fs.outlet_tds_flow")
    # print("  - m.fs.outlet_air_flow")
    # print("  - m.fs.outlet_water_vapor_flow")
    # print("  - m.fs.tds_concentration_outflow")
    # print("="*50)

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
    # True Li+ volumetric flow (m³/s): mass flow / concentration
    vol_flow_li = m.fs.ion_outflow['Li+'] / m.fs.ion_concentration_outflow['Li+']
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
    
    # Get new precipitate concentration coefficients
    concentration_a = value(m.fs.pond.annual_solid_precipitate_a)
    concentration_b = value(m.fs.pond.annual_solid_precipitate_b)
    
    # TDS range (g/L)
    tds_range = np.linspace(0, 500, 200)  # 0 to 500 g/L
    
    # Calculate precipitation rate (ft/yr) - original function
    precip_rate = a1 * tds_range**2 + a2 * tds_range + intercept
    
    # Calculate mass flow (kg/yr) - original function
    # dens_solids: g/cm³ -> kg/m³ (1 g/cm³ = 1000 kg/m³)
    dens_solids_kg_m3 = dens_solids * 1000
    # 1 acre = 4046.86 m², 1 ft = 0.3048 m
    area_m2 = area_acre * 4046.86
    precip_rate_m = precip_rate * 0.3048  # ft/yr to m/yr
    mass_flow_kg_yr = area_m2 * precip_rate_m * dens_solids_kg_m3  # kg/yr
    
    # Calculate new precipitate concentration (kg/m³) - new function
    # Evaporation ratio range (dimensionless)
    evaporation_ratio_range = np.linspace(0, 1, 200)  # 0 to 1 (0% to 100% evaporation)
    precipitate_concentration = concentration_a * (1-evaporation_ratio_range) + concentration_b  # kg/m³
    
    # Convert precipitate concentration to annual mass flow rate
    # Use the same original water volume as in the model
    original_water_volume_m3_s = value(m.fs.pond.properties_in[0].flow_mass_phase_comp['Liq', 'H2O']) / 1227  # m³/s
    annual_mass_flow_precipitate = precipitate_concentration * original_water_volume_m3_s * 3600 * 24 * 365  # kg/year
    
    # Get current model values for comparison
    current_tds_conc = value(m.fs.pond.properties_in[0].conc_mass_phase_comp['Liq', 'TDS'])
    current_evap_ratio = value(m.fs.water_evaporated / m.fs.pond.properties_in[0].flow_mass_phase_comp['Liq', 'H2O'])
    original_mass_flow = value(m.fs.pond.mass_flow_precipitate)  # This is the new custom calculation
    
    # Get the original pond's mass_flow_precipitate before w# We need to calculate what the original would have been
    original_precip_rate = a1 * current_tds_conc**2 + a2 * current_tds_conc + intercept
    original_precip_rate_m = original_precip_rate * 0.3048  # ft/yr to m/yr
    original_mass_flow_calc = area_m2 * original_precip_rate_m * dens_solids_kg_m3  # kg/yr

    # Plot precipitation rate vs TDS
    plt.figure(figsize=(15, 8))
    
    plt.subplot(2, 3, 1)
    plt.plot(tds_range, precip_rate)
    plt.axvline(x=current_tds_conc, color='red', linestyle='--', label=f'Current TDS: {current_tds_conc:.1f} g/L')
    plt.xlabel("TDS concentration (g/L)")
    plt.ylabel("Solids precipitation rate (ft/yr)")
    plt.title("Original: Precipitation Rate vs TDS")
    plt.legend()
    plt.grid(True)
    
    # Plot mass flow vs TDS - original function
    plt.subplot(2, 3, 2)
    plt.plot(tds_range, mass_flow_kg_yr)
    plt.axvline(x=current_tds_conc, color='red', linestyle='--', label=f'Current TDS: {current_tds_conc:.1f} g/L')
    plt.axhline(y=original_mass_flow_calc, color='green', linestyle=':', label=f'New calc: {original_mass_flow_calc:.0f} kg/yr')
    plt.xlabel("TDS concentration (g/L)")
    plt.ylabel("Mass flow of precipitate (kg/yr)")
    plt.title("Original: Mass Flow Precipitate vs TDS")
    plt.legend()
    plt.grid(True)
    
    # Plot new precipitate concentration vs evaporation ratio
    plt.subplot(2, 3, 3)
    plt.plot(evaporation_ratio_range * 100, precipitate_concentration)  # Convert to percentage
    plt.axvline(x=current_evap_ratio * 100, color='red', linestyle='--', label=f'Current evaporated: {current_evap_ratio*100:.1f}%')
    plt.xlabel("Evaporation ratio (%)")
    plt.ylabel("Precipitate concentration (kg/m³)")
    plt.title("New: Precipitate Concentration vs Evaporation Ratio")
    plt.legend()
    plt.grid(True)
    
    # Plot new annual mass flow vs evaporation ratio
    plt.subplot(2, 3, 4)
    plt.plot(evaporation_ratio_range * 100, annual_mass_flow_precipitate)  # Convert to percentage
    plt.axvline(x=current_evap_ratio * 100, color='red', linestyle='--', label=f'Current evaporated: {current_evap_ratio*100:.1f}%')
    plt.axhline(y=original_mass_flow, color='green', linestyle=':', label=f'New calc: {original_mass_flow:.0f} kg/year')
    plt.xlabel("Evaporation ratio (%)")
    plt.ylabel("Annual mass flow precipitate (kg/year)")
    plt.title("New: Annual Mass Flow vs Evaporation Ratio")
    plt.legend()
    plt.grid(True)
    
    # Comparison plot: Original vs New mass flow
    plt.subplot(2, 3, 5)
    
    comparison_data = ['Original\nCalculation', 'New\nCalculation']
    comparison_values = [original_mass_flow_calc, original_mass_flow]
    colors = ['blue', 'green']
    
    bars = plt.bar(comparison_data, comparison_values, color=colors, alpha=0.7)
    plt.ylabel("Mass flow precipitate (kg/year)")
    plt.title("Comparison: Original vs New Mass Flow")
    plt.grid(True, axis='y')
    
    # Add value labels on bars
    for bar, value in zip(bars, comparison_values):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(comparison_values)*0.01, 
                f'{value:.0f}', ha='center', va='bottom', fontweight='bold')
    
    # Summary table
    plt.subplot(2, 3, 6)
    plt.axis('off')
    
    # Create summary text
    summary_text = f"""
MASS FLOW PRECIPITATE COMPARISON

Current Conditions:
• TDS concentration: {current_tds_conc:.1f} g/L
• Evaporation ratio: {current_evap_ratio*100:.1f}%
• Original water volume: {original_water_volume_m3_s:.3f} m³/s

Results:
• Original calculation: {original_mass_flow_calc:.0f} kg/year
• New calculation: {original_mass_flow:.0f} kg/year
• Difference: {original_mass_flow - original_mass_flow_calc:.0f} kg/year
• Ratio (New/Original): {original_mass_flow/original_mass_flow_calc:.2f}x

New Function Parameters:
• concentration_a: {concentration_a:.3e} kg/m³
• concentration_b: {concentration_b:.3e} kg/m³
• Precipitate concentration: {concentration_a * current_evap_ratio + concentration_b:.3f} kg/m³
"""
    
    plt.text(0.05, 0.95, summary_text, transform=plt.gca().transAxes, 
             fontsize=10, verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.8))
    
    plt.tight_layout()
    plt.show()
    
    # Print comparison information
    print("\n" + "="*80)
    print("PRECIPITATION FUNCTION COMPARISON")
    print("="*80)
    print(f"Original function coefficients:")
    print(f"  a1 = {a1:.2e} ft/yr/(g/L)²")
    print(f"  a2 = {a2:.2e} ft/yr/(g/L)")
    print(f"  intercept = {intercept:.2e} ft/yr")
    print(f"  dens_solids = {dens_solids:.2f} g/cm³")
    print(f"  area_acre = {area_acre:.1f} acres")
    print()
    print(f"New precipitate concentration function coefficients:")
    print(f"  concentration_a = {concentration_a:.2e} kg/m³")
    print(f"  concentration_b = {concentration_b:.2e} kg/m³")
    print()
    print(f"Current model values:")
    print(f"  TDS concentration = {current_tds_conc:.1f} g/L")
    print(f"  Evaporation ratio = {current_evap_ratio:.3f}")
    print(f"  Original water volume = {original_water_volume_m3_s:.3f} m³/s")
    print(f"  Original mass_flow_precipitate = {original_mass_flow_calc:.0f} kg/year")
    print(f"  New mass_flow_precipitate = {original_mass_flow:.0f} kg/year")
    print(f"  Difference = {original_mass_flow - original_mass_flow_calc:.0f} kg/year")
    print(f"  Ratio (New/Original) = {original_mass_flow/original_mass_flow_calc:.2f}x")
    print("="*80)

def calculate_achievable_li_concentration_range(m):
    """
    Calculate the achievable Li+ concentration range based on evaporation fraction bounds.
    This helps users set realistic target concentrations.
    """
    print("\n=== LI+ CONCENTRATION ANALYSIS ===")
    
    prop_in = m.fs.pond.properties_in[0]
    li_inlet_flow = value(prop_in.flow_mass_phase_comp["Liq", "Li+"])
    water_inlet_flow = value(prop_in.flow_mass_phase_comp["Liq", "H2O"])
    rho_val = 1227  # kg/m3
    
    # Li+ fitted sigmoid parameters
    y_min, y_max, k, x0 = 0.3271, 1.0001, 120.1276, 0.8920
    
    print(f"Li+ inlet flow: {li_inlet_flow:.6f} kg/s")
    print(f"Water inlet flow: {water_inlet_flow:.3f} kg/s")
    print(f"Li+ inlet concentration: {li_inlet_flow/water_inlet_flow*rho_val:.4f} kg/m³")
    
    # Test across evaporation fraction range
    evap_fractions = [0.01, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]
    concentrations = []
    
    print(f"\n{'Evap Fraction':<15} {'Li+ Mass Fraction':<18} {'Li+ Outflow (kg/s)':<18} {'Li+ Conc (kg/m³)':<15}")
    print("-" * 70)
    
    for evap_frac in evap_fractions:
        # Calculate Li+ mass fraction using sigmoid
        li_mass_frac = y_min + (y_max - y_min) / (1 + np.exp(k * (evap_frac - x0)))
        
        # Calculate Li+ outflow
        li_outflow = li_inlet_flow * li_mass_frac
        
        # Calculate water outflow
        water_outflow = water_inlet_flow * (1 - evap_frac)
        
        # Calculate Li+ concentration
        li_conc = li_outflow / (water_outflow + 1e-12) * rho_val if water_outflow > 1e-12 else 0
        concentrations.append(li_conc)
        
        print(f"{evap_frac:<15.2f} {li_mass_frac:<18.4f} {li_outflow:<18.6f} {li_conc:<15.4f}")
    
    min_conc = min(concentrations)
    max_conc = max(concentrations)
    
    print(f"\nAchievable Li+ concentration range: {min_conc:.4f} to {max_conc:.4f} kg/m³")
    print(f"Current target: {value(m.fs.target_li_concentration):.4f} kg/m³")
    
    if value(m.fs.target_li_concentration) > max_conc:
        print("⚠ WARNING: Target concentration is above maximum achievable!")
        print("   Consider reducing the target concentration.")
    elif value(m.fs.target_li_concentration) < min_conc:
        print("⚠ WARNING: Target concentration is below minimum achievable!")
        print("   Consider increasing the target concentration.")
    else:
        print("✓ Target concentration is within achievable range.")
    
    print("=== END LI+ CONCENTRATION ANALYSIS ===\n")
    
    return min_conc, max_conc


if __name__ == "__main__":
    main()