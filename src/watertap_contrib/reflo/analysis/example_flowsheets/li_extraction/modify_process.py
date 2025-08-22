"""Process modification module for lithium extraction flowsheet.

Defines additional constraints and parameters for the lithium extraction process.
"""

import pyomo.environ as pyo
from pyomo.environ import units as pyunits, value
from pyomo.core.base.constraint import Constraint
from pyomo.core.base.var import Var
from pyomo.core.base.param import Param

def general_parameters(m):
    """Define general process parameters including density, precipitation, and pumping."""
    # Solution density for brine calculations
    m.fs.rho = Param(
        initialize=1227,
        mutable=True,
        units=pyunits.kg / pyunits.m**3,
        doc="Solution density"
    )
    
    # Pond design safety factor
    m.fs.pond_overdesign_factor = Param(
        initialize=1.0,
        mutable=True,
        units=pyunits.dimensionless,
        doc="Overdesign factor for pond area (multiplier for calculated area)"
    )

def brine_extraction_section(m):
    """Define brine extraction infrastructure parameters."""
    # Wellfield and infrastructure parameters
    m.fs.number_of_wells = Param(
        initialize=379,
        mutable=True,
        units=pyunits.dimensionless,
        doc="Number of extraction wells"
    )
    m.fs.piping_length = Param(
        initialize=5.0,
        mutable=True,
        units=pyunits.km,
        doc="Piping length from wells to pond (km)"
    )
    m.fs.pumping_efficiency = Param(
        initialize=0.7,
        mutable=True,
        units=pyunits.dimensionless,
        doc="Pumping efficiency (fraction)"
    )
    
    # Pumping head calculation parameters
    m.fs.static_head = Param(
        initialize=39.5,
        mutable=True,
        units=pyunits.m,
        doc="Static head (elevation difference)"
    )
    m.fs.friction_head = Param(
        initialize=354,
        mutable=True,
        units=pyunits.m/pyunits.km,
        doc="Friction head loss per km"
    )
    
    # Pumping head variable - calculated from static and friction components
    m.fs.pumping_head = Var(
        initialize=value(m.fs.static_head + m.fs.friction_head * m.fs.piping_length),
        bounds=(0, None),
        units=pyunits.m,
        doc="Pumping head (m)"
    )
    
    # Constraint to calculate total pumping head
    @m.fs.Constraint(doc="Pumping head calculation")
    def eq_pumping_head(b):
        return b.pumping_head == b.static_head + b.friction_head * b.piping_length

def shipping_section(m):
    """Define shipping infrastructure parameters."""
    m.fs.number_of_trucks = Param(
        initialize=230,
        mutable=True,
        units=pyunits.dimensionless,
        doc="Number of trucks"
    )
    m.fs.shipping_distance = Param(
        initialize=250,
        mutable=True,
        units=pyunits.km,
        doc="Shipping distance to next facility (km)"
    )

def flow_parameters(m):
    """Define flow and evaporation parameters."""
    # Fixed parameters
    m.fs.final_li_conc = Param(
        initialize=0.055,
        mutable=True,
        units=pyunits.kg / pyunits.kg,
        doc="Final lithium concentration"
    )
    
    m.fs.li_recovery = Param(
        initialize=0.6,
        mutable=True,
        units=pyunits.dimensionless,
        doc="Lithium recovery fraction"
    )
    
    m.fs.final_tds_conc = Param(
        initialize=0.429,
        mutable=True,
        units=pyunits.kg / pyunits.kg,
        doc="Final TDS concentration"
    )
    
