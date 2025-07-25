from watertap.core.solvers import get_solver
from pyomo.environ import TerminationCondition

def solve(m, solver=None):
    if solver is None:
        solver = get_solver()

    # Try with default settings first
    print("Attempting solve with default solver settings...")
    try:
        results = solver.solve(m, tee=True)
        tc = results.solver.termination_condition
    except Exception as e:
        print(f"Default solve failed with exception: {e}")
        results = None
        tc = None

    # If first attempt fails, try with improved settings
    if (results is None or tc != TerminationCondition.optimal):
        print("Default solve failed, trying with improved settings...")
        solver.options = {
            "tol": 1e-5,
            "constr_viol_tol": 1e-5,
            "acceptable_constr_viol_tol": 1e-5,
            "bound_push": 1e-5,
            "bound_frac": 1e-5,
            "max_iter": 1000,
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

        # If second attempt fails, try with more aggressive settings
        if (results is None or tc != TerminationCondition.optimal):
            print("Second solve attempt failed, trying with more aggressive settings...")
            solver.options.update({
                "tol": 1e-4,
                "constr_viol_tol": 1e-4,
                "acceptable_constr_viol_tol": 1e-4,
                "max_iter": 2000,
                "print_level": 12,
            })
            try:
                results = solver.solve(m, tee=True)
            except Exception as e:
                print(f"Third solve failed with exception: {e}")
                results = None

    return results