from watertap_contrib.reflo.analysis.example_flowsheets.li_processing.pc_build_flowsheet import build_flowsheet
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.solve import solve
from watertap_contrib.reflo.analysis.example_flowsheets.li_processing.add_costing import add_costing
from watertap_contrib.reflo.analysis.example_flowsheets.li_processing.process_costing import process_costing
from watertap_contrib.reflo.analysis.example_flowsheets.li_processing.display_results import display_results
from pyomo.environ import assert_optimal_termination
from idaes.core.util import DiagnosticsToolbox


def main():
    print("\n" + "="*80)
    print("STAGE 1: BUILDING FEED, STORAGE TANK, AND PUMP")
    print("="*80)
    m = build_flowsheet(stage=1)
    dt = DiagnosticsToolbox(m)
    dt.display_underconstrained_set()
    input("Press enter to solve Stage 1")
    results = solve(m)
    assert_optimal_termination(results)
    print("\n=== STAGE 1 RESULTS ===")
    display_results(m)
    input("Press enter to continue to Stage 2")

    print("\n" + "="*80)
    print("STAGE 2: ADDING STOICHIOMETRIC REACTORS")
    print("="*80)
    m = build_flowsheet(stage=2)
    dt = DiagnosticsToolbox(m)
    dt.display_underconstrained_set()
    input("Press enter to solve Stage 2")
    results = solve(m)
    assert_optimal_termination(results)
    print("\n=== STAGE 2 RESULTS ===")
    display_results(m)
    input("Press enter to continue to Stage 3")

    print("\n" + "="*80)
    print("STAGE 3: ADDING DEWATERERS")
    print("="*80)
    m = build_flowsheet(stage=3)
    dt = DiagnosticsToolbox(m)
    dt.display_underconstrained_set()
    input("Press enter to solve Stage 3 (complete flowsheet without costing)")
    results = solve(m)
    assert_optimal_termination(results)
    print("\n=== STAGE 3 RESULTS (NO COSTING) ===")
    display_results(m)

    print("\n" + "="*80)
    print("FINAL STAGE: ADDING COSTING TO COMPLETE FLOWSHEET")
    print("="*80)
    input("Press enter to solve with costing")
    add_costing(m)
    process_costing(m)
    results = solve(m)
    assert_optimal_termination(results)
    print("\n=== FINAL FLOWSHEET RESULTS (WITH COSTING) ===")
    display_results(m, show_costing=True)
    
    return m


if __name__ == "__main__":
    m = main() 