def flow_variables(m):
    """Define flow and evaporation variables."""
    m.fs.li_outflow = Var(
        initialize=1.536,
        bounds=(0, None),
        units=pyunits.kg / pyunits.s,
        doc="Lithium outflow rate"
    )
    
    m.fs.concentrated_brine_outflow = Var(
        initialize=25.6,
        bounds=(0, None),
        units=pyunits.kg / pyunits.s,
        doc="TDS and water outflow rate"
    )
    
    m.fs.tds_outflow = Var(
        initialize=10.96,
        bounds=(0, None),
        units=pyunits.kg / pyunits.s,
        doc="TDS outflow rate"
    )
    
    m.fs.water_outflow = Var(
        initialize=14.64,
        bounds=(0, None),
        units=pyunits.kg / pyunits.s,
        doc="Water outflow rate"
    )
    
    m.fs.fraction_evaporated = Var(
        initialize=0.987,
        bounds=(0, 0.99),
        units=pyunits.dimensionless,
        doc="Fraction of water that is evaporated"
    )
    
    m.fs.pond.mass_flow_precipitate = Var(
        initialize=14000000000,
        bounds=(0, None),
        units=pyunits.kg / pyunits.year,
        doc="Annual mass flow of precipitate"
    )

def flow_constraints(m):
    """Define flow and evaporation constraints."""
    prop_in = m.fs.feed.properties[0]
    
    # Constraint: li_outflow = li_inflow * li_recovery
    @m.fs.Constraint(doc="Lithium outflow constraint")
    def eq_li_outflow(b):
        return b.li_outflow == prop_in.flow_mass_phase_comp["Liq", "Li+"] * b.li_recovery
    
    # Constraint: tds_water_outflow = li_outflow / final_li_conc
    @m.fs.Constraint(doc="Concentrated brine outflow constraint")
    def eq_concentrated_brine_outflow(b):
        return b.concentrated_brine_outflow * b.final_li_conc == b.li_outflow
    
    # Constraint: tds_outflow = final_tds_conc * concentrated_brine_outflow
    @m.fs.Constraint(doc="TDS outflow constraint")
    def eq_tds_outflow(b):
        return b.tds_outflow == b.final_tds_conc * b.concentrated_brine_outflow
    
    # Constraint: water_outflow = concentrated_brine_outflow - tds_outflow
    @m.fs.Constraint(doc="Water outflow constraint")
    def eq_water_outflow(b):
        return b.water_outflow == b.concentrated_brine_outflow - b.tds_outflow
    
    # Constraint: fraction_evaporated = 1 - water_outflow / water_inflow
    @m.fs.Constraint(doc="Fraction evaporated constraint")
    def eq_fraction_evaporated(b):
        return b.fraction_evaporated * prop_in.flow_mass_phase_comp["Liq", "H2O"] == prop_in.flow_mass_phase_comp["Liq", "H2O"] - b.water_outflow
    
    # Constraint: mass_flow_precipitate = tds_inflow - tds_outflow * 3600 * 24 * 365
    @m.fs.Constraint(doc="Mass flow precipitate constraint")
    def eq_mass_flow_precipitate(b):
        return b.pond.mass_flow_precipitate == pyunits.convert(prop_in.flow_mass_phase_comp["Liq", "TDS"] - b.tds_outflow, to_units=pyunits.kg / pyunits.year)

def evaporative_area_section(m):
    """Define evaporative area constraints with overdesign factor."""
    # Custom evaporative area constraint with overdesign factor
    def eq_total_evaporative_area_required_partial(b):
        # Area * mass_flux = water_evaporated * overdesign_factor
        return b.total_evaporative_area_required * b.mass_flux_water_vapor_average == m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "H2O"] * m.fs.fraction_evaporated * m.fs.pond_overdesign_factor
    m.fs.pond.eq_total_evaporative_area_required_partial = Constraint(rule=eq_total_evaporative_area_required_partial, doc="Total evaporative area required for partial evaporation with overdesign factor")

def modify_process(m):
    """Apply process modifications to the flowsheet."""
    # Remove original expressions and constraints
    if hasattr(m.fs.pond, 'mass_flow_precipitate'):
        m.fs.pond.del_component('mass_flow_precipitate')
    if hasattr(m.fs.pond, 'eq_total_evaporative_area_required'):
        m.fs.pond.eq_total_evaporative_area_required.deactivate()
        
    # Add all parameters and infrastructure
    general_parameters(m)
    brine_extraction_section(m)
    shipping_section(m)
    
    # Add flow and evaporation infrastructure
    flow_parameters(m)
    flow_variables(m)
    flow_constraints(m)
    evaporative_area_section(m)
