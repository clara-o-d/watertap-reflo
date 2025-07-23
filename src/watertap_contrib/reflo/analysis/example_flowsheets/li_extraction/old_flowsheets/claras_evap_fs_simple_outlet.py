"""
Task: Create a simple flowsheet using the detailed EvaporationPond unit model with simple outlet variables
"""

import os
from re import A
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
from idaes.core.util import DiagnosticsToolbox
from idaes.core.util.testing import initialization_tester
from idaes.core.util.math import smooth_max, smooth_min
from idaes.core.util.model_statistics import degrees_of_freedom
import idaes.core.util.scaling as iscale

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

    print(calculate_max_feasible_li_concentration(m))
    # plot_li_concentration_percent_vs_evap(m)

    # dt = DiagnosticsToolbox(m)
    # dt.report_structural_issues()
    # dt.display_potential_evaluation_errors()

    results = solve(m)
    assert_optimal_termination(results)

    display_results(m, weather_name)
    
    # Pause after first solve to inspect results
    print("\n" + "="*50)
    print("FIRST SOLVE COMPLETED - PRESS ENTER TO CONTINUE")
    print("="*50)
    input()

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
    
    iscale.calculate_scaling_factors(m)
    initialize_system(m)
    
    # Pause after initialization to inspect model state
    print("\n" + "="*50)
    print("MODEL INITIALIZED - PRESS ENTER TO CONTINUE")
    print("="*50)
    input()
    
    return m

