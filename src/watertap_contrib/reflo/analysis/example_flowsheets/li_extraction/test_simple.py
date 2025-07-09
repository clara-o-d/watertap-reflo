#!/usr/bin/env python3
"""
Simple test script for the evaporation pond without costing
"""

import os
import sys
import pyomo.environ as pyo
from pyomo.environ import (
    assert_optimal_termination,
    ConcreteModel,
    value,
    units as pyunits,
)
from idaes.core import FlowsheetBlock
from idaes.core.util.model_statistics import degrees_of_freedom
from watertap_contrib.reflo.property_models import (
    AirWaterEq,
    DensityCalculation,
)
from watertap_contrib.reflo.unit_models import EvaporationPond
from watertap.core.solvers import get_solver
from watertap.core.util.initialization import assert_degrees_of_freedom

def test_evaporation_pond_basic():
    """Test basic evaporation pond functionality without costing"""
    print("Testing basic evaporation pond functionality...")
    
    # Get the test weather data path
    this_dir = os.path.dirname(os.path.abspath(__file__))
    weather_file = os.path.join(this_dir, "evaporation_pond_test_data.csv")
    
    if not os.path.exists(weather_file):
        print(f"Error: Weather file not found: {weather_file}")
        return False
    
    try:
        # Build the model
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
            weather_data_path=weather_file,
            weather_data_column_dict=weather_data_column_dict,
            dike_height=8,
            add_enhancement=True,
        )
        
        # Set operating conditions
        flow_vol = 1.051 * pyunits.m**3 / pyunits.s
        conc_tds = 70 * pyunits.kg / pyunits.m**3
        rho = 1000 * pyunits.kg / pyunits.m**3
        prop_in = m.fs.pond.properties_in[0]
        prop_in.pressure.fix(101325)
        prop_in.temperature["Liq"].fix(298)
        prop_in.temperature["Vap"].fix(293)
        prop_in.flow_mass_phase_comp["Liq", "H2O"].fix(flow_vol * rho)
        prop_in.flow_mass_phase_comp["Liq", "TDS"].fix(flow_vol * conc_tds)
        prop_in.flow_mass_phase_comp["Vap", "Air"].fix(1)
        prop_in.flow_mass_phase_comp["Vap", "H2O"].fix(0)
        
        m.fs.pond.evaporation_rate_salinity_adjustment_factor.set_value(0.75)
        m.fs.pond.evaporation_rate_enhancement_adjustment_factor.fix(1.08)
        m.fs.pond.number_evaporation_ponds.fix(300)
        
        # Check degrees of freedom
        dof = degrees_of_freedom(m)
        print(f"Degrees of freedom: {dof}")
        assert_degrees_of_freedom(m, 0)
        
        # Initialize
        print("Initializing model...")
        m.fs.pond.initialize()
        
        # Solve
        print("Solving model...")
        solver = get_solver()
        results = solver.solve(m, tee=True)  # Enable tee to see solver output
        
        print(f"Solver termination condition: {results.solver.termination_condition}")
        print(f"Solver status: {results.solver.status}")
        
        # Check if solve was successful
        if results.solver.termination_condition == pyo.TerminationCondition.optimal:
            print("✓ Solve successful")
        else:
            print("❌ Solve failed")
            print(f"Termination condition: {results.solver.termination_condition}")
            print(f"Solver status: {results.solver.status}")
            if hasattr(results.solver, 'message'):
                print(f"Solver message: {results.solver.message}")
            return False
        
        # Display basic results
        print("\n" + "="*50)
        print("BASIC EVAPORATION POND RESULTS")
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
        print("="*50)
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_evaporation_pond_basic()
    if success:
        print("\n✅ Basic evaporation pond test passed!")
    else:
        print("\n❌ Basic evaporation pond test failed!")
        sys.exit(1) 