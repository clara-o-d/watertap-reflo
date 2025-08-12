"""Process costing calculations for lithium extraction flowsheet.

Calculates LCOLi and specific energy consumption metrics.
"""

from pyomo.environ import Param, Var, Constraint
from pyomo.environ import units as pyunits
from pyomo.environ import value

def process_costing(m):
    """Initialize costing and add LCOLi calculations.
    
    Args:
        m: Pyomo model with costing block
    """
    m.fs.pond.costing.initialize()
    m.fs.costing.cost_process()
    m.fs.costing.initialize()

    m.fs.density_concentrated_brine = Param(
        initialize=1323,
        mutable=True,
        units=pyunits.kg / pyunits.m**3,
        doc="Density of concentrated brine for Li+ volume calculation"
    )
    vol_flow_li = m.fs.li_outflow / m.fs.density_concentrated_brine  # m³/s
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
        expr=m.fs.costing.LCOLi_mass == pyunits.convert(m.fs.costing.LCOLi / m.fs.density_concentrated_brine, to_units=m.fs.costing.base_currency / pyunits.t)
    ) 