"""Costing module for lithium processing flowsheet.

Adds capital and operating costs for:
- Storage tank
- Pump
- Soda ash reactor (first softening stage)
- Lime reactor (second softening stage)
- Lithium carbonate reactor
- Soda ash dewatering unit (RDVF - custom implementation)
- Soda ash centrifuge unit (centrifuge)
- Lime press filter unit (belt filter press)
- Lime centrifuge unit (centrifuge)
- Lithium dewatering unit (belt filter press)
"""

from idaes.core import UnitModelCostingBlock
from watertap_contrib.reflo.costing.watertap_reflo_costing_package import REFLOCosting
from watertap.costing.unit_models.dewatering import cost_dewatering, DewateringType
from watertap.costing.util import make_capital_cost_var
from pyomo.environ import Param, Var, Expression, Constraint, Block
from pyomo.environ import units as pyunits
from pyomo.environ import value
from idaes.core.util.model_statistics import degrees_of_freedom

def build_rdvf_cost_params(costing_package):
    if not hasattr(costing_package, 'rdvf'):
        costing_package.rdvf = Block()
        
        costing_package.rdvf.capital_a_parameter = Var(
            initialize=2.31,
            doc="A parameter for capital cost",
            units=pyunits.dimensionless,
        )
        costing_package.rdvf.capital_a_parameter.fix()
        
        costing_package.rdvf.drum_unit_cost = Var(
            initialize=27500,
            doc="Unit cost per drum",
            units=pyunits.USD_2007,
        )
        costing_package.rdvf.drum_unit_cost.fix()

def cost_rdvf_custom(blk, number_of_drums=2, cost_electricity_flow=True):
    """Custom RDVF costing method for soda ash dewatering unit."""
    build_rdvf_cost_params(blk.costing_package)
    
    make_capital_cost_var(blk)
    blk.costing_package.add_cost_factor(blk, "TIC")
    cost_blk = blk.costing_package.rdvf
    t0 = blk.flowsheet().time.first()
    
    blk.number_of_drums = Param(
        initialize=number_of_drums,
        mutable=True,
        doc="Number of drums",
        units=pyunits.dimensionless,
    )
    
    blk.capital_cost_constraint = Constraint(
        expr=blk.capital_cost
        == blk.cost_factor
        * pyunits.convert(
            cost_blk.capital_a_parameter * blk.number_of_drums * cost_blk.drum_unit_cost,
            to_units=blk.costing_package.base_currency,
        )
    )
    
    if cost_electricity_flow:
        blk.costing_package.cost_flow(
            pyunits.convert(
                blk.unit_model.electricity_consumption[t0],
                to_units=pyunits.kW,
            ),
            "electricity",
        )

def make_rdvf_costing_method(number_of_drums=2, cost_electricity_flow=True):
    def costing_method(blk):
        cost_rdvf_custom(blk, number_of_drums, cost_electricity_flow)
    return costing_method