def define_operating_params_and_vars(m):
    # Operating parameters
    m.fs.flow_vol = pyo.Param(
        initialize=1.051,
        mutable=True,
        units=pyunits.m**3 / pyunits.s,
        doc="Inlet volumetric flow rate"
    )
    
    m.fs.conc_tds_inlet = pyo.Param(
        initialize=370,
        mutable=True,
        units=pyunits.kg / pyunits.m**3,
        doc="Inlet TDS concentration"
    )
    
    m.fs.conc_li_inlet = pyo.Param(
        initialize=0.82,
        mutable=True,
        units=pyunits.kg / pyunits.m**3,
        doc="Inlet lithium concentration"
    )
    
    m.fs.rho = pyo.Param(
        initialize=1269,
        mutable=True,
        units=pyunits.kg / pyunits.m**3,
        doc="Solution density"
    )
    
    m.fs.pressure_inlet = pyo.Param(
        initialize=101325,
        mutable=True,
        units=pyunits.Pa,
        doc="Inlet pressure"
    )
    
    m.fs.temperature_liquid_inlet = pyo.Param(
        initialize=298,
        mutable=True,
        units=pyunits.K,
        doc="Inlet liquid temperature"
    )
    
    m.fs.temperature_vapor_inlet = pyo.Param(
        initialize=293,
        mutable=True,
        units=pyunits.K,
        doc="Inlet vapor temperature"
    )
    
    m.fs.air_flow_inlet = pyo.Param(
        initialize=1,
        mutable=True,
        units=pyunits.kg / pyunits.s,
        doc="Inlet air flow rate"
    )
    
    m.fs.water_vapor_flow_inlet = pyo.Param(
        initialize=0,
        mutable=True,
        units=pyunits.kg / pyunits.s,
        doc="Inlet water vapor flow rate"
    )
    
    m.fs.evaporation_rate_salinity_adjustment_factor = pyo.Param(
        initialize=1,
        mutable=True,
        units=pyunits.dimensionless,
        doc="Evaporation rate salinity adjustment factor"
    )
    
    m.fs.evaporation_rate_enhancement_adjustment_factor = pyo.Param(
        initialize=1,
        mutable=True,
        units=pyunits.dimensionless,
        doc="Evaporation rate enhancement adjustment factor"
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

    m.fs.target_li_concentration = pyo.Param(
        initialize=3.500,
        mutable=True,
        units=pyunits.kg / pyunits.m**3,
        doc="Target Li+ concentration in outflow"
    )
    
    # Operating variables
    m.fs.fraction_outflow = pyo.Var(
        initialize=0.05,
        bounds=(0.01, 0.99),
        units=pyunits.dimensionless,
        doc="Fraction of water that flows out (not evaporated)"
    )

    m.fs.fraction_evaporated = pyo.Var(
        initialize=0.95,
        bounds=(0.01, 1.0),
        units=pyunits.dimensionless,
        doc="Fraction of water that is evaporated"
    )
    
    m.fs.water_outflow = pyo.Var(
        initialize=0.05,
        bounds=(0, None),
        units=pyunits.kg / pyunits.s,
        doc="Water flow rate in the outflow stream"
    )
    
    # m.fs.tds_outflow = pyo.Var(
    #     initialize=0.5,
    #     bounds=(0, None),
    #     units=pyunits.kg / pyunits.s,
    #     doc="TDS flow rate in the outflow stream"
    # )

    # Remove the original mass_flow_precipitate Expression and replace it with a variable
    if hasattr(m.fs.pond, 'mass_flow_precipitate'):
        m.fs.pond.del_component('mass_flow_precipitate')
    
    m.fs.pond.mass_flow_precipitate = pyo.Var(
        initialize=1000,
        bounds=(0, None),
        units=pyunits.kg / pyunits.year,
        doc="Annual mass flow of precipitate"
    )
    
    # m.fs.tds_concentration_outflow = pyo.Var(
    #     initialize=1000,
    #     bounds=(0, None),
    #     units=pyunits.kg / pyunits.m**3,
    #     doc="TDS concentration in the outflow stream"
    # )
    
    # m.fs.li_outflow = pyo.Var(
    #     initialize=0.001,
    #     bounds=(0, None),
    #     units=pyunits.kg / pyunits.s,
    #     doc="Lithium flow rate in the outflow stream"
    # )

    m.fs.li_concentration_outflow = pyo.Var(
        initialize=3.500,
        bounds=(0, None),
        units=pyunits.kg / pyunits.m**3,
        doc="Lithium concentration in the outflow stream"
    )

def set_operating_conditions(m):
    # Define all parameters and variables first
    define_operating_params_and_vars(m)

    prop_in = m.fs.pond.properties_in[0]
    prop_in.pressure.fix(value(m.fs.pressure_inlet))
    prop_in.temperature["Liq"].fix(value(m.fs.temperature_liquid_inlet))
    prop_in.temperature["Vap"].fix(value(m.fs.temperature_vapor_inlet))
    prop_in.flow_mass_phase_comp["Liq", "H2O"].fix(value(m.fs.flow_vol * m.fs.rho))
    prop_in.flow_mass_phase_comp["Liq", "TDS"].fix(value(m.fs.flow_vol * m.fs.conc_tds_inlet))
    prop_in.flow_mass_phase_comp["Liq", "Li+"].fix(value(m.fs.flow_vol * m.fs.conc_li_inlet))
    prop_in.flow_mass_phase_comp["Vap", "Air"].fix(value(m.fs.air_flow_inlet))
    prop_in.flow_mass_phase_comp["Vap", "H2O"].fix(value(m.fs.water_vapor_flow_inlet))
    
    m.fs.pond.evaporation_rate_salinity_adjustment_factor.set_value(value(m.fs.evaporation_rate_salinity_adjustment_factor))
    m.fs.pond.evaporation_rate_enhancement_adjustment_factor.fix(value(m.fs.evaporation_rate_enhancement_adjustment_factor))

    m.fs.fraction_evaporated.fix(0.95)

    @m.fs.Constraint(doc="Fraction of outflow water")
    def eq_fraction_outflow(b):
        return (
            b.fraction_outflow + b.fraction_evaporated == 1
    )
    
    # Calculate evaporated and outflow water
    m.fs.water_evaporated = pyo.Expression(
        expr=prop_in.flow_mass_phase_comp["Liq", "H2O"] * m.fs.fraction_evaporated
    )

    # TDS precipitated as an Expression
    m.fs.tds_precipitated = pyo.Expression(
        expr=pyunits.convert(m.fs.pond.mass_flow_precipitate, to_units=pyunits.kg/pyunits.s)
    )

    @m.fs.Constraint(doc="Water outflow mass balance")
    def eq_water_outflow(b):
        return b.water_outflow == prop_in.flow_mass_phase_comp["Liq", "H2O"] * (1 - b.fraction_evaporated)

    @m.fs.pond.Constraint(doc="Annual mass flow of precipitate from concentration and water volume")
    def eq_mass_flow_precipitate(b):
        # precipitate concentration = a * (1-evaporation_ratio) + b
        precipitate_concentration = m.fs.pond.annual_solid_precipitate_a * (1 - m.fs.fraction_evaporated) + m.fs.pond.annual_solid_precipitate_b
        # original water volume = water mass flow / density
        original_water_volume = prop_in.flow_mass_phase_comp["Liq", "H2O"] / m.fs.rho
        # annual mass flow = concentration * volume * time conversion
        annual_mass_flow = pyunits.convert(precipitate_concentration * original_water_volume, to_units=pyunits.kg/pyunits.year)
        return b.mass_flow_precipitate == annual_mass_flow

    # @m.fs.Constraint(doc="TDS outflow mass balance")
    # def eq_tds_outflow(b):
    #     return b.tds_outflow == prop_in.flow_mass_phase_comp["Liq", "TDS"] - b.tds_precipitated

    # @m.fs.Constraint(doc="TDS concentration in outflow")
    # def eq_tds_concentration_outflow(b):
    #     return b.tds_concentration_outflow == b.tds_outflow / (b.water_outflow + 1e-12 * pyunits.kg / pyunits.s) * b.rho

    # Li+ outflow and concentration constraint (all logic here, no li_precipitated var)
    @m.fs.Constraint(doc="Li+ outflow and concentration using polynomial mass fraction")
    def eq_li_concentration_outflow(b):
        evap_ratio = b.fraction_evaporated
        a = 88.1606
        b_ = -169.2358
        c = 81.4783
        mass_frac_before = 1.0
        mass_frac_after = a * evap_ratio**2 + b_ * evap_ratio + c
        mass_frac = smooth_min(mass_frac_after, mass_frac_before, eps=1e-3)
        li_in = prop_in.flow_mass_phase_comp["Liq", "Li+"]
        li_out = li_in * mass_frac
        return b.li_concentration_outflow == li_out / (b.water_outflow + 1e-12 * pyunits.kg / pyunits.s) * b.rho

    # Li+ precipitated as an Expression
    def li_precipitated_expr():
        evap_ratio = m.fs.fraction_evaporated
        a = 88.1606
        b_ = -169.2358
        c = 81.4783
        mass_frac_before = 1.0
        mass_frac_after = a * evap_ratio**2 + b_ * evap_ratio + c
        from idaes.core.util.math import smooth_min
        mass_frac = smooth_min(mass_frac_after, mass_frac_before, eps=1e-3)
        li_in = prop_in.flow_mass_phase_comp["Liq", "Li+"]
        li_out = li_in * mass_frac
        return li_in - li_out
    m.fs.li_precipitated = pyo.Expression(expr=li_precipitated_expr())
    
    @m.fs.Constraint(doc="Evaporation fraction from final li concentration")
    def eq_evaporation_fraction(b):
        return b.li_concentration_outflow == m.fs.target_li_concentration
    
    # Modify the pond model to only evaporate the calculated fraction
    if hasattr(m.fs.pond, 'eq_total_evaporative_area_required'):
        m.fs.pond.eq_total_evaporative_area_required.deactivate()
    
    # @m.fs.pond.Constraint(doc="Total evaporative area required for partial evaporation")
    # def eq_total_evaporative_area_required_partial(b):
    #     return (
    #         b.total_evaporative_area_required * b.mass_flux_water_vapor_average
    #         == m.fs.water_evaporated
    #     )

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
    print(f"Li+ outflow concentration: {value(m.fs.li_concentration_outflow):.2f} kg/m³")

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
    m.fs.density_concentrated_brine = pyo.Param(
        initialize=1323,
        mutable=True,
        units=pyunits.kg / pyunits.m**3,
        doc="Density of concentrated brine for Li+ volume calculation"
    )
    vol_flow_li = m.fs.li_outflow / m.fs.density_concentrated_brine  # m³/s
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
    original_water_volume_m3_s = value(m.fs.pond.properties_in[0].flow_mass_phase_comp['Liq', 'H2O']) / value(m.fs.rho)  # m³/s
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

def calculate_max_feasible_li_concentration(m):
    """
    Calculate the maximum feasible Li+ concentration in the outflow based on the polynomial fit
    and the bounds on the evaporation ratio.
    """
    print("\n=== MAX FEASIBLE LI+ CONCENTRATION ANALYSIS ===")
    prop_in = m.fs.pond.properties_in[0]
    li_inlet_flow = value(prop_in.flow_mass_phase_comp["Liq", "Li+"])
    water_inlet_flow = value(prop_in.flow_mass_phase_comp["Liq", "H2O"])
    rho_val = value(m.fs.rho)  # kg/m3
    # Polynomial coefficients from fit
    a = 88.1606  
    b_ = -169.2358  
    c = 81.4783
    # Test across evaporation fraction range
    evap_fractions = np.linspace(0.01, 0.99, 50)
    concentrations = []
    print(f"{'Evap Fraction':<15} {'Li+ Mass Fraction':<18} {'Li+ Outflow (kg/s)':<18} {'Li+ Conc (kg/m³)':<15}")
    print("-" * 70)
    for evap_frac in evap_fractions:
        # Calculate Li+ mass fraction using polynomial, clipped to [0, 1]
        li_mass_frac = max(0, min(a * evap_frac**2 + b_ * evap_frac + c, 1))
        li_outflow = li_inlet_flow * li_mass_frac
        water_outflow = water_inlet_flow * (1 - evap_frac)
        li_conc = li_outflow / (water_outflow + 1e-12) * rho_val if water_outflow > 1e-12 else 0
        concentrations.append(li_conc)
        print(f"{evap_frac:<15.2f} {li_mass_frac:<18.4f} {li_outflow:<18.6f} {li_conc:<15.4f}")
    max_conc = max(concentrations)
    min_conc = min(concentrations)
    print(f"\nAchievable Li+ concentration range: {min_conc:.4f} to {max_conc:.4f} kg/m³")
    print("=== END LI+ CONCENTRATION ANALYSIS ===\n")
    return min_conc, max_conc

def plot_li_concentration_percent_vs_evap(m):
    """
    Plot Li+ concentration as percent (w/w) in the outlet brine vs evaporation fraction.
    """
    import matplotlib.pyplot as plt
    import numpy as np
    prop_in = m.fs.pond.properties_in[0]
    li_inlet_flow = value(prop_in.flow_mass_phase_comp["Liq", "Li+"])
    water_inlet_flow = value(prop_in.flow_mass_phase_comp["Liq", "H2O"])
    rho_val = 1227  # kg/m3
    # Polynomial coefficients from fit
    a2 = 88.1606
    a1 = -169.2358
    a0 = 81.4783
    evap_fractions = np.linspace(0.01, 0.99, 100)
    li_percent = []
    for evap_frac in evap_fractions:
        li_mass_frac = max(0, min(a2 * evap_frac**2 + a1 * evap_frac + a0, 1))
        li_outflow = li_inlet_flow * li_mass_frac
        water_outflow = water_inlet_flow * (1 - evap_frac)
        li_conc = li_outflow / (water_outflow + 1e-12) * rho_val if water_outflow > 1e-12 else 0
        # Convert to mass percent: Li+ mass / (Li+ mass + H2O mass) * 100
        # Assume outlet is just Li+ and H2O (ignore other solutes for this plot)
        total_mass = li_outflow + water_outflow
        percent = (li_outflow / total_mass) * 100 if total_mass > 0 else 0
        li_percent.append(percent)
    plt.figure(figsize=(7,5))
    plt.plot(evap_fractions, li_percent, label="Li+ mass % in outlet brine")
    plt.xlabel("Evaporation Fraction")
    plt.ylabel("Li+ Concentration in Outlet Brine (% w/w)")
    plt.title("Li+ Mass Percent vs Evaporation Fraction")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("li_percent_vs_evap.png", dpi=200)
    plt.show()
    print("Plot saved as 'li_percent_vs_evap.png'")


if __name__ == "__main__":
    main() 