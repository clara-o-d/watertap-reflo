import pyomo.environ as pyo
from pyomo.environ import units as pyunits, value
from pyomo.core.base.constraint import Constraint
from pyomo.core.base.expression import Expression
from pyomo.core.base.var import Var
from pyomo.core.base.param import Param
from idaes.core.util.math import smooth_min

def define_general_parameters(m):
    m.fs.rho = Param(
        initialize=1227,
        mutable=True,
        units=pyunits.kg / pyunits.m**3,
        doc="Solution density"
    )
    m.fs.pond.annual_solid_precipitate_a = Param(
        initialize=-3.1473e02, mutable=True, doc="Linear fit coefficient a [kg/m³]",
        units=pyunits.kg/pyunits.m**3
    )
    m.fs.pond.annual_solid_precipitate_b = Param(
        initialize=3.5704e02, mutable=True, doc="Linear fit intercept b [kg/m³]",
        units=pyunits.kg/pyunits.m**3
    )
    m.fs.shipping_distance = Param(
        initialize=200,
        mutable=True,
        units=pyunits.km,
        doc="Shipping distance to next facility (km)"
    )
    
    # Overdesign factor for pond area
    m.fs.pond_overdesign_factor = Param(
        initialize=1.1,
        mutable=True,
        units=pyunits.dimensionless,
        doc="Overdesign factor for pond area (multiplier for calculated area)"
    )
    
    # Parameters needed for costing constraints
    m.fs.number_of_wells = Param(
        initialize=320,
        mutable=True,
        units=pyunits.dimensionless,
        doc="Number of extraction wells"
    )
    m.fs.piping_length = Param(
        initialize=1,
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
    
    # Pumping head parameters
    m.fs.static_head = Param(
        initialize=5.0,
        mutable=True,
        units=pyunits.m,
        doc="Static head (elevation difference)"
    )
    m.fs.friction_head = Param(
        initialize=318,
        mutable=True,
        units=pyunits.m/pyunits.km,
        doc="Friction head loss per km"
    )
    
    # Pumping head as a variable
    m.fs.pumping_head = Var(
        initialize=50,
        bounds=(0, None),
        units=pyunits.m,
        doc="Pumping head (m)"
    )
    
    # Constraint to calculate pumping head
    @m.fs.Constraint(doc="Pumping head calculation")
    def eq_pumping_head(b):
        return b.pumping_head == b.static_head + b.friction_head * b.piping_length
    
def define_pond_parameters(m):
    m.fs.pond.evaporation_rate_salinity_adjustment_factor.set_value(0.75)
    m.fs.pond.evaporation_rate_enhancement_adjustment_factor.fix(1.16)
    m.fs.pond.number_evaporation_ponds.fix(300)

def define_flow_and_evaporation(m):
    m.fs.fraction_outflow = Var(
        initialize=0.05,
        bounds=(0.01, 0.99),
        units=pyunits.dimensionless,
        doc="Fraction of water that flows out (not evaporated)"
    )
    m.fs.water_outflow = pyo.Var(
        initialize=0.05,
        bounds=(0, None),
        units=pyunits.kg / pyunits.s,
        doc="Water flow rate in the outflow stream"
    )
    m.fs.fraction_evaporated = Var(
        initialize=0.95,
        bounds=(0.01, 1.0),
        units=pyunits.dimensionless,
        doc="Fraction of water that is evaporated"
    )
    prop_in = m.fs.feed.properties[0]
    def eq_fraction_outflow(b):
        return b.fraction_outflow + b.fraction_evaporated == 1
    m.fs.eq_fraction_outflow = Constraint(rule=eq_fraction_outflow, doc="Fraction of outflow water")
    m.fs.water_evaporated = Expression(expr=prop_in.flow_mass_phase_comp["Liq", "H2O"] * m.fs.fraction_evaporated)
    
    def eq_water_outflow(b):
        return b.water_outflow == prop_in.flow_mass_phase_comp["Liq", "H2O"] * b.fraction_outflow
    m.fs.eq_water_outflow = Constraint(rule=eq_water_outflow, doc="Water outflow mass balance")

def define_tds_section(m):
    m.fs.tds_outflow = Var(
        initialize=0.5,
        bounds=(0, None),
        units=pyunits.kg / pyunits.s,
        doc="TDS flow rate in the outflow stream"
    )
    m.fs.tds_concentration_outflow = Var(
        initialize=1000,
        bounds=(0, None),
        units=pyunits.kg / pyunits.m**3,
        doc="TDS concentration in the outflow stream"
    )
    prop_in = m.fs.feed.properties[0]
    m.fs.tds_precipitated = Expression(expr=pyunits.convert(m.fs.pond.mass_flow_precipitate, to_units=pyunits.kg/pyunits.s))
    def eq_tds_outflow(b):
        return b.tds_outflow == prop_in.flow_mass_phase_comp["Liq", "TDS"] - b.tds_precipitated
    m.fs.eq_tds_outflow = Constraint(rule=eq_tds_outflow, doc="TDS outflow mass balance")
    def eq_tds_concentration_outflow(b):
        return b.tds_concentration_outflow == b.tds_outflow / (b.water_outflow + 1e-12 * pyunits.kg / pyunits.s) * b.rho
    m.fs.eq_tds_concentration_outflow = Constraint(rule=eq_tds_concentration_outflow, doc="TDS concentration in outflow")

def define_lithium_section(m):
    m.fs.target_li_concentration = Param(
        initialize=0.05,
        mutable=True,
        units=pyunits.g / pyunits.kg,
        doc="Target Li+ concentration in outflow"
    )
    m.fs.li_outflow = Var(
        initialize=0.001,
        bounds=(0, None),
        units=pyunits.kg / pyunits.s,
        doc="Lithium flow rate in the outflow stream"
    )
    m.fs.li_concentration_outflow = Var(
        initialize=3.500,
        bounds=(0, None),
        units=pyunits.kg / pyunits.m**3,
        doc="Lithium concentration in the outflow stream"
    )
    prop_in = m.fs.feed.properties[0]
    def eq_li_concentration_outflow(b):
        evap_ratio = b.fraction_evaporated
        a = 88.1606
        b_ = -169.2358
        c = 81.4783
        mass_frac_before = 1.0
        mass_frac_after = a * evap_ratio**2 + b_ * evap_ratio + c
        mass_frac = smooth_min(mass_frac_after, mass_frac_before, eps=1e-3)
        li_in = prop_in.flow_mass_phase_comp["Liq", "Li+"]
        li_out = li_in * mass_frac
        return b.li_concentration_outflow == li_out / (b.water_outflow + 1e-12 * pyunits.kg / pyunits.s) * b.rho
    m.fs.eq_li_concentration_outflow = Constraint(rule=eq_li_concentration_outflow, doc="Li+ outflow and concentration using polynomial mass fraction")
    def eq_li_outflow(b):
        evap_ratio = b.fraction_evaporated
        a = 88.1606
        b_ = -169.2358
        c = 81.4783
        mass_frac_before = 1.0
        mass_frac_after = a * evap_ratio**2 + b_ * evap_ratio + c
        mass_frac = smooth_min(mass_frac_after, mass_frac_before, eps=1e-3)
        li_in = prop_in.flow_mass_phase_comp["Liq", "Li+"]
        return b.li_outflow == li_in * mass_frac
    m.fs.eq_li_outflow = Constraint(rule=eq_li_outflow, doc="Li+ outflow mass flow rate")
    def li_precipitated_expr():
        evap_ratio = m.fs.fraction_evaporated
        a = 88.1606
        b_ = -169.2358
        c = 81.4783
        mass_frac_before = 1.0
        mass_frac_after = a * evap_ratio**2 + b_ * evap_ratio + c
        mass_frac = smooth_min(mass_frac_after, mass_frac_before, eps=1e-3)
        li_in = prop_in.flow_mass_phase_comp["Liq", "Li+"]
        li_out = li_in * mass_frac
        return li_in - li_out
    m.fs.li_precipitated = Expression(expr=li_precipitated_expr())

def define_precipitate_section(m):
    if hasattr(m.fs.pond, 'mass_flow_precipitate'):
        m.fs.pond.del_component('mass_flow_precipitate')
    m.fs.pond.mass_flow_precipitate = Var(
        initialize=1000,
        bounds=(0, None),
        units=pyunits.kg / pyunits.year,
        doc="Annual mass flow of precipitate"
    )
    prop_in = m.fs.feed.properties[0]
    def eq_mass_flow_precipitate(b):
        precipitate_concentration = m.fs.pond.annual_solid_precipitate_a * (1 - m.fs.fraction_evaporated) + m.fs.pond.annual_solid_precipitate_b
        original_water_volume = prop_in.flow_mass_phase_comp["Liq", "H2O"] / m.fs.rho
        annual_mass_flow = pyunits.convert(precipitate_concentration * original_water_volume, to_units=pyunits.kg/pyunits.year)
        return b.mass_flow_precipitate == annual_mass_flow
    m.fs.pond.eq_mass_flow_precipitate = Constraint(rule=eq_mass_flow_precipitate, doc="Annual mass flow of precipitate from concentration and water volume")

def define_brine_outflow_section(m):
    m.fs.concentrated_brine_outflow = Var(
        initialize=1,
        bounds=(0, None),
        units=pyunits.kg / pyunits.second,
        doc="Total concentrated brine outflow for shipping (post-evaporation)"
    )
    def eq_concentrated_brine_outflow(b):
        return b.concentrated_brine_outflow == b.water_outflow + b.tds_outflow + b.li_outflow
    m.fs.eq_concentrated_brine_outflow = Constraint(rule=eq_concentrated_brine_outflow, doc="Concentrated brine outflow for shipping")

def define_evaporative_area_section(m):
    if hasattr(m.fs.pond, 'eq_total_evaporative_area_required'):
        m.fs.pond.eq_total_evaporative_area_required.deactivate()
    def eq_total_evaporative_area_required_partial(b):
        return b.total_evaporative_area_required * b.mass_flux_water_vapor_average == m.fs.water_evaporated * m.fs.pond_overdesign_factor
    m.fs.pond.eq_total_evaporative_area_required_partial = Constraint(rule=eq_total_evaporative_area_required_partial, doc="Total evaporative area required for partial evaporation with overdesign factor")

def define_target_li_concentration_constraint(m):
    # Add variables to break down the complex relationship
    m.fs.li_mass_fraction_after_evap = Var(
        initialize=0.5,
        bounds=(0, 1),
        units=pyunits.dimensionless,
        doc="Lithium mass fraction remaining after evaporation"
    )
    
    m.fs.li_outflow_calc = Var(
        initialize=0.001,
        bounds=(0, None),
        units=pyunits.kg / pyunits.s,
        doc="Calculated lithium outflow for target constraint"
    )
    
    m.fs.water_outflow_calc = Var(
        initialize=0.05,
        bounds=(0, None),
        units=pyunits.kg / pyunits.s,
        doc="Calculated water outflow for target constraint"
    )
    
    # Calculate lithium mass fraction using polynomial
    @m.fs.Constraint(doc="Lithium mass fraction calculation")
    def eq_li_mass_fraction(b):
        a = 88.1606
        b_ = -169.2358
        c = 81.4783
        
        mass_frac_before = 1.0
        mass_frac_after = a * b.fraction_evaporated**2 + b_ * b.fraction_evaporated + c
        return b.li_mass_fraction_after_evap == smooth_min(mass_frac_after, mass_frac_before, eps=1e-3)
    
    # Calculate lithium outflow
    @m.fs.Constraint(doc="Lithium outflow calculation")
    def eq_li_outflow_calc(b):
        prop_in = m.fs.feed.properties[0]
        li_inlet_flow = prop_in.flow_mass_phase_comp["Liq", "Li+"]
        return b.li_outflow_calc == li_inlet_flow * b.li_mass_fraction_after_evap
    
    # Calculate water outflow
    @m.fs.Constraint(doc="Water outflow calculation")
    def eq_water_outflow_calc(b):
        prop_in = m.fs.feed.properties[0]
        water_inlet_flow = prop_in.flow_mass_phase_comp["Liq", "H2O"]
        return b.water_outflow_calc == water_inlet_flow * (1 - b.fraction_evaporated)
    
    # Target lithium concentration constraint (linearized)
    @m.fs.Constraint(doc="Target lithium concentration constraint")
    def eq_target_li_concentration(b):
        return b.li_outflow_calc == b.target_li_concentration * b.water_outflow_calc

def define_additional_constraints(m):
    define_general_parameters(m)
    define_pond_parameters(m)
    define_flow_and_evaporation(m)
    define_tds_section(m)
    define_lithium_section(m)
    define_precipitate_section(m)
    define_brine_outflow_section(m)
    define_evaporative_area_section(m)
    define_target_li_concentration_constraint(m) 