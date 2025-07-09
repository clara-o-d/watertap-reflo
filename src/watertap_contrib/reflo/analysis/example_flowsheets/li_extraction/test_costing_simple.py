"""
Simple test script for costing functionality
"""

import os
import sys
import pyomo.environ as pyo
from pyomo.environ import value, units as pyunits

# Add the parent directory to the path to import the main module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_costing_integration():
    """Test the costing integration with improved error handling"""
    
    print("Testing costing integration with improved error handling...")
    
    try:
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
            
            # Add costing with improved error handling
            add_costing(m)
            initialize_costing(m)
            process_costing(m)
            
            # Solve with costing
            results = solve(m)
            
            if results.solver.termination_condition == pyo.TerminationCondition.optimal:
                print("✓ Solve with costing successful")
                
                # Display costing results
                display_costing_results(m)
                
                return True
            else:
                print("✗ Solve with costing failed")
                print(f"Solver status: {results.solver.termination_condition}")
                return False
        else:
            print("✗ Initial solve failed")
            print(f"Solver status: {results.solver.termination_condition}")
            return False
            
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("This may be due to missing dependencies or environment issues.")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_costing_integration()
    if success:
        print("\n✓ Costing integration test passed!")
    else:
        print("\n✗ Costing integration test failed!")
        sys.exit(1) 