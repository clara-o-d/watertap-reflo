from idaes.core import UnitModelCostingBlock
from watertap_contrib.reflo.costing.watertap_reflo_costing_package import REFLOCosting
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.process_costing import process_costing
from pyomo.environ import Param, Var, Constraint, Expression
from pyomo.environ import units as pyunits
import idaes.core.util.scaling as iscale
from pyomo.environ import value

def add_costing(m):
    m.fs.costing = REFLOCosting()
    m.fs.pond.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)

    # Wellfield capital cost
    m.fs.well_capital_cost = Param(
        initialize=104.65e6 / 379,  # 104.65M total / 320 wells
        mutable=True, units=pyunits.USD_2020,
        doc="Capital cost per extraction well ($/well)"
    )
    m.fs.piping_unit_cost = Param(
        initialize=104.65e6 / 5.0,  # 104.65M total / 5 km = cost per km
        mutable=True, units=pyunits.USD_2020/pyunits.km,
        doc="Piping and pump cost per km ($/km)"
    )
    m.fs.facilities_electrical_unit_cost = Param(
        initialize=86.72e6 / 379,  # 86.72M total / 320 wells = cost per well
        mutable=True, units=pyunits.USD_2020,
        doc="Facilities/electrical cost per well ($/well)"
    )
    m.fs.other_fixed_assets_factor = Param(
        initialize=1.20,
        mutable=True,
        doc="Other fixed assets factor"
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

    # Shipping capital cost
    m.fs.truck_capital_cost = Param(
        initialize=158000,
        mutable=True,
        units=pyunits.USD_2023,
        doc="Truck capital cost"
    )
    m.fs.total_truck_capital_cost = Var(initialize=158000*230, units=m.fs.costing.base_currency, bounds=(0, None), doc="Total truck capital cost")

    @m.fs.Constraint(doc="Total truck capital cost")
    def total_truck_capital_cost_constraint(b):
        return b.total_truck_capital_cost == b.number_of_trucks * b.truck_capital_cost * 1.36 # Indirect cost multiplier

    # Capital cost replacement
    m.fs.pond.costing.total_capital_cost = Expression(
        expr=m.fs.pond.costing.land_capital_cost + 
        m.fs.pond.costing.land_clearing_capital_cost + 
        m.fs.pond.costing.dike_capital_cost + 
        m.fs.pond.costing.liner_capital_cost + 
        m.fs.pond.costing.fence_capital_cost + 
        m.fs.pond.costing.road_capital_cost + 
        m.fs.other_fixed_assets_factor * (
        m.fs.total_well_capital_cost + 
        m.fs.total_piping_pump_capital_cost + 
        m.fs.total_facilities_electrical_capital_cost) +
        m.fs.total_truck_capital_cost,
        doc="Total capital cost (pond + extraction + piping/pumps + facilities)"
    )

    m.fs.pond.costing.capital_cost_constraint.deactivate()
    @m.fs.pond.costing.Constraint(doc="Capital cost for pond + extraction + piping/pumps + facilities")
    def capital_cost_constraint(b):
        return b.capital_cost == b.total_capital_cost

    # Pumping flow variable and constraint
    m.fs.pumping_flow = Var(
        initialize=100000, 
        units=pyunits.m**3/pyunits.year, 
        bounds=(0, None), 
        doc="Pumping volumetric flow rate"
    )

    @m.fs.Constraint(doc="Pumping flow calculation")
    def eq_pumping_flow(b):
        return b.pumping_flow == pyunits.convert(
            (b.feed.properties[0].flow_mass_phase_comp["Liq", "H2O"] + 
             b.feed.properties[0].flow_mass_phase_comp["Liq", "TDS"]) / b.rho, 
            to_units=pyunits.m**3/pyunits.year
        )

    m.fs.pumping_power = Var(
        initialize=0.1,
        bounds=(0, None),
        units=pyunits.kW,
        doc="Mechanical power for pumping"
    )

    @m.fs.Constraint(doc="Pumping power calculation")
    def eq_pumping_power(b):
        work_per_m3 = pyunits.convert(
            9.81 * pyunits.m/pyunits.s**2 * b.pumping_head * b.rho / b.pumping_efficiency, 
            to_units=pyunits.kWh/pyunits.m**3
        )
        return b.pumping_power == work_per_m3 * b.pumping_flow / pyunits.convert(1 * pyunits.year, to_units=pyunits.hr)

    m.fs.costing.cost_flow(m.fs.pumping_power, "electricity")

    # Shipping flow cost
    m.fs.shipping_unit_cost = Param(
        initialize=6.4e-5, # 1.28e-4 USD_2022/kg/km
        mutable=True,
        units=pyunits.USD_2022/pyunits.kg/pyunits.km,
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
    
    # Fix costing parameters
    m.fs.costing.plant_lifetime.fix(35)
    m.fs.costing.wacc.fix(0.10) # capital_recovery_factor = 0.10368970512
    m.fs.costing.electricity_cost.fix(value(pyunits.convert(0.15 * pyunits.USD_2023 / pyunits.kWh, to_units=m.fs.costing.base_currency / pyunits.kWh)))
    m.fs.costing.electrical_carbon_intensity.fix(0.229)
    m.fs.costing.utilization_factor.fix(0.98)

    m.fs.costing.evaporation_pond.liner_thickness.fix(40)
    m.fs.costing.recovered_solids.cost.set_value(value(pyunits.convert(-0.01 * pyunits.USD_2020 / pyunits.kg, to_units=pyunits.USD_2023 / pyunits.kg)))
    m.fs.costing.evaporation_pond.recovered_solids_handling_cost.fix(value(pyunits.convert(0.01 * pyunits.USD_2020 / pyunits.kg, to_units=pyunits.USD_2020 / pyunits.kg)))
    m.fs.costing.evaporation_pond.enhancement_dose_basis.fix(0)
    m.fs.costing.evaporation_pond.land_clearing_cost.fix(2000)
    m.fs.costing.evaporation_pond.fence_capital_cost_base.fix(0)

    process_costing(m)