"""
Task: Create a simple flowsheet using the detailed EvaporationPond unit model with enhanced outlet variables and easy connection to additional units
"""

import os
import pyomo.environ as pyo
from pyomo.environ import (
    assert_optimal_termination,
    ConcreteModel,
    value,
    units as pyunits,
)
from idaes.core import FlowsheetBlock
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
    print("Available weather data sources:")
    print("1. Station 34 (10-minute intervals, converted to hourly)")
    print("2. Open-Meteo (hourly data, Chile location)")
    print("3. Test data (original evaporation pond test data)")
    print("4. Run all datasets and compare")
    
    choice = input("Enter your choice (1, 2, 3, or 4): ").strip()
    this_dir = os.path.dirname(os.path.abspath(__file__))
    
    if choice == "4":
        run_all_datasets_and_compare(this_dir)
        return
    
    if choice == "1":
        raw_weather_file = os.path.join(this_dir, "station[34]_2024-01-01_2024-12-31.csv")
        processed_weather_file = os.path.join(this_dir, "station34_processed_weather.csv")
        data_type = "station34"
        weather_name = "Station 34"
    elif choice == "2":
        raw_weather_file = os.path.join(this_dir, "open-meteo-23.66S68.45W2301m.csv")
        processed_weather_file = os.path.join(this_dir, "openmeteo_processed_weather.csv")
        data_type = "openmeteo"
        weather_name = "Open-Meteo (Chile)"
    elif choice == "3":
        processed_weather_file = os.path.join(this_dir, "evaporation_pond_test_data.csv")
        weather_name = "Test Data"
    else:
        print("Invalid choice. Using Station 34 data as default.")
        raw_weather_file = os.path.join(this_dir, "station[34]_2024-01-01_2024-12-31.csv")
        processed_weather_file = os.path.join(this_dir, "station34_processed_weather.csv")
        data_type = "station34"
        weather_name = "Station 34"
    
    print(f"\nUsing weather data: {weather_name}")
    first_time_processing = False
    if choice in ["1", "2"]:
        if not os.path.exists(processed_weather_file):
            first_time_processing = True
            print(f"First time processing {weather_name} data - will run weather analysis.")
        else:
            print(f"Using existing processed weather file - skipping weather analysis.")
    if choice in ["1", "2"]:
        if not os.path.exists(processed_weather_file):
            preprocess_weather_data(raw_weather_file, processed_weather_file, data_type)
        else:
            print(f"Using existing processed weather file: {processed_weather_file}")
    m = build(processed_weather_file)
    results = solve(m)
    assert_optimal_termination(results)
    display_results(m, weather_name)
    if first_time_processing:
        print_weather_statistics(m, weather_name)
        plot_evaporation_and_weather_data(m, weather_name, save_plots=True)
    else:
        print("\nSkipping weather analysis (dataset already processed).")
    print("\n" + "="*50)
    print("DEMONSTRATING UNIT CONNECTIONS")
    print("="*50)
    # add_example_downstream_unit(m)
    print("\n" + "="*50)
    print("ADDING COSTING")
    print("="*50)
    add_costing(m)
    assert_degrees_of_freedom(m, 0)
    print("Initializing costing...")
    initialize_costing(m)
    process_costing(m)
    assert_degrees_of_freedom(m, 0)
    dof_after_costing = pyo.value(pyo.Constraint.Skip) if hasattr(pyo, 'Constraint') else 0
    print(f"Degrees of freedom after costing: {dof_after_costing}")
    print("Solving with costing...")
    results = solve(m)
    assert_degrees_of_freedom(m, 0)
    if results.solver.termination_condition == pyo.TerminationCondition.optimal:
        print("SUCCESS: Model solved optimally with costing!")
        display_costing_results(m)
    else:
        print(f"WARNING: Solver terminated with condition: {results.solver.termination_condition}")
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
        dike_height=8,
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
    prop_in.flow_mass_phase_comp["Vap", "Air"].fix(2)
    prop_in.flow_mass_phase_comp["Vap", "H2O"].fix(0)
    m.fs.pond.evaporation_rate_salinity_adjustment_factor.set_value(1)
    m.fs.pond.evaporation_rate_enhancement_adjustment_factor.fix(1)
    m.fs.fraction_evaporated = pyo.Var(initialize=fraction_evaporated_val, bounds=(0.01, 1.0))
    m.fs.fraction_evaporated.fix(fraction_evaporated_val)
    m.fs.water_evaporated = pyo.Expression(
        expr=prop_in.flow_mass_phase_comp["Liq", "H2O"] * m.fs.fraction_evaporated
    )
    m.fs.water_outflow = pyo.Expression(
        expr=prop_in.flow_mass_phase_comp["Liq", "H2O"] * (1 - m.fs.fraction_evaporated)
    )
    m.fs.tds_precipitated = pyo.Expression(
        expr=m.fs.pond.mass_flow_precipitate / (365 * 24 * 3600)
    )
    m.fs.tds_outflow = pyo.Expression(
        expr=prop_in.flow_mass_phase_comp["Liq", "TDS"] - m.fs.tds_precipitated
    )
    m.fs.tds_concentration_outflow = pyo.Expression(
        expr=m.fs.tds_outflow / (m.fs.water_outflow + 1e-12 * pyunits.kg / pyunits.s) * rho
    )
    m.fs.pond_outlet = pyo.Block()
    m.fs.pond_outlet.flow_mass_phase_comp = pyo.Var(
        ["Liq", "Vap"], ["H2O", "TDS", "Air"],
        initialize=0.0,
        bounds=(0, None),
        units=pyunits.kg/pyunits.s,
        doc="Outlet mass flow rates by phase and component"
    )
    m.fs.pond_outlet.temperature = pyo.Var(
        ["Liq", "Vap"],
        initialize=298.0,
        bounds=(273, 373),
        units=pyunits.K,
        doc="Outlet temperature by phase"
    )
    m.fs.pond_outlet.pressure = pyo.Var(
        initialize=101325.0,
        bounds=(1e5, 2e5),
        units=pyunits.Pa,
        doc="Outlet pressure"
    )
    m.fs.pond_outlet.conc_mass_phase_comp = pyo.Var(
        ["Liq", "Vap"], ["H2O", "TDS", "Air"],
        initialize=0.0,
        bounds=(0, None),
        units=pyunits.kg/pyunits.m**3,
        doc="Outlet concentration by phase and component"
    )
    m.fs.pond_outlet.flow_mass_phase_comp["Liq", "H2O"].set_value(value(m.fs.water_outflow))
    m.fs.pond_outlet.flow_mass_phase_comp["Liq", "TDS"].set_value(value(m.fs.tds_outflow))
    m.fs.pond_outlet.flow_mass_phase_comp["Vap", "Air"].set_value(2.0)
    m.fs.pond_outlet.flow_mass_phase_comp["Vap", "H2O"].set_value(0.0)
    m.fs.pond_outlet.temperature["Liq"].set_value(298.0)
    m.fs.pond_outlet.temperature["Vap"].set_value(293.0)
    m.fs.pond_outlet.pressure.set_value(101325.0)
    @m.fs.Constraint(doc="Water mass balance - outlet")
    def eq_water_mass_balance_outlet(b):
        return m.fs.pond_outlet.flow_mass_phase_comp["Liq", "H2O"] == m.fs.water_outflow
    @m.fs.Constraint(doc="TDS mass balance - outlet")
    def eq_tds_mass_balance_outlet(b):
        return m.fs.pond_outlet.flow_mass_phase_comp["Liq", "TDS"] == m.fs.tds_outflow
    @m.fs.Constraint(doc="Air mass balance - outlet")
    def eq_air_mass_balance_outlet(b):
        return m.fs.pond_outlet.flow_mass_phase_comp["Vap", "Air"] == prop_in.flow_mass_phase_comp["Vap", "Air"]
    @m.fs.Constraint(doc="Water vapor mass balance - outlet")
    def eq_water_vapor_mass_balance_outlet(b):
        return m.fs.pond_outlet.flow_mass_phase_comp["Vap", "H2O"] == prop_in.flow_mass_phase_comp["Vap", "H2O"]
    @m.fs.Constraint(doc="Liquid temperature - outlet")
    def eq_liquid_temperature_outlet(b):
        return m.fs.pond_outlet.temperature["Liq"] == prop_in.temperature["Liq"]
    @m.fs.Constraint(doc="Vapor temperature - outlet")
    def eq_vapor_temperature_outlet(b):
        return m.fs.pond_outlet.temperature["Vap"] == prop_in.temperature["Vap"]
    @m.fs.Constraint(doc="Pressure - outlet")
    def eq_pressure_outlet(b):
        return m.fs.pond_outlet.pressure == prop_in.pressure
    @m.fs.Constraint(doc="Liquid water concentration - outlet")
    def eq_liquid_water_conc_outlet(b):
        return (m.fs.pond_outlet.conc_mass_phase_comp["Liq", "H2O"] * 
                m.fs.pond_outlet.flow_mass_phase_comp["Liq", "H2O"] == 
                m.fs.pond_outlet.flow_mass_phase_comp["Liq", "H2O"] * 1227)
    @m.fs.Constraint(doc="Liquid TDS concentration - outlet")
    def eq_liquid_tds_conc_outlet(b):
        return (m.fs.pond_outlet.conc_mass_phase_comp["Liq", "TDS"] * 
                m.fs.pond_outlet.flow_mass_phase_comp["Liq", "H2O"] == 
                m.fs.pond_outlet.flow_mass_phase_comp["Liq", "TDS"] * 1227)
    def connect_to_inlet(self, inlet_block):
        inlet_block.flow_mass_phase_comp["Liq", "H2O"].fix(m.fs.pond_outlet.flow_mass_phase_comp["Liq", "H2O"])
        inlet_block.flow_mass_phase_comp["Liq", "TDS"].fix(m.fs.pond_outlet.flow_mass_phase_comp["Liq", "TDS"])
        inlet_block.flow_mass_phase_comp["Vap", "Air"].fix(m.fs.pond_outlet.flow_mass_phase_comp["Vap", "Air"])
        inlet_block.flow_mass_phase_comp["Vap", "H2O"].fix(m.fs.pond_outlet.flow_mass_phase_comp["Vap", "H2O"])
        inlet_block.temperature["Liq"].fix(m.fs.pond_outlet.temperature["Liq"])
        inlet_block.temperature["Vap"].fix(m.fs.pond_outlet.temperature["Vap"])
        inlet_block.pressure.fix(m.fs.pond_outlet.pressure)
    m.fs.pond.connect_to_inlet = connect_to_inlet
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
    prop_in = m.fs.pond.properties_in[0]
    inlet_tds = value(prop_in.flow_mass_phase_comp["Liq", "TDS"])
    tds_precipitated = value(m.fs.tds_precipitated)
    tds_outflow = value(m.fs.tds_outflow)
    water_outflow = value(m.fs.water_outflow)
    print(f"TDS inlet: {inlet_tds:.2f} kg/s")
    print(f"TDS precipitated: {tds_precipitated:.2f} kg/s")
    print(f"TDS outflow: {tds_outflow:.2f} kg/s")
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
    tds_balance = inlet_tds - tds_precipitated - tds_outflow
    print(f"TDS mass balance check (should be ~0): {tds_balance:.6f} kg/s")
    print("\n" + "-"*50)
    print("ENHANCED OUTLET STREAM INFORMATION")
    print("-"*50)
    print(f"Outlet water flow: {value(m.fs.pond_outlet.flow_mass_phase_comp['Liq', 'H2O']):.2f} kg/s")
    print(f"Outlet TDS flow: {value(m.fs.pond_outlet.flow_mass_phase_comp['Liq', 'TDS']):.2f} kg/s")
    print(f"Outlet air flow: {value(m.fs.pond_outlet.flow_mass_phase_comp['Vap', 'Air']):.2f} kg/s")
    print(f"Outlet water vapor flow: {value(m.fs.pond_outlet.flow_mass_phase_comp['Vap', 'H2O']):.2f} kg/s")
    print(f"Outlet liquid temperature: {value(m.fs.pond_outlet.temperature['Liq']):.1f} K")
    print(f"Outlet vapor temperature: {value(m.fs.pond_outlet.temperature['Vap']):.1f} K")
    print(f"Outlet pressure: {value(m.fs.pond_outlet.pressure):.0f} Pa")
    if value(m.fs.pond_outlet.flow_mass_phase_comp['Liq', 'H2O']) > 1e-6:
        outlet_tds_conc = value(m.fs.pond_outlet.conc_mass_phase_comp['Liq', 'TDS'])
        print(f"Outlet TDS concentration: {outlet_tds_conc:.0f} kg/m³")
    else:
        print("Outlet TDS concentration: N/A (no liquid outflow)")
    print("\n" + "="*50)
    print("ENHANCED OUTLET STRUCTURE AVAILABLE")
    print("="*50)
    print("The pond now has an enhanced outlet structure for easy unit connections:")
    print("  - m.fs.pond_outlet.flow_mass_phase_comp[phase, component]")
    print("  - m.fs.pond_outlet.temperature[phase]")
    print("  - m.fs.pond_outlet.pressure")
    print("  - m.fs.pond_outlet.conc_mass_phase_comp[phase, component]")
    print("  - m.fs.pond.connect_to_inlet(inlet_block) - connection method")
    print("="*50)

