"""Process costing calculations for lithium processing flowsheet.

Calculates LCOLi and specific energy consumption metrics based on precipitated Li2CO3.
"""

from pyomo.environ import Param, Var, Constraint
from pyomo.environ import units as pyunits
from watertap_contrib.reflo.analysis.example_flowsheets.li_processing.pc_scaling_factors import set_scaling_factors

def process_costing(m):
    """Initialize costing blocks and add LCOLi calculations based on Li2CO3 production."""
    if hasattr(m.fs, 'brine_storage') and hasattr(m.fs.brine_storage, 'costing'):
        m.fs.brine_storage.costing.initialize()
    if hasattr(m.fs, 'brine_pump') and hasattr(m.fs.brine_pump, 'costing'):
        m.fs.brine_pump.costing.initialize()
    if hasattr(m.fs, 'soda_ash_reactor') and hasattr(m.fs.soda_ash_reactor, 'costing'):
        m.fs.soda_ash_reactor.costing.initialize()
    if hasattr(m.fs, 'lime_reactor') and hasattr(m.fs.lime_reactor, 'costing'):
        m.fs.lime_reactor.costing.initialize()
    if hasattr(m.fs, 'lithium_carbonate_reactor') and hasattr(m.fs.lithium_carbonate_reactor, 'costing'):
        m.fs.lithium_carbonate_reactor.costing.initialize()
    if hasattr(m.fs, 'soda_ash_vacuum_filter') and hasattr(m.fs.soda_ash_vacuum_filter, 'costing'):
        m.fs.soda_ash_vacuum_filter.costing.initialize()
    if hasattr(m.fs, 'soda_ash_centrifuge') and hasattr(m.fs.soda_ash_centrifuge, 'costing'):
        m.fs.soda_ash_centrifuge.costing.initialize()
    if hasattr(m.fs, 'lime_press_filter') and hasattr(m.fs.lime_press_filter, 'costing'):
        m.fs.lime_press_filter.costing.initialize()
    if hasattr(m.fs, 'lime_centrifuge') and hasattr(m.fs.lime_centrifuge, 'costing'):
        m.fs.lime_centrifuge.costing.initialize()
    if hasattr(m.fs, 'li_dewatering') and hasattr(m.fs.li_dewatering, 'costing'):
        m.fs.li_dewatering.costing.initialize()
    
    m.fs.costing.cost_process()

    if hasattr(m.fs, 'lithium_carbonate_reactor'):
        # Calculate Li production from Li2CO3 production
        li2co3_production = m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3']
        
        li_mw = 6.94 * pyunits.g / pyunits.mol
        li2co3_mw = 73.89 * pyunits.g / pyunits.mol
        li_content_fraction = (2 * li_mw) / li2co3_mw  # Li2CO3 contains 2 Li atoms
        
        li_production = li2co3_production * li_content_fraction

        m.fs.costing.add_LCOW(li_production * pyunits.m**3 / pyunits.kg, name="LCOLi")
        m.fs.costing.add_specific_energy_consumption(li_production * pyunits.m**3 / pyunits.kg, name="specific_energy_consumption")
        m.fs.costing.LCOLi_mass = Var(
            initialize=1000,
            units=m.fs.costing.base_currency / pyunits.kg,
            bounds=(0, None),
            doc="Levelized cost of lithium by mass ($/kg Li)"
        )
        m.fs.costing.LCOLi_mass_constraint = Constraint(
            expr=m.fs.costing.LCOLi_mass == pyunits.convert(
                m.fs.costing.LCOLi * pyunits.m**3 / pyunits.kg, 
                to_units=m.fs.costing.base_currency / pyunits.kg
            )
        )

        m.fs.costing.specific_energy_consumption_mass = Var(
            initialize=1000,
            units=pyunits.kWh / pyunits.kg,
            bounds=(0, None),
            doc="Specific energy consumption per kg of lithium (kWh/kg Li)"
        )
        m.fs.costing.specific_energy_consumption_mass_constraint = Constraint(
            expr=m.fs.costing.specific_energy_consumption_mass == pyunits.convert(
                m.fs.costing.specific_energy_consumption * pyunits.m**3 / pyunits.kg, 
                to_units=pyunits.kWh / pyunits.kg
            )
        )

        m.fs.costing.LCOLi2CO3_mass = Var(
            initialize=1000,
            units=m.fs.costing.base_currency / pyunits.kg,
            bounds=(0, None),
            doc="Levelized cost of lithium carbonate by mass ($/kg Li2CO3)"
        )
        m.fs.costing.LCOLi2CO3_mass_constraint = Constraint(
            expr=m.fs.costing.LCOLi2CO3_mass == pyunits.convert(
                m.fs.costing.LCOLi * pyunits.m**3 / pyunits.kg / li_content_fraction, 
                to_units=m.fs.costing.base_currency / pyunits.kg
            )
        )

        m.fs.costing.specific_energy_consumption_Li2CO3_mass = Var(
            initialize=1000,
            units=pyunits.kWh / pyunits.kg,
            bounds=(0, None),
            doc="Specific energy consumption per kg of lithium carbonate (kWh/kg Li2CO3)"
        )
        m.fs.costing.specific_energy_consumption_Li2CO3_mass_constraint = Constraint(
            expr=m.fs.costing.specific_energy_consumption_Li2CO3_mass == pyunits.convert(
                m.fs.costing.specific_energy_consumption * pyunits.m**3 / pyunits.kg / li_content_fraction, 
                to_units=pyunits.kWh / pyunits.kg
            )
        )
    
    set_scaling_factors(m)

