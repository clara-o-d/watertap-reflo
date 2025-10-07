"""Costing module for lithium processing flowsheet.

Adds capital and operating costs for storage tank, pump, and reactors.
"""

from idaes.core import UnitModelCostingBlock
from watertap_contrib.reflo.costing.watertap_reflo_costing_package import REFLOCosting
from pyomo.environ import Param, Var, Expression
from pyomo.environ import units as pyunits
from pyomo.environ import value
from idaes.core.util.model_statistics import degrees_of_freedom

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
    if hasattr(m.fs.softening_reactor, 'flow_mass_reagent'):
        if "Na2CO3" in m.fs.softening_reactor.flow_mass_reagent:
            original_lb = m.fs.softening_reactor.flow_mass_reagent["Na2CO3"].lb
            m.fs.softening_reactor.flow_mass_reagent["Na2CO3"].setlb(0)
        if "CaO" in m.fs.softening_reactor.flow_mass_reagent:
            original_lb = m.fs.softening_reactor.flow_mass_reagent["CaO"].lb
            m.fs.softening_reactor.flow_mass_reagent["CaO"].setlb(0)
    
    if hasattr(m.fs.lithium_carbonate_reactor, 'flow_mass_reagent'):
        if "Na2CO3" in m.fs.lithium_carbonate_reactor.flow_mass_reagent:
            original_lb = m.fs.lithium_carbonate_reactor.flow_mass_reagent["Na2CO3"].lb
            m.fs.lithium_carbonate_reactor.flow_mass_reagent["Na2CO3"].setlb(0)
    
    # Pump electricity cost
    m.fs.costing.cost_flow(m.fs.brine_pump.control_volume.work[0], "electricity")
    
    # Reagent costs for softening reactor
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
    
    # Register reagent flow types
    m.fs.costing.register_flow_type("soda_ash", m.fs.soda_ash_cost)
    m.fs.costing.register_flow_type("lime", m.fs.lime_cost)
    
    # Cost reagent flows
    m.fs.costing.cost_flow(m.fs.softening_reactor.flow_mass_reagent["Na2CO3"], "soda_ash")
    m.fs.costing.cost_flow(m.fs.softening_reactor.flow_mass_reagent["CaO"], "lime")
    
    # Cost soda ash for lithium carbonate reactor
    m.fs.costing.cost_flow(m.fs.lithium_carbonate_reactor.flow_mass_reagent["Na2CO3"], "soda_ash")

def add_costing(m):
    """Add costing components to the lithium processing flowsheet.
    
    Args:
        m: Pyomo model to add costing to
    """
    # Add global costing
    m.fs.costing = REFLOCosting()
    m.fs.costing.base_currency = pyunits.USD_2023

    # Add unit model costing blocks
    m.fs.brine_storage.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)
    m.fs.brine_pump.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)
    m.fs.softening_reactor.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)
    m.fs.lithium_carbonate_reactor.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)
    
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
