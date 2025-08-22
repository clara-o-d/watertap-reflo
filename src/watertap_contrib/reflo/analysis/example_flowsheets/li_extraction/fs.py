"""Main lithium extraction flowsheet execution module.

Executes the complete lithium extraction process including building, solving, and displaying results.
"""

from pyomo.core import value
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.build_flowsheet import build_flowsheet
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.solve import solve
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.display_initial_results import display_initial_results
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.add_costing import add_costing
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.display_costing_results import display_costing_results
from idaes.core.util import DiagnosticsToolbox
from pyomo.environ import assert_optimal_termination

__author__ = "Clara Drysdale"


"""
References

Garrett, D.E., 2004. Handbook of lithium and natural calcium chloride. Elsevier Ltd.

Hoffmeister, Dirk (2018): Meteorological and soil measurements of the permanent weather stations in 
the Atacama desert, Chile. CRC1211 Database (CRC1211DB). DOI: 10.5880/CRC1211DB.1 

U.S. Dept. of Interior & Michael C. Mickley (2006)
"Membrane Concentrate Disposal: Practices and Regulation"
Desalination and Water Purification Research and Development Program Report No. 123 (Second Edition)
Chapter 10: Evaporation Pond Disposal

WSP, 2022. Technical report summary: Operation report, Salar de Atacama. WSP-SQM0011-TRS-Salar-Rev1.
"""

def main():
    """Execute the complete lithium extraction flowsheet analysis."""
    m = build_flowsheet()
    # dt = DiagnosticsToolbox(m)
    results = solve(m)
    assert_optimal_termination(results)
    display_initial_results(m)
    
    add_costing(m)
    results = solve(m)
    assert_optimal_termination(results)
    display_initial_results(m)
    display_costing_results(m, detailed=True)

if __name__ == "__main__":
    main() 