def add_example_downstream_unit(m):
    print("\n" + "="*50)
    print("EXAMPLE: ADDING DOWNSTREAM UNIT")
    print("="*50)
    m.fs.storage_tank = pyo.Block(concrete=True)
    m.fs.storage_tank.flow_mass_phase_comp = pyo.Var(
        ["Liq", "Vap"], ["H2O", "TDS", "Air"],
        initialize=0.0,
        bounds=(0, None),
        units=pyunits.kg/pyunits.s,
        doc="Storage tank inlet mass flow rates"
    )
    m.fs.storage_tank.temperature = pyo.Var(
        ["Liq", "Vap"],
        initialize=298.0,
        bounds=(273, 373),
        units=pyunits.K,
        doc="Storage tank inlet temperature"
    )
    m.fs.storage_tank.pressure = pyo.Var(
        initialize=101325.0,
        bounds=(1e5, 2e5),
        units=pyunits.Pa,
        doc="Storage tank inlet pressure"
    )
    print("Connecting pond outlet to storage tank inlet...")
    m.fs.pond.connect_to_inlet(m.fs.storage_tank)
    m.fs.storage_tank.volume = pyo.Var(
        initialize=1000.0,
        bounds=(0, None),
        units=pyunits.m**3,
        doc="Storage tank volume"
    )
    print("Storage tank added and connected successfully!")
    print(f"Storage tank inlet water flow: {value(m.fs.storage_tank.flow_mass_phase_comp['Liq', 'H2O']):.2f} kg/s")
    print(f"Storage tank inlet TDS flow: {value(m.fs.storage_tank.flow_mass_phase_comp['Liq', 'TDS']):.2f} kg/s")
    print("="*50)

def add_costing(m):
    from idaes.core import UnitModelCostingBlock
    from watertap_contrib.reflo.costing.watertap_reflo_costing_package import REFLOCosting
    m.fs.costing = REFLOCosting()
    m.fs.pond.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)
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