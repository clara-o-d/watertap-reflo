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

import yaml
from pathlib import Path
from idaes.core import UnitModelCostingBlock
from watertap_contrib.reflo.costing.watertap_reflo_costing_package import REFLOCosting
from watertap.costing.unit_models.dewatering import cost_dewatering, DewateringType
from watertap.costing.util import make_capital_cost_var
from pyomo.environ import Param, Var, Expression, Constraint, Block
from pyomo.environ import units as pyunits
from pyomo.environ import value
from idaes.core.util.model_statistics import degrees_of_freedom

def load_costing_parameters(yaml_path=None):
    """Load costing parameters from YAML file."""
    if yaml_path is None:
        yaml_path = Path(__file__).parent / "costing_parameters.yaml"
    else:
        yaml_path = Path(yaml_path)
    
    with open(yaml_path, 'r') as f:
        params = yaml.safe_load(f)
    return params

def build_rdvf_cost_params(costing_package, params=None):
    if params is None:
        params = load_costing_parameters()
    rdvf_params = params['rdvf']
    
    if not hasattr(costing_package, 'rdvf'):
        costing_package.rdvf = Block()
        
        costing_package.rdvf.capital_a_parameter = Var(
            initialize=rdvf_params['capital_a_parameter'],
            doc="A parameter for capital cost",
            units=pyunits.dimensionless,
        )
        costing_package.rdvf.capital_a_parameter.fix()
        
        costing_package.rdvf.drum_unit_cost = Var(
            initialize=rdvf_params['drum_unit_cost'],
            doc="Unit cost per drum",
            units=pyunits.USD_2007,
        )
        costing_package.rdvf.drum_unit_cost.fix()

def cost_rdvf_custom(blk, number_of_drums=2, cost_electricity_flow=True, params=None):
    """Custom RDVF costing method for soda ash dewatering unit."""
    if params is None:
        params = load_costing_parameters()
    build_rdvf_cost_params(blk.costing_package, params)
    
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

def make_rdvf_costing_method(number_of_drums=2, cost_electricity_flow=True, params=None):
    if params is None:
        params = load_costing_parameters()
    rdvf_params = params['rdvf']
    number_of_drums = rdvf_params.get('number_of_drums', number_of_drums)
    cost_electricity_flow = rdvf_params.get('cost_electricity_flow', cost_electricity_flow)
    
    def costing_method(blk):
        cost_rdvf_custom(blk, number_of_drums, cost_electricity_flow, params)
    return costing_method

