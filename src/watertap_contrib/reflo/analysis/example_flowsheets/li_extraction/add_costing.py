from idaes.core import UnitModelCostingBlock
from watertap_contrib.reflo.costing.watertap_reflo_costing_package import REFLOCosting
from pyomo.environ import Param, Var, Constraint, Expression
from pyomo.environ import units as pyunits
import idaes.core.util.scaling as iscale
from pyomo.environ import value

def add_costing(m):
    m.fs.costing = REFLOCosting()
    m.fs.pond.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)

    # Wellfield capital cost
    m.fs.well_capital_cost = Param(
        initialize=104.65e6 / 320,  # 104.65M total / 320 wells
        mutable=True, units=m.fs.costing.base_currency,
        doc="Capital cost per extraction well ($/well)"
    )
    m.fs.piping_length = Param(
        initialize=10.0,  # Updated to 10 km average distance
        mutable=True,
        units=pyunits.km,
        doc="Piping length from wells to pond (km)"
    )
    m.fs.piping_unit_cost = Param(
        initialize=104.65e6 / 10.0,  # 104.65M total / 10 km = cost per km
        mutable=True, units=m.fs.costing.base_currency/pyunits.km,
        doc="Piping and pump cost per km ($/km)"
    )
    m.fs.facilities_electrical_unit_cost = Param(
        initialize=86.72e6 / 320,  # 86.72M total / 320 wells = cost per well
        mutable=True, units=m.fs.costing.base_currency,
        doc="Facilities/electrical cost per well ($/well)"
    )

    m.fs.total_well_capital_cost = Var(initialize=104.65e6, units=m.fs.costing.base_currency, bounds=(0, None), doc="Total wellfield capital cost")
    m.fs.total_piping_pump_capital_cost = Var(initialize=104.65e6, units=m.fs.costing.base_currency, bounds=(0, None), doc="Total piping and pump capital cost")
    m.fs.total_facilities_electrical_capital_cost = Var(initialize=86.72e6, units=m.fs.costing.base_currency, bounds=(0, None), doc="Total facilities/electrical capital cost")

    @m.fs.Constraint(doc="Total wellfield capital cost")
    def total_well_capital_cost_constraint(b):
        return b.total_well_capital_cost == b.number_of_wells * b.well_capital_cost
    
    @m.fs.Constraint(doc="Total piping and pump capital cost")
    def total_piping_pump_capital_cost_constraint(b):
        return b.total_piping_pump_capital_cost == b.piping_length * b.piping_unit_cost
    
    @m.fs.Constraint(doc="Total facilities/electrical capital cost")
    def total_facilities_electrical_capital_cost_constraint(b):
        return b.total_facilities_electrical_capital_cost == b.number_of_wells * b.facilities_electrical_unit_cost

    # Capital cost replacement
    m.fs.pond.costing.total_capital_cost = Expression(
        expr=m.fs.pond.costing.land_capital_cost + 
        m.fs.pond.costing.land_clearing_capital_cost + 
        m.fs.pond.costing.dike_capital_cost + 
        m.fs.pond.costing.liner_capital_cost + 
        m.fs.pond.costing.fence_capital_cost + 
        m.fs.pond.costing.road_capital_cost + 
        m.fs.total_well_capital_cost + 
        m.fs.total_piping_pump_capital_cost + 
        m.fs.total_facilities_electrical_capital_cost,
        doc="Total capital cost (pond + extraction + piping/pumps + facilities)"
    )

    m.fs.pond.costing.capital_cost_constraint.deactivate()
    @m.fs.pond.costing.Constraint(doc="Capital cost for pond + extraction + piping/pumps + facilities")
    def capital_cost_constraint(b):
        return b.capital_cost == b.total_capital_cost

    # Pumping flow variable and constraint
    m.fs.pumping_flow = Var(initialize=100000, units=pyunits.m**3/pyunits.year, bounds=(0, None), doc="Pumping mass flow rate")

    @m.fs.Constraint(doc="Pumping flow calculation")
    def eq_pumping_flow(b):
        return b.pumping_flow == pyunits.convert((b.feed.properties[0].flow_mass_phase_comp["Liq", "H2O"] + b.feed.properties[0].flow_mass_phase_comp["Liq", "TDS"]) / b.rho, to_units=pyunits.m**3/pyunits.year)

    # Pumping unit cost as a variable with constraint
    m.fs.pumping_unit_cost = Var(
        initialize=0.1,
        bounds=(0, None),
        units=m.fs.costing.base_currency/pyunits.m**3,
        doc="Pumping cost per m³"
    )

    @m.fs.Constraint(doc="Pumping unit cost calculation")
    def eq_pumping_unit_cost(b):
        # Calculate energy required per m³: (head * g * density) / efficiency
        energy_per_m3 = pyunits.convert(9.81 * pyunits.m/pyunits.s**2 * b.pumping_head * b.rho / b.pumping_efficiency, to_units=pyunits.kWh/pyunits.m**3)
        # Convert to cost per m³: energy * electricity_cost
        return b.pumping_unit_cost == energy_per_m3 * b.costing.electricity_cost

    m.fs.costing.register_flow_type("pumping", m.fs.pumping_unit_cost)
    m.fs.costing.cost_flow(m.fs.pumping_flow, "pumping")

    # Shipping flow cost
    m.fs.shipping_unit_cost = Param(
        initialize=3e-5, mutable=True, units=m.fs.costing.base_currency/pyunits.kg/pyunits.km,
        doc="Shipping cost per kg per km ($/kg/km)"
    )

    m.fs.annual_concentrated_brine_outflow = Var(
        initialize=1e7,
        bounds=(0, None),
        units=pyunits.kg / pyunits.year,
        doc="Annual total concentrated brine outflow for shipping (post-evaporation)"
    )

    @m.fs.Constraint(doc="Annual concentrated brine outflow for shipping")
    def eq_annual_concentrated_brine_outflow(b):
        return b.annual_concentrated_brine_outflow == pyunits.convert(b.concentrated_brine_outflow, to_units=pyunits.kg/pyunits.year)

    m.fs.shipping_cost = Expression(
        expr=m.fs.shipping_distance * m.fs.shipping_unit_cost,
        doc="Shipping cost per kg (as Expression)"
    )
    m.fs.costing.register_flow_type("shipping", m.fs.shipping_cost)
    m.fs.costing.cost_flow(m.fs.annual_concentrated_brine_outflow, "shipping")

    iscale.calculate_scaling_factors(m)
    
    # Fix global costing parameters
    m.fs.costing.plant_lifetime.fix(35)
    m.fs.costing.wacc.fix(0.07)
    m.fs.costing.electricity_cost.fix(0.16)
    m.fs.costing.electrical_carbon_intensity.fix(0.229)
    m.fs.costing.utilization_factor.fix(0.98)
    m.fs.costing.maintenance_labor_chemical_factor.fix(0.01) 