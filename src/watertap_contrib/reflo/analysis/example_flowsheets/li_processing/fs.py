from watertap_contrib.reflo.analysis.example_flowsheets.li_processing.build_flowsheet import build_flowsheet
from watertap_contrib.reflo.analysis.example_flowsheets.li_processing.solve import solve
# from watertap_contrib.reflo.analysis.example_flowsheets.li_processing.add_costing import add_costing
# from watertap_contrib.reflo.analysis.example_flowsheets.li_processing.process_costing import process_costing
from watertap_contrib.reflo.analysis.example_flowsheets.li_processing.display_results import display_results
from pyomo.environ import assert_optimal_termination
from idaes.core.util import DiagnosticsToolbox


def main():
    m = build_flowsheet()
    # dt = DiagnosticsToolbox(m)
    # dt.report_structural_issues(m)

    results = solve(m)
    assert_optimal_termination(results)
    print("\n=== LITHIUM PROCESSING FLOWSHEET RESULTS ===")
    display_results(m)
    
    # Costing is disabled for now due to complexity of mixed unit types:
    # - BoronRemoval (standard WaterTAP) needs specific costing method definition
    # - ChemicalSoftening (REFLO custom) has default_costing_method but requires REFLOCosting
    # - StorageTankZO/ClarifierZO (zero-order) need database configuration
    # This would require significant additional setup to implement properly.
    
    # Uncomment these lines when costing setup is completed:
    # print("\n=== INITIAL FLOWSHEET RESULTS (NO COSTING) ===")
    # input("Press enter to solve with costing")
    # add_costing(m)
    # process_costing(m)
    # results = solve(m)
    # assert_optimal_termination(results)
    # print("\n=== FINAL FLOWSHEET RESULTS (WITH COSTING) ===")
    # display_results(m)


if __name__ == "__main__":
    main() 