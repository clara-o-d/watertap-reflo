"""Process costing calculations for lithium processing flowsheet.

Calculates LCOLi and specific energy consumption metrics based on precipitated Li2CO3.
"""

from pyomo.environ import Param, Var, Constraint
from pyomo.environ import units as pyunits

def process_costing(m):
    """Initialize costing and add LCOLi calculations.
    
    Args:
        m: Pyomo model with costing block
    """
    # Initialize costing blocks
    if hasattr(m.fs.brine_storage, 'costing'):
        m.fs.brine_storage.costing.initialize()
    if hasattr(m.fs.brine_pump, 'costing'):
        m.fs.brine_pump.costing.initialize()
    if hasattr(m.fs.softening_reactor, 'costing'):
        m.fs.softening_reactor.costing.initialize()
    if hasattr(m.fs.lithium_carbonate_reactor, 'costing'):
        m.fs.lithium_carbonate_reactor.costing.initialize()
    
    m.fs.costing.cost_process()
    m.fs.costing.initialize()

    # Calculate Li2CO3 production rate (kg/s)
    li2co3_production = m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3']
    
    # Convert Li2CO3 to equivalent Li mass flow rate
    # Li2CO3 molecular weight: 73.89 g/mol
    # Li atomic weight: 6.94 g/mol  
    # Li content in Li2CO3: 2 * 6.94 / 73.89 = 0.188
    li_mw = 6.94 * pyunits.g / pyunits.mol
    li2co3_mw = 73.89 * pyunits.g / pyunits.mol
    li_content_fraction = (2 * li_mw) / li2co3_mw  # fraction of Li in Li2CO3
    
    # Li production rate (kg/s)
    li_production = li2co3_production * li_content_fraction
    
    # Calculate volumetric flow rate of Li (m³/s) - using density of Li metal
    li_density = 534 * pyunits.kg / pyunits.m**3  # density of Li metal at 20°C
    vol_flow_li = li_production / li_density  # m³/s

    # Add LCOLi calculation (cost per m³ of Li)
    m.fs.costing.add_LCOW(vol_flow_li, name="LCOLi")  # $/m³ Li
    
    # Add specific energy consumption calculation (kWh per m³ of Li)
    m.fs.costing.add_specific_energy_consumption(vol_flow_li, name="specific_energy_consumption")

    # Add variable and constraint for $/kg Li
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

    # Add variable and constraint for kWh/kg Li
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

    # Add variable and constraint for $/kg Li2CO3
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

    # Add variable and constraint for kWh/kg Li2CO3
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
