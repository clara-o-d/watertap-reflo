from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.build_flowsheet import build_flowsheet
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.solve import solve
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.display_initial_results import display_initial_results
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.add_costing import add_costing
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.process_costing import process_costing
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.display_costing_results import display_costing_results
from idaes.core.util import DiagnosticsToolbox
from pyomo.environ import assert_optimal_termination

def main():
    m = build_flowsheet()
    # dt = DiagnosticsToolbox(m)
    results = solve(m)
    assert_optimal_termination(results)
    display_initial_results(m)
    add_costing(m)
    process_costing(m)
    results = solve(m)
    assert_optimal_termination(results)
    display_costing_results(m, detailed=True)

if __name__ == "__main__":
    main() 