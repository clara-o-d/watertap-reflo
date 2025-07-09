"""
Test script for claras_evap_fs.py with costing functionality
"""

import os
import sys
import pyomo.environ as pyo
from pyomo.environ import value, units as pyunits

# Add the parent directory to the path to import the main module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from claras_evap_fs import (
    build, 
    set_operating_conditions, 
    initialize_system, 
    solve, 
    add_costing, 
    initialize_costing, 
    process_costing,
    display_results,
    display_costing_results
)

def test_evaporation_pond_with_costing():
    """Test the evaporation pond with costing functionality"""
    
    print("Testing evaporation pond with costing...")
    
    # Use test data for simplicity
    this_dir = os.path.dirname(os.path.abspath(__file__))
    weather_data_path = os.path.join(this_dir, "evaporation_pond_test_data.csv")
    
    # Build the model
    m = build(weather_data_path)
    
    # Set operating conditions
    set_operating_conditions(m)
    m.fs.pond.number_evaporation_ponds.fix(300)
    
    # Initialize and solve
    initialize_system(m)
    results = solve(m)
    
    if results.solver.termination_condition == pyo.TerminationCondition.optimal:
        print("✓ Initial solve successful")
        
        # Display initial results
        display_results(m, "Test Data")
        
        # Add costing
        add_costing(m)
        initialize_costing(m)
        process_costing(m)
        
        # Solve with costing
        results = solve(m)
        
        if results.solver.termination_condition == pyo.TerminationCondition.optimal:
            print("✓ Solve with costing successful")
            
            # Display costing results
            display_costing_results(m)
            
            # Print some key costing values
            print("\nKey Costing Values:")
            print(f"Capital cost: ${value(m.fs.pond.costing.capital_cost):,.0f}")
            print(f"Fixed operating cost: ${value(m.fs.pond.costing.fixed_operating_cost):,.0f}/year")
            
            if hasattr(m.fs.costing, "LCOLi"):
                lcoli = value(m.fs.costing.LCOLi)
                print(f"LCOLi: ${lcoli:.2f}/m³")
            
            return True
        else:
            print("✗ Solve with costing failed")
            return False
    else:
        print("✗ Initial solve failed")
        return False

if __name__ == "__main__":
    success = test_evaporation_pond_with_costing()
    if success:
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Tests failed!")
        sys.exit(1) 