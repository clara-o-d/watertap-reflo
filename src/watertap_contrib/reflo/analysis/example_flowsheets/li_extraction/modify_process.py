"""Process modification module for lithium extraction flowsheet.

Defines additional constraints and parameters for the lithium extraction process.
"""

import pyomo.environ as pyo
from pyomo.environ import units as pyunits, value
from pyomo.core.base.constraint import Constraint
from pyomo.core.base.expression import Expression
from pyomo.core.base.var import Var
from pyomo.core.base.param import Param
from idaes.core.util.math import smooth_min, smooth_max
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.utils import compute_evaporation_fraction_for_target_li_conc

def define_general_parameters(m):
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

def define_flow_and_evaporation_section(m):
    """Define flow and evaporation fraction constraints."""
    # Evaporation and outflow fraction variables
    m.fs.fraction_outflow = Var(
        initialize=0.01,
        bounds=(0.01, 0.99),
        units=pyunits.dimensionless,
        doc="Fraction of water that flows out (not evaporated)"
    )
    m.fs.water_outflow = pyo.Var(
        initialize=11.2,
        bounds=(0, None),
        units=pyunits.kg / pyunits.s,
        doc="Water flow rate in the outflow stream"
    )
    m.fs.fraction_evaporated = Var(
        initialize=0.99,
        bounds=(0.01, 0.99),
        units=pyunits.dimensionless,
        doc="Fraction of water that is evaporated"
    )

    prop_in = m.fs.feed.properties[0]
    # Mass balance constraint: outflow + evaporated = 1
    def eq_fraction_outflow(b):
        return b.fraction_outflow + b.fraction_evaporated == 1
    m.fs.eq_fraction_outflow = Constraint(rule=eq_fraction_outflow, doc="Fraction of outflow water")
    # Calculate water evaporated based on fraction
    m.fs.water_evaporated = Expression(expr=prop_in.flow_mass_phase_comp["Liq", "H2O"] * m.fs.fraction_evaporated)
    
    # Water outflow mass balance
    def eq_water_outflow(b):
        return b.water_outflow == prop_in.flow_mass_phase_comp["Liq", "H2O"] * b.fraction_outflow
    m.fs.eq_water_outflow = Constraint(rule=eq_water_outflow, doc="Water outflow mass balance")

def define_precipitate_section(m):
    """Define precipitate mass flow constraints."""
    # Precipitation model coefficients from empirical fit (kg/m³)
    m.fs.pond.annual_solid_precipitate_a = Param(
        initialize=-3.1473e02, mutable=True, doc="Linear fit coefficient a [kg/m³]",
        units=pyunits.kg/pyunits.m**3
    )
    m.fs.pond.annual_solid_precipitate_b = Param(
        initialize=3.5704e02, mutable=True, doc="Linear fit intercept b [kg/m³]",
        units=pyunits.kg/pyunits.m**3
    )
    # Remove existing precipitate variable if it exists
    if hasattr(m.fs.pond, 'mass_flow_precipitate'):
        m.fs.pond.del_component('mass_flow_precipitate')
    # Annual precipitate mass flow variable
    m.fs.pond.mass_flow_precipitate = Var(
        initialize=12508164782,
        bounds=(0, None),
        units=pyunits.kg / pyunits.year,
        doc="Annual mass flow of precipitate"
    )
    prop_in = m.fs.feed.properties[0]
    # Calculate precipitate mass flow using empirical correlation
    def eq_mass_flow_precipitate(b):
        # Linear fit: precipitate_concentration = a * (1-evap_frac) + b
        precipitate_concentration = m.fs.pond.annual_solid_precipitate_a * (1 - m.fs.fraction_evaporated) + m.fs.pond.annual_solid_precipitate_b
        original_water_volume = prop_in.flow_mass_phase_comp["Liq", "H2O"] / (1000 * pyunits.kg / pyunits.m**3)
        annual_mass_flow = pyunits.convert(precipitate_concentration * original_water_volume, to_units=pyunits.kg/pyunits.year)
        return b.mass_flow_precipitate == annual_mass_flow
    m.fs.pond.eq_mass_flow_precipitate = Constraint(rule=eq_mass_flow_precipitate, doc="Annual mass flow of precipitate from concentration and water volume")

def define_tds_section(m):
    """Define TDS outflow and concentration constraints."""
    # TDS outflow and concentration variables
    m.fs.tds_outflow = Var(
        initialize=56.64,
        bounds=(0, None),
        units=pyunits.kg / pyunits.s,
        doc="TDS flow rate in the outflow stream"
    )
    m.fs.tds_concentration_outflow = Var(
        initialize=6205.13,
        bounds=(0, None),
        units=pyunits.kg / pyunits.m**3,
        doc="TDS concentration in the outflow stream"
    )
    prop_in = m.fs.feed.properties[0]
    # TDS outflow = TDS inlet - TDS precipitated
    def eq_tds_outflow(b):
        return b.tds_outflow == prop_in.flow_mass_phase_comp["Liq", "TDS"] - pyunits.convert(m.fs.pond.mass_flow_precipitate, to_units=pyunits.kg/pyunits.s)
    m.fs.eq_tds_outflow = Constraint(rule=eq_tds_outflow, doc="TDS outflow mass balance")
    # TDS concentration = TDS outflow / water outflow * density
    def eq_tds_concentration_outflow(b):
        return b.tds_concentration_outflow * b.water_outflow == b.tds_outflow * b.rho
    m.fs.eq_tds_concentration_outflow = Constraint(rule=eq_tds_concentration_outflow, doc="TDS concentration in outflow")

