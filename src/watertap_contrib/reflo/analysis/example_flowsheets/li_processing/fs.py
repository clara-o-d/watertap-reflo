import io
import pydoc
import sys

from watertap_contrib.reflo.analysis.example_flowsheets.li_processing.pc_build_flowsheet import build_flowsheet
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.solve import solve
from watertap_contrib.reflo.analysis.example_flowsheets.li_processing.add_costing import add_costing
from watertap_contrib.reflo.analysis.example_flowsheets.li_processing.process_costing import process_costing
from watertap_contrib.reflo.analysis.example_flowsheets.li_processing.display_results import display_results
from watertap_contrib.reflo.analysis.example_flowsheets.li_processing.save_results import save_results
from pyomo.environ import assert_optimal_termination
from idaes.core.util import DiagnosticsToolbox
from idaes.core.util.model_statistics import degrees_of_freedom


def _paged_display_results(m, **kwargs):
    buf = io.StringIO()
    sys.stdout = buf
    try:
        display_results(m, **kwargs)
    finally:
        sys.stdout = sys.__stdout__
    pydoc.pager(buf.getvalue())


def main():
    """
    Build and solve the lithium carbonate processing flowsheet in stages.
    
    This script demonstrates the staged build approach:
    - Stage 1: Feed + storage + pump
    - Stage 2: Stage 1 + soda ash reactor (first softening)
    - Stage 3: Stage 2 + lime reactor (second softening)
    - Stage 4: Stage 3 + lithium carbonate reactor (Li precipitation)
    - Stage 5: Stage 4 + dewatering units (complete flowsheet)
    """
    print("\n" + "="*80)
    print("STAGE 1: BUILDING FEED, STORAGE TANK, AND PUMP")
    print("="*80)
    m = build_flowsheet(stage=1)
    dt = DiagnosticsToolbox(m)
    dt.display_underconstrained_set()
    input("Press enter to solve Stage 1")
    assert degrees_of_freedom(m) == 0, f"Stage 1: expected 0 DOF, got {degrees_of_freedom(m)}"
    results = solve(m)
    assert_optimal_termination(results)
    print("\n=== STAGE 1 RESULTS ===")
    display_results(m)
    input("Press enter to continue to Stage 2")

    print("\n" + "="*80)
    print("STAGE 2: ADDING SODA ASH REACTOR (FIRST SOFTENING STAGE)")
    print("="*80)
    m = build_flowsheet(stage=2)
    dt = DiagnosticsToolbox(m)
    dt.display_underconstrained_set()
    input("Press enter to solve Stage 2")
    assert degrees_of_freedom(m) == 0, f"Stage 2: expected 0 DOF, got {degrees_of_freedom(m)}"
    results = solve(m)
    assert_optimal_termination(results)
    print("\n=== STAGE 2 RESULTS ===")
    display_results(m)
    input("Press enter to continue to Stage 3")

    print("\n" + "="*80)
    print("STAGE 3: ADDING LIME REACTOR (SECOND SOFTENING STAGE)")
    print("="*80)
    m = build_flowsheet(stage=3)
    dt = DiagnosticsToolbox(m)
    dt.display_underconstrained_set()
    input("Press enter to solve Stage 3")
    assert degrees_of_freedom(m) == 0, f"Stage 3: expected 0 DOF, got {degrees_of_freedom(m)}"
    results = solve(m)
    assert_optimal_termination(results)
    print("\n=== STAGE 3 RESULTS ===")
    display_results(m)
    input("Press enter to continue to Stage 4")

    print("\n" + "="*80)
    print("STAGE 4: ADDING LITHIUM CARBONATE REACTOR (Li PRECIPITATION)")
    print("="*80)
    m = build_flowsheet(stage=4)
    dt = DiagnosticsToolbox(m)
    dt.display_underconstrained_set()
    input("Press enter to solve Stage 4")
    assert degrees_of_freedom(m) == 0, f"Stage 4: expected 0 DOF, got {degrees_of_freedom(m)}"
    results = solve(m)
    assert_optimal_termination(results)
    print("\n=== STAGE 4 RESULTS ===")
    display_results(m)
    input("Press enter to continue to Stage 5")

    print("\n" + "="*80)
    print("STAGE 5: ADDING DEWATERING UNITS (COMPLETE FLOWSHEET)")
    print("="*80)
    m = build_flowsheet(stage=5)
    dt = DiagnosticsToolbox(m)
    dt.display_underconstrained_set()
    input("Press enter to solve Stage 5 (complete flowsheet without costing)")
    assert degrees_of_freedom(m) == 0, f"Stage 5: expected 0 DOF, got {degrees_of_freedom(m)}"
    results = solve(m)
    assert_optimal_termination(results)
    print("\n=== STAGE 5 RESULTS (NO COSTING) ===")
    _paged_display_results(m)

    print("\n" + "="*80)
    print("FINAL STAGE: ADDING COSTING TO COMPLETE FLOWSHEET")
    print("="*80)
    input("Press enter to solve with costing")
    add_costing(m)
    process_costing(m)
    assert degrees_of_freedom(m) == 0, f"Final stage (with costing): expected 0 DOF, got {degrees_of_freedom(m)}"
    results = solve(m)
    assert_optimal_termination(results)
    print("\n=== FINAL FLOWSHEET RESULTS (WITH COSTING) ===")
    display_results(m, show_costing=True)
    
    save_results(m)
    
    return m


if __name__ == "__main__":
    m = main()