def add_flow_costs(m):
    if hasattr(m.fs.brine_pump.control_volume, 'work'):
        original_lb = m.fs.brine_pump.control_volume.work[0].lb
        m.fs.brine_pump.control_volume.work[0].setlb(0)
    
    if hasattr(m.fs.soda_ash_reactor, 'flow_mass_reagent'):
        if "Na2CO3" in m.fs.soda_ash_reactor.flow_mass_reagent:
            original_lb = m.fs.soda_ash_reactor.flow_mass_reagent["Na2CO3"].lb
            m.fs.soda_ash_reactor.flow_mass_reagent["Na2CO3"].setlb(0)
    
    if hasattr(m.fs.lime_reactor, 'flow_mass_reagent'):
        if "CaO" in m.fs.lime_reactor.flow_mass_reagent:
            original_lb = m.fs.lime_reactor.flow_mass_reagent["CaO"].lb
            m.fs.lime_reactor.flow_mass_reagent["CaO"].setlb(0)
    
    if hasattr(m.fs.lithium_carbonate_reactor, 'flow_mass_reagent'):
        if "Na2CO3" in m.fs.lithium_carbonate_reactor.flow_mass_reagent:
            original_lb = m.fs.lithium_carbonate_reactor.flow_mass_reagent["Na2CO3"].lb
            m.fs.lithium_carbonate_reactor.flow_mass_reagent["Na2CO3"].setlb(0)
    
    m.fs.costing.cost_flow(m.fs.brine_pump.control_volume.work[0], "electricity")
    
    if hasattr(m.fs.soda_ash_vacuum_filter, 'electricity_consumption'):
        m.fs.soda_ash_vacuum_filter.electricity_consumption[0].setlb(0)
        m.fs.costing.cost_flow(m.fs.soda_ash_vacuum_filter.electricity_consumption[0], "electricity")
    
    if hasattr(m.fs.soda_ash_centrifuge, 'electricity_consumption'):
        m.fs.soda_ash_centrifuge.electricity_consumption[0].setlb(0)
        m.fs.costing.cost_flow(m.fs.soda_ash_centrifuge.electricity_consumption[0], "electricity")
    
    if hasattr(m.fs.lime_press_filter, 'electricity_consumption'):
        m.fs.lime_press_filter.electricity_consumption[0].setlb(0)
        m.fs.costing.cost_flow(m.fs.lime_press_filter.electricity_consumption[0], "electricity")
    
    if hasattr(m.fs.lime_centrifuge, 'electricity_consumption'):
        m.fs.lime_centrifuge.electricity_consumption[0].setlb(0)
        m.fs.costing.cost_flow(m.fs.lime_centrifuge.electricity_consumption[0], "electricity")
    
    if hasattr(m.fs.li_dewatering, 'electricity_consumption'):
        m.fs.li_dewatering.electricity_consumption[0].setlb(0)
        m.fs.costing.cost_flow(m.fs.li_dewatering.electricity_consumption[0], "electricity")
    
    m.fs.soda_ash_cost = Param(
        initialize=0.5,
        mutable=True,
        units=pyunits.USD_2023/pyunits.kg,
        doc="Soda ash (Na2CO3) cost per kg"
    )
    
    m.fs.lime_cost = Param(
        initialize=0.3,
        mutable=True,
        units=pyunits.USD_2023/pyunits.kg,
        doc="Lime (CaO) cost per kg"
    )
    
    m.fs.process_water_cost = Param(
        initialize=0.001,
        mutable=True,
        units=pyunits.USD_2023/pyunits.kg,
        doc="Process water cost per kg"
    )
    
    m.fs.costing.register_flow_type("soda_ash", m.fs.soda_ash_cost)
    m.fs.costing.register_flow_type("lime", m.fs.lime_cost)
    m.fs.costing.register_flow_type("process_water", m.fs.process_water_cost)
    
    m.fs.costing.cost_flow(m.fs.soda_ash_reactor.flow_mass_reagent["Na2CO3"], "soda_ash")
    if "H2O" in m.fs.soda_ash_reactor.flow_mass_reagent:
        m.fs.costing.cost_flow(m.fs.soda_ash_reactor.flow_mass_reagent["H2O"], "process_water")
    
    m.fs.costing.cost_flow(m.fs.lime_reactor.flow_mass_reagent["Ca(OH)2"], "lime")
    if "H2O" in m.fs.lime_reactor.flow_mass_reagent:
        m.fs.costing.cost_flow(m.fs.lime_reactor.flow_mass_reagent["H2O"], "process_water")
    
    m.fs.costing.cost_flow(m.fs.lithium_carbonate_reactor.flow_mass_reagent["Na2CO3"], "soda_ash")
    if "H2O" in m.fs.lithium_carbonate_reactor.flow_mass_reagent:
        m.fs.costing.cost_flow(m.fs.lithium_carbonate_reactor.flow_mass_reagent["H2O"], "process_water")

def add_costing(m):
    """Add costing blocks to all unit models and register flow costs."""
    m.fs.costing = REFLOCosting()
    m.fs.costing.base_currency = pyunits.USD_2023

    m.fs.brine_storage.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)
    m.fs.brine_pump.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)
    
    if hasattr(m.fs, 'soda_ash_reactor'):
        m.fs.soda_ash_reactor.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)
        m.fs.lime_reactor.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)
        m.fs.lithium_carbonate_reactor.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)
    
    if hasattr(m.fs, 'soda_ash_vacuum_filter'):
        m.fs.lime_press_filter.costing = UnitModelCostingBlock(
            flowsheet_costing_block=m.fs.costing,
            costing_method=cost_dewatering,
            costing_method_arguments={
                "dewatering_type": DewateringType.filter_plate_press,
                "cost_electricity_flow": True,
            },
        )
        
        m.fs.lime_centrifuge.costing = UnitModelCostingBlock(
            flowsheet_costing_block=m.fs.costing,
            costing_method=cost_dewatering,
            costing_method_arguments={
                "dewatering_type": DewateringType.centrifuge,
                "cost_electricity_flow": True,
            },
        )
        
        m.fs.soda_ash_vacuum_filter.costing = UnitModelCostingBlock(
            flowsheet_costing_block=m.fs.costing,
            costing_method=make_rdvf_costing_method(
                number_of_drums=2,
                cost_electricity_flow=True,
            ),
        )
        
        m.fs.soda_ash_centrifuge.costing = UnitModelCostingBlock(
            flowsheet_costing_block=m.fs.costing,
            costing_method=cost_dewatering,
            costing_method_arguments={
                "dewatering_type": DewateringType.centrifuge,
                "cost_electricity_flow": True,
            },
        )
        
        m.fs.li_dewatering.costing = UnitModelCostingBlock(
            flowsheet_costing_block=m.fs.costing,
            costing_method=cost_dewatering,
            costing_method_arguments={
                "dewatering_type": DewateringType.filter_belt_press,
                "cost_electricity_flow": True,
            },
        )
    
    add_flow_costs(m)
    
    m.fs.costing.plant_lifetime.fix(35)
    m.fs.costing.wacc.fix(0.10)
    m.fs.costing.electricity_cost.fix(value(pyunits.convert(0.15 * pyunits.USD_2023 / pyunits.kWh, to_units=m.fs.costing.base_currency / pyunits.kWh)))
    m.fs.costing.electrical_carbon_intensity.fix(0.229)
    m.fs.costing.utilization_factor.fix(0.98)

    dof = degrees_of_freedom(m)
    if dof != 0:
        print(f"Warning: {dof} degrees of freedom remaining after costing setup")
    else:
        print("All variables properly fixed after costing setup")