def define_lithium_section(m):
    """Define lithium outflow constraints."""
    # Target lithium concentration parameter
    m.fs.target_li_concentration = Param(
        initialize=12.6,
        mutable=True,
        units=pyunits.g / pyunits.kg,
        doc="Target Li+ concentration in outflow"
    )
    # Lithium outflow variable
    m.fs.li_outflow = Var(
        initialize=0.86,
        bounds=(0, None),
        units=pyunits.kg / pyunits.second,
        doc="Li+ outflow"
    )
    # Lithium outflow using empirical correlation with smooth minimum
    def eq_li_outflow(b):
        # Quadratic fit: mass_fraction = 88.1606*evap_frac² - 169.2358*evap_frac + 81.4783
        return b.li_outflow == m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "Li+"] * smooth_min(1.0, 88.1606 * b.fraction_evaporated**2 + -169.2358 * b.fraction_evaporated + 81.4783, eps=1e-3)
    m.fs.eq_li_outflow = Constraint(rule=eq_li_outflow, doc="Li+ outflow mass balance")

def define_concentrated_brine_outflow_section(m):
    """Define concentrated brine outflow constraints."""
    # Total concentrated brine outflow for shipping
    m.fs.concentrated_brine_outflow = Var(
        initialize=67.84,
        bounds=(0, None),
        units=pyunits.kg / pyunits.second,
        doc="Total concentrated brine outflow for shipping (post-evaporation)"
    )
    # Brine outflow = water outflow + TDS outflow
    def eq_concentrated_brine_outflow(b):
        return b.concentrated_brine_outflow == b.water_outflow + b.tds_outflow
    m.fs.eq_concentrated_brine_outflow = Constraint(rule=eq_concentrated_brine_outflow, doc="Concentrated brine outflow for shipping")

def define_evaporative_area_section(m):
    """Define evaporative area constraints with overdesign factor."""
    # Deactivate default evaporative area constraint
    if hasattr(m.fs.pond, 'eq_total_evaporative_area_required'):
        m.fs.pond.eq_total_evaporative_area_required.deactivate()
    # Custom evaporative area constraint with overdesign factor
    def eq_total_evaporative_area_required_partial(b):
        # Area * mass_flux = water_evaporated * overdesign_factor
        return b.total_evaporative_area_required * b.mass_flux_water_vapor_average == m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "H2O"] * m.fs.fraction_evaporated * m.fs.pond_overdesign_factor
    m.fs.pond.eq_total_evaporative_area_required_partial = Constraint(rule=eq_total_evaporative_area_required_partial, doc="Total evaporative area required for partial evaporation with overdesign factor")

def define_brine_extraction_section(m):
    # Wellfield and infrastructure parameters
    m.fs.number_of_wells = Param(
        initialize=379,
        mutable=True,
        units=pyunits.dimensionless,
        doc="Number of extraction wells"
    )
    m.fs.piping_length = Param(
        initialize=7.0,
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
        initialize=2000,
        bounds=(0, None),
        units=pyunits.m,
        doc="Pumping head (m)"
    )
    
    # Constraint to calculate total pumping head
    @m.fs.Constraint(doc="Pumping head calculation")
    def eq_pumping_head(b):
        return b.pumping_head == b.static_head + b.friction_head * b.piping_length

def define_shipping_section(m):
    # Shipping infrastructure parameters
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

def define_target_li_concentration_constraint(m):
    """Define target lithium concentration constraint."""
    # Target lithium concentration constraint using the provided equation
    @m.fs.Constraint(doc="Target lithium concentration constraint")
    def eq_target_li_concentration(b):
        prop_in = b.feed.properties[0]
        inlet_li_mass_flow = prop_in.flow_mass_phase_comp["Liq", "Li+"]

        # Complex constraint: Li concentration = target * (1 + TDS/water ratio)
        return inlet_li_mass_flow * smooth_min(1.0, 88.1606 * b.fraction_evaporated**2 + -169.2358 * b.fraction_evaporated + 81.4783, eps=1e-1) / (b.water_outflow) * 1000 == b.target_li_concentration * (1 + b.tds_outflow / b.water_outflow)

def fix_evaporation_fraction_for_target_li(m):
    """Fix evaporation fraction to achieve target lithium concentration."""
    # Get target concentration and compute required evaporation fraction
    target_li_conc = value(m.fs.target_li_concentration)
    evap_frac = compute_evaporation_fraction_for_target_li_conc(m, target_li_conc)
    m.fs.fraction_evaporated.fix(evap_frac)

def modify_process(m):
    """Apply all process modifications to the flowsheet."""
    # Apply all process modifications in sequence
    define_general_parameters(m)
    define_flow_and_evaporation_section(m)
    define_precipitate_section(m)
    define_tds_section(m)
    define_lithium_section(m)
    define_concentrated_brine_outflow_section(m)
    define_evaporative_area_section(m)
    #define_target_li_concentration_constraint(m) 
    fix_evaporation_fraction_for_target_li(m)