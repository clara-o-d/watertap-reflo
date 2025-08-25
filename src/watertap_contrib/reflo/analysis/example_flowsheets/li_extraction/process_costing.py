"""Process costing calculations for lithium extraction flowsheet.

Calculates LCOLi and specific energy consumption metrics.
"""

from pyomo.environ import Param, Var, Constraint
from pyomo.environ import units as pyunits

def process_costing(m):
    """Initialize costing and add LCOLi calculations.
    
    Args:
        m: Pyomo model with costing block
    """
    m.fs.pond.costing.initialize()
    m.fs.costing.cost_process()
    m.fs.costing.initialize()

    vol_flow_li = m.fs.li_outflow * pyunits.m**3 / pyunits.kg # m³/s

    m.fs.costing.add_LCOW(vol_flow_li, name="LCOLi") # $/m³ Li
    m.fs.costing.add_specific_energy_consumption(vol_flow_li, name="specific_energy_consumption")

    # Add variable and constraint for $/kg
    m.fs.costing.LCOLi_mass = Var(
        initialize=1000,
        units=m.fs.costing.base_currency / pyunits.t,
        bounds=(0, None),
        doc="Levelized cost of lithium by mass ($/mt)"
    )
    m.fs.costing.LCOLi_mass_constraint = Constraint(
        expr=m.fs.costing.LCOLi_mass == pyunits.convert(m.fs.costing.LCOLi * pyunits.m**3 / pyunits.kg, to_units=m.fs.costing.base_currency / pyunits.t)
    )

    # Add variable and constraint for kWh/kg
    m.fs.costing.specific_energy_consumption_mass = Var(
        initialize=1000,
        units=pyunits.kWh / pyunits.t,
        bounds=(0, None),
        doc="Specific energy consumption per tonne of lithium (kWh/t)"
    )
    m.fs.costing.specific_energy_consumption_mass_constraint = Constraint(
        expr=m.fs.costing.specific_energy_consumption_mass == pyunits.convert(m.fs.costing.specific_energy_consumption * pyunits.m**3 / pyunits.kg, to_units=pyunits.kWh / pyunits.t)
    )