def add_flow_costs(m, params=None):
    if params is None:
        params = load_costing_parameters()
    flow_costs = params['flow_costs']
    
    if hasattr(m.fs.brine_pump.control_volume, 'work'):
        original_lb = m.fs.brine_pump.control_volume.work[0].lb
        m.fs.brine_pump.control_volume.work[0].setlb(0)
    
    if hasattr(m.fs, 'soda_ash_reactor'):
        if "Na2CO3" in m.fs.soda_ash_reactor.flow_mass_reagent:
            original_lb = m.fs.soda_ash_reactor.flow_mass_reagent["Na2CO3"].lb
            m.fs.soda_ash_reactor.flow_mass_reagent["Na2CO3"].setlb(0)
    
    if hasattr(m.fs, 'lime_reactor'):
        if "CaO" in m.fs.lime_reactor.flow_mass_reagent:
            original_lb = m.fs.lime_reactor.flow_mass_reagent["CaO"].lb
            m.fs.lime_reactor.flow_mass_reagent["CaO"].setlb(0)
    
    if hasattr(m.fs, 'lithium_carbonate_reactor'):
        if "Na2CO3" in m.fs.lithium_carbonate_reactor.flow_mass_reagent:
            original_lb = m.fs.lithium_carbonate_reactor.flow_mass_reagent["Na2CO3"].lb
            m.fs.lithium_carbonate_reactor.flow_mass_reagent["Na2CO3"].setlb(0)
    
    m.fs.costing.cost_flow(m.fs.brine_pump.control_volume.work[0], "electricity")
    
    if hasattr(m.fs, 'soda_ash_vacuum_filter'):
        m.fs.soda_ash_vacuum_filter.electricity_consumption[0].setlb(0)
        m.fs.costing.cost_flow(m.fs.soda_ash_vacuum_filter.electricity_consumption[0], "electricity")
    
    if hasattr(m.fs, 'soda_ash_centrifuge'):
        m.fs.soda_ash_centrifuge.electricity_consumption[0].setlb(0)
        m.fs.costing.cost_flow(m.fs.soda_ash_centrifuge.electricity_consumption[0], "electricity")
    
    if hasattr(m.fs, 'lime_press_filter'):
        m.fs.lime_press_filter.electricity_consumption[0].setlb(0)
        m.fs.costing.cost_flow(m.fs.lime_press_filter.electricity_consumption[0], "electricity")
    
    if hasattr(m.fs, 'lime_centrifuge'):
        m.fs.lime_centrifuge.electricity_consumption[0].setlb(0)
        m.fs.costing.cost_flow(m.fs.lime_centrifuge.electricity_consumption[0], "electricity")
    
    if hasattr(m.fs, 'li_dewatering'):
        m.fs.li_dewatering.electricity_consumption[0].setlb(0)
        m.fs.costing.cost_flow(m.fs.li_dewatering.electricity_consumption[0], "electricity")
    
    m.fs.soda_ash_cost = Param(
        initialize=flow_costs['soda_ash_cost'],
        mutable=True,
        units=pyunits.USD_2023/pyunits.kg,
        doc="Soda ash (Na2CO3) cost per kg"
    )
    
    m.fs.lime_cost = Param(
        initialize=flow_costs['lime_cost'],
        mutable=True,
        units=pyunits.USD_2023/pyunits.kg,
        doc="Lime (CaO) cost per kg"
    )
    
    m.fs.process_water_cost = Param(
        initialize=flow_costs['process_water_cost'],
        mutable=True,
        units=pyunits.USD_2023/pyunits.kg,
        doc="Process water cost per kg"
    )
    
    m.fs.costing.register_flow_type("soda_ash", m.fs.soda_ash_cost)
    m.fs.costing.register_flow_type("lime", m.fs.lime_cost)
    m.fs.costing.register_flow_type("process_water", m.fs.process_water_cost)
    
    if hasattr(m.fs, 'soda_ash_reactor'):
        m.fs.costing.cost_flow(m.fs.soda_ash_reactor.flow_mass_reagent["Na2CO3"], "soda_ash")
        if "H2O" in m.fs.soda_ash_reactor.flow_mass_reagent:
            m.fs.costing.cost_flow(m.fs.soda_ash_reactor.flow_mass_reagent["H2O"], "process_water")
    
    if hasattr(m.fs, 'lime_reactor'):
        m.fs.costing.cost_flow(m.fs.lime_reactor.flow_mass_reagent["Ca(OH)2"], "lime")
        if "H2O" in m.fs.lime_reactor.flow_mass_reagent:
            m.fs.costing.cost_flow(m.fs.lime_reactor.flow_mass_reagent["H2O"], "process_water")
    
    if hasattr(m.fs, 'lithium_carbonate_reactor'):
        m.fs.costing.cost_flow(m.fs.lithium_carbonate_reactor.flow_mass_reagent["Na2CO3"], "soda_ash")
        if "H2O" in m.fs.lithium_carbonate_reactor.flow_mass_reagent:
            m.fs.costing.cost_flow(m.fs.lithium_carbonate_reactor.flow_mass_reagent["H2O"], "process_water")

