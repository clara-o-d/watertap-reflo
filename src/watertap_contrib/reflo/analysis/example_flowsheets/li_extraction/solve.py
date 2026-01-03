"""Flowsheet solving module with fallback solver options."""

from watertap.core.solvers import get_solver
from pyomo.environ import TerminationCondition
from idaes.core.util.model_diagnostics import DiagnosticsToolbox
from idaes.core.util.model_statistics import degrees_of_freedom

def solve(m, solver=None):
    """Solve the flowsheet model with fallback solver options.
    
    Args:
        m: Pyomo model to solve
        solver: Optional solver instance
        
    Returns:
        Solver results object
    """
    if solver is None:
        solver = get_solver()

    # Try with default settings first
    print("Attempting solve with default solver settings...")
    print("Degrees of freedom: ", degrees_of_freedom(m))
    try:
        results = solver.solve(m, tee=True)
        tc = results.solver.termination_condition
    except Exception as e:
        print(f"Default solve failed with exception: {e}")
        results = None
        tc = None

    # If first attempt fails, try with improved settings
    if (results is None or tc != TerminationCondition.optimal):
        #input("Default solve failed. Press Enter to try with improved settings...")
        solver.options = {
            "tol": 1e-4,
            "constr_viol_tol": 5e-5,  
            "acceptable_constr_viol_tol": 1e-4,
            "acceptable_tol": 1e-4,
            "bound_push": 1e-5,
            "bound_frac": 1e-5,
            "max_iter": 5000,
            "linear_solver": "ma27",
            "hessian_approximation": "limited-memory",
            "mu_strategy": "adaptive",
            "mu_oracle": "probing",
            "alpha_for_y": "primal",
            "slack_bound_push": 0.01,
            "slack_bound_frac": 0.01,
            "print_level": 5,
            "warm_start_init_point": "yes",
            "warm_start_bound_push": 1e-5,
            "warm_start_mult_bound_push": 1e-5,
        }
        try:
            results = solver.solve(m, tee=True)
            tc = results.solver.termination_condition
        except Exception as e:
            print(f"Second solve failed with exception: {e}")
            results = None
            tc = None
    
    # If still not optimal, run diagnostics to identify issues
    if tc != TerminationCondition.optimal:
        print("\n" + "="*80)
        print("SOLVER FAILED - Running IDAES Diagnostics to identify issues...")
        print("="*80)
        
        try:
            dt = DiagnosticsToolbox(m)
            
            print("\n1. Degrees of Freedom:")
            print(f"   DOF = {degrees_of_freedom(m)}")
            
            print("\n2. Checking for numerical warnings...")
            dt.report_numerical_issues()
            
            print("\n3. Displaying constraints with largest residuals...")
            dt.display_constraints_with_large_residuals()
            
            print("\n4. Computing infeasibility explanation...")
            dt.display_near_parallel_constraints()
            
            print("\n5. Analyzing constraint/variable interactions...")
            print("\nVariables involved in violated constraints:")
            dt.display_variables_with_extreme_jacobians()
            
            print("\n" + "="*80)
            print("Diagnostics complete!")
            print("="*80 + "\n")
        except Exception as e:
            print(f"Diagnostic analysis failed: {e}")
            import traceback
            traceback.print_exc()

    return results