import pyomo.environ as pyo
from pyomo.environ import units as pyunits


def process_costing(m):
    # Molar masses and mass flows
    M_Li = 6.94e-3
    M_Li2CO3 = 73.89e-3
    M_LiOH_H2O = 41.96e-3
    li_mass_flow = m.fs.li2co3_product.properties[0].flow_mass_phase_comp["Liq", "li+"]
    li2co3_mass_flow = li_mass_flow * (M_Li2CO3 / (2 * M_Li))
    lioh_mass_flow = li_mass_flow * (M_LiOH_H2O / M_Li)
    
    # Volumetric LCOLi (for reference)
    m.fs.density_concentrated_brine = pyo.Param(
        initialize=1323,  # placeholder value, kg/m^3
        mutable=True,
        units=pyunits.kg / pyunits.m**3,
        doc="Density of concentrated brine for Li+ volume calculation"
    )
    vol_flow_li = li_mass_flow / m.fs.density_concentrated_brine  # m³/s
    if hasattr(m.fs.costing, "add_LCOW"):
        m.fs.costing.add_LCOW(vol_flow_li, name="LCOLi")
    
    # Mass-based LCOLi for Li2CO3
    m.fs.costing.LCOLi2CO3 = pyo.Var(
        initialize=1000,
        units=m.fs.costing.base_currency / pyunits.t,
        bounds=(0, None),
        doc="Levelized cost of lithium carbonate by mass ($/t)"
    )
    m.fs.costing.LCOLi2CO3_constraint = pyo.Constraint(
        expr=m.fs.costing.LCOLi2CO3 == m.fs.costing.LCOLi / li2co3_mass_flow * pyunits.convert(1 * pyunits.s, to_units=pyunits.year) / 1000
    )
    
    # Mass-based LCOLi for LiOH·H2O
    m.fs.costing.LCOLiOH_H2O = pyo.Var(
        initialize=1000,
        units=m.fs.costing.base_currency / pyunits.t,
        bounds=(0, None),
        doc="Levelized cost of lithium hydroxide monohydrate by mass ($/t)"
    )
    m.fs.costing.LCOLiOH_H2O_constraint = pyo.Constraint(
        expr=m.fs.costing.LCOLiOH_H2O == m.fs.costing.LCOLi / lioh_mass_flow * pyunits.convert(1 * pyunits.s, to_units=pyunits.year) / 1000
    ) 