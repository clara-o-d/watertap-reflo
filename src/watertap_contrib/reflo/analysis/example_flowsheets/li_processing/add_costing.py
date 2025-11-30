"""Costing module for lithium processing flowsheet.

Adds capital and operating costs for:
- Storage tank
- Pump
- Soda ash reactor (first softening stage)
- Lime reactor (second softening stage)
- Lithium carbonate reactor
- Soda ash dewatering unit (RDVF - custom implementation)
- Soda ash centrifuge unit (centrifuge)
- Lime dewatering unit (belt filter press)
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
    """Build RDVF cost parameters on the costing package if they don't exist.
    
    Args:
        costing_package: The flowsheet costing package
    """
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
    """Custom RDVF costing method for soda ash dewatering.
    
    This function applies Rotary Drum Vacuum Filter (RDVF) costing methodology
    directly to a dewatering unit's costing block without modifying the 
    watertap dewatering.py file.
    
    Args:
        blk: The unit model costing block (e.g., soda_ash_dewatering.costing)
        number_of_drums: Number of drums for RDVF (default: 2)
        cost_electricity_flow: Whether to cost electricity flow (default: True)
    """
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
    """Factory function to create an RDVF costing method with specific parameters.
    
    Args:
        number_of_drums: Number of drums for RDVF (default: 2)
        cost_electricity_flow: Whether to cost electricity flow (default: True)
        
    Returns:
        A costing method function that can be passed to UnitModelCostingBlock
    """
    def costing_method(blk):
        cost_rdvf_custom(blk, number_of_drums, cost_electricity_flow)
    return costing_method

def add_flow_costs(m):
    """Add flow costs to the lithium processing flowsheet.
    
    Args:
        m: Pyomo model to add flow costs to
    """
    # Fix flow bounds to avoid negative cost warnings
    # Pump work - set lower bound to 0 for costing
    if hasattr(m.fs.brine_pump.control_volume, 'work'):
        original_lb = m.fs.brine_pump.control_volume.work[0].lb
        m.fs.brine_pump.control_volume.work[0].setlb(0)
    
    # Reagent flows - set lower bounds to 0 for costing
    # Soda ash reactor
    if hasattr(m.fs.soda_ash_reactor, 'flow_mass_reagent'):
        if "Na2CO3" in m.fs.soda_ash_reactor.flow_mass_reagent:
            original_lb = m.fs.soda_ash_reactor.flow_mass_reagent["Na2CO3"].lb
            m.fs.soda_ash_reactor.flow_mass_reagent["Na2CO3"].setlb(0)
    
    # Lime reactor
    if hasattr(m.fs.lime_reactor, 'flow_mass_reagent'):
        if "CaO" in m.fs.lime_reactor.flow_mass_reagent:
            original_lb = m.fs.lime_reactor.flow_mass_reagent["CaO"].lb
            m.fs.lime_reactor.flow_mass_reagent["CaO"].setlb(0)
    
    if hasattr(m.fs.lithium_carbonate_reactor, 'flow_mass_reagent'):
        if "Na2CO3" in m.fs.lithium_carbonate_reactor.flow_mass_reagent:
            original_lb = m.fs.lithium_carbonate_reactor.flow_mass_reagent["Na2CO3"].lb
            m.fs.lithium_carbonate_reactor.flow_mass_reagent["Na2CO3"].setlb(0)
    
    # Pump electricity cost
    m.fs.costing.cost_flow(m.fs.brine_pump.control_volume.work[0], "electricity")
    
    # Soda ash dewatering unit electricity cost
    if hasattr(m.fs.soda_ash_dewatering, 'electricity_consumption'):
        m.fs.soda_ash_dewatering.electricity_consumption[0].setlb(0)
        m.fs.costing.cost_flow(m.fs.soda_ash_dewatering.electricity_consumption[0], "electricity")
    
    # Soda ash centrifuge dewatering unit electricity cost
    if hasattr(m.fs.soda_ash_centrifuge, 'electricity_consumption'):
        m.fs.soda_ash_centrifuge.electricity_consumption[0].setlb(0)
        m.fs.costing.cost_flow(m.fs.soda_ash_centrifuge.electricity_consumption[0], "electricity")
    
    # Softening dewatering unit electricity cost
    if hasattr(m.fs.lime_dewatering, 'electricity_consumption'):
        m.fs.lime_dewatering.electricity_consumption[0].setlb(0)
        m.fs.costing.cost_flow(m.fs.lime_dewatering.electricity_consumption[0], "electricity")
    
    # Centrifuge dewatering unit electricity cost
    if hasattr(m.fs.lime_centrifuge, 'electricity_consumption'):
        m.fs.lime_centrifuge.electricity_consumption[0].setlb(0)
        m.fs.costing.cost_flow(m.fs.lime_centrifuge.electricity_consumption[0], "electricity")
    
    # Lithium dewatering unit electricity cost
    if hasattr(m.fs.li_dewatering, 'electricity_consumption'):
        m.fs.li_dewatering.electricity_consumption[0].setlb(0)
        m.fs.costing.cost_flow(m.fs.li_dewatering.electricity_consumption[0], "electricity")
    
    # Reagent costs
    m.fs.soda_ash_cost = Param(
        initialize=0.5,  # USD_2023/kg
        mutable=True,
        units=pyunits.USD_2023/pyunits.kg,
        doc="Soda ash (Na2CO3) cost per kg"
    )
    
    m.fs.lime_cost = Param(
        initialize=0.3,  # USD_2023/kg
        mutable=True,
        units=pyunits.USD_2023/pyunits.kg,
        doc="Lime (CaO) cost per kg"
    )
    
    m.fs.process_water_cost = Param(
        initialize=0.001,  # USD_2023/kg (approximately $1/m³)
        mutable=True,
        units=pyunits.USD_2023/pyunits.kg,
        doc="Process water cost per kg"
    )
    
    # Register reagent flow types
    m.fs.costing.register_flow_type("soda_ash", m.fs.soda_ash_cost)
    m.fs.costing.register_flow_type("lime", m.fs.lime_cost)
    m.fs.costing.register_flow_type("process_water", m.fs.process_water_cost)
    
    # Cost reagent flows for soda ash reactor
    m.fs.costing.cost_flow(m.fs.soda_ash_reactor.flow_mass_reagent["Na2CO3"], "soda_ash")
    if "H2O" in m.fs.soda_ash_reactor.flow_mass_reagent:
        m.fs.costing.cost_flow(m.fs.soda_ash_reactor.flow_mass_reagent["H2O"], "process_water")
    
    # Cost reagent flows for lime reactor
    m.fs.costing.cost_flow(m.fs.lime_reactor.flow_mass_reagent["Ca(OH)2"], "lime")
    if "H2O" in m.fs.lime_reactor.flow_mass_reagent:
        m.fs.costing.cost_flow(m.fs.lime_reactor.flow_mass_reagent["H2O"], "process_water")
    
    # Cost soda ash for lithium carbonate reactor
    m.fs.costing.cost_flow(m.fs.lithium_carbonate_reactor.flow_mass_reagent["Na2CO3"], "soda_ash")
    if "H2O" in m.fs.lithium_carbonate_reactor.flow_mass_reagent:
        m.fs.costing.cost_flow(m.fs.lithium_carbonate_reactor.flow_mass_reagent["H2O"], "process_water")

def add_costing(m, stage=3):
    """Add costing components to the lithium processing flowsheet.
    
    Args:
        m: Pyomo model to add costing to
        stage: Stage of flowsheet to add costing to
            1 - Feed, storage tank, and pump only
            2 - Stage 1 + stoichiometric reactors
            3 - Stage 2 + dewaterers (complete flowsheet)
    """
    # Add global costing
    m.fs.costing = REFLOCosting()
    m.fs.costing.base_currency = pyunits.USD_2023

    # Add unit model costing blocks for Stage 1
    m.fs.brine_storage.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)
    m.fs.brine_pump.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)
    
    # Add unit model costing blocks for Stage 2
    if stage >= 2:
        m.fs.soda_ash_reactor.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)
        m.fs.lime_reactor.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)
        m.fs.lithium_carbonate_reactor.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)
    
    # Add unit model costing blocks for Stage 3
    if stage >= 3:
        # Add lime dewatering unit costing with belt filter press configuration
        m.fs.lime_dewatering.costing = UnitModelCostingBlock(
            flowsheet_costing_block=m.fs.costing,
            costing_method=cost_dewatering,
            costing_method_arguments={
                "dewatering_type": DewateringType.filter_plate_press,
                "cost_electricity_flow": True,
            },
        )
        
        # Add lime centrifuge unit costing with centrifuge configuration
        m.fs.lime_centrifuge.costing = UnitModelCostingBlock(
            flowsheet_costing_block=m.fs.costing,
            costing_method=cost_dewatering,
            costing_method_arguments={
                "dewatering_type": DewateringType.centrifuge,
                "cost_electricity_flow": True,
            },
        )
        
        # Add soda ash dewatering unit costing with custom RDVF configuration
        m.fs.soda_ash_dewatering.costing = UnitModelCostingBlock(
            flowsheet_costing_block=m.fs.costing,
            costing_method=make_rdvf_costing_method(
                number_of_drums=2,
                cost_electricity_flow=True,
            ),
        )
        
        # Add soda ash centrifuge dewatering unit costing with centrifuge configuration
        m.fs.soda_ash_centrifuge.costing = UnitModelCostingBlock(
            flowsheet_costing_block=m.fs.costing,
            costing_method=cost_dewatering,
            costing_method_arguments={
                "dewatering_type": DewateringType.centrifuge,
                "cost_electricity_flow": True,
            },
        )
        
        # Add lithium dewatering unit costing with belt filter press configuration
        m.fs.li_dewatering.costing = UnitModelCostingBlock(
            flowsheet_costing_block=m.fs.costing,
            costing_method=cost_dewatering,
            costing_method_arguments={
                "dewatering_type": DewateringType.filter_belt_press,
                "cost_electricity_flow": True,
            },
        )
    
    # Add flow costs
    add_flow_costs(m)
    
    # Fix global costing parameters
    m.fs.costing.plant_lifetime.fix(35)
    m.fs.costing.wacc.fix(0.10)
    m.fs.costing.electricity_cost.fix(value(pyunits.convert(0.15 * pyunits.USD_2023 / pyunits.kWh, to_units=m.fs.costing.base_currency / pyunits.kWh)))
    m.fs.costing.electrical_carbon_intensity.fix(0.229)
    m.fs.costing.utilization_factor.fix(0.98)

    # Check degrees of freedom
    dof = degrees_of_freedom(m)
    if dof != 0:
        print(f"Warning: {dof} degrees of freedom remaining after costing setup")
    else:
        print("All variables properly fixed after costing setup")