def build_reactor_cost_params(costing_package, params=None):
    """Build cost parameters for reactor capital cost correlation C_cap = a + b*V^n"""
    if params is None:
        params = load_costing_parameters()
    reactor_params = params['reactor_cost']
    
    if not hasattr(costing_package, 'reactor_cost_params'):
        costing_package.reactor_cost_params = Block()
        
        costing_package.reactor_cost_params.capital_a_parameter = Var(
            initialize=reactor_params['capital_a_parameter'],
            doc="Fixed cost parameter (a) in reactor capital cost correlation",
            units=pyunits.USD_2023,
        )
        costing_package.reactor_cost_params.capital_a_parameter.fix()
        
        costing_package.reactor_cost_params.capital_b_parameter = Var(
            initialize=reactor_params['capital_b_parameter'],
            doc="Variable cost parameter (b) in reactor capital cost correlation",
            units=pyunits.USD_2023 / (pyunits.m**3)**0.6,
        )
        costing_package.reactor_cost_params.capital_b_parameter.fix()
        
        costing_package.reactor_cost_params.capital_n_exponent = Var(
            initialize=reactor_params['capital_n_exponent'],
            doc="Exponent (n) in reactor capital cost correlation",
            units=pyunits.dimensionless,
        )
        costing_package.reactor_cost_params.capital_n_exponent.fix()

def add_costing(m, yaml_path=None):
    """Add costing blocks to all unit models and register flow costs."""
    params = load_costing_parameters(yaml_path)
    general_params = params['general']
    
    m.fs.costing = REFLOCosting()
    m.fs.costing.base_currency = pyunits.USD_2023
    
    build_reactor_cost_params(m.fs.costing, params)

    m.fs.brine_storage.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)
    m.fs.brine_pump.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)
    
    if hasattr(m.fs, 'soda_ash_reactor'):
        m.fs.soda_ash_reactor.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)
    
    if hasattr(m.fs, 'lime_reactor'):
        m.fs.lime_reactor.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)
    
    if hasattr(m.fs, 'lithium_carbonate_reactor'):
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
            costing_method=make_rdvf_costing_method(params=params),
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
    
    add_flow_costs(m, params)
    
    for reactor_name in ['soda_ash_reactor', 'lime_reactor', 'lithium_carbonate_reactor']:
        if hasattr(m.fs, reactor_name):
            reactor = getattr(m.fs, reactor_name)
            if hasattr(reactor, 'costing') and hasattr(reactor.costing, 'capital_cost_constraint'):
                print(f"Replacing capital cost constraint for {reactor_name} with volume-based correlation")
                blk = reactor.costing
                
                blk.capital_cost_constraint.deactivate()
                
                if hasattr(reactor, 'reactor_volume'):
                    blk.capital_cost_constraint_volume = Constraint(
                        expr=blk.capital_cost
                        == blk.cost_factor
                        * (
                            blk.costing_package.reactor_cost_params.capital_a_parameter
                            + blk.costing_package.reactor_cost_params.capital_b_parameter
                            * pyunits.convert(reactor.reactor_volume, to_units=pyunits.m**3)
                            ** blk.costing_package.reactor_cost_params.capital_n_exponent
                        )
                    )
                    print(f"  → Volume-based cost constraint created for {reactor_name}")
                else:
                    print(f"  → Warning: reactor_volume not found for {reactor_name}, keeping original constraint")
                    blk.capital_cost_constraint.activate()
    
    m.fs.costing.plant_lifetime.fix(general_params['plant_lifetime'])
    m.fs.costing.wacc.fix(general_params['wacc'])
    m.fs.costing.electricity_cost.fix(value(pyunits.convert(general_params['electricity_cost'] * pyunits.USD_2023 / pyunits.kWh, to_units=m.fs.costing.base_currency / pyunits.kWh)))
    m.fs.costing.electrical_carbon_intensity.fix(general_params['electrical_carbon_intensity'])
    m.fs.costing.utilization_factor.fix(general_params['utilization_factor'])

    dof = degrees_of_freedom(m)
    if dof != 0:
        print(f"Warning: {dof} degrees of freedom remaining after costing setup")
    else:
        print("All variables properly fixed after costing setup")
