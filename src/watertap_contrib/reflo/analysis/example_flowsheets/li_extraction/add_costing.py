from idaes.core import UnitModelCostingBlock
from watertap_contrib.reflo.costing.watertap_reflo_costing_package import REFLOCosting
from watertap.unit_models.pressure_changer import Pump
from pyomo.environ import Param, Var, Constraint, Expression
from pyomo.environ import units as pyunits
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.custom_brine_transfer_costing import cost_brine_transfer_system

def add_costing(m):
    m.fs.costing = REFLOCosting()
    m.fs.pond.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)
    
    # Use custom brine transfer costing for the pump (includes pipeline costs)
    m.fs.pump.costing = UnitModelCostingBlock(
        flowsheet_costing_block=m.fs.costing,
        costing_method=cost_brine_transfer_system,
        costing_method_arguments={
            "pipeline_length_km": 1.0,  # 1 km pipeline
            "pipeline_diameter_m": 0.12,  # 12 cm diameter HDPE pipe
        }
    )
    
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

    def eq_annual_concentrated_brine_outflow(b):
        return b.annual_concentrated_brine_outflow == pyunits.convert(b.concentrated_brine_outflow, to_units=pyunits.kg/pyunits.year)
    m.fs.eq_annual_concentrated_brine_outflow = Constraint(rule=eq_annual_concentrated_brine_outflow, doc="Annual concentrated brine outflow for shipping")

    m.fs.shipping_cost = Expression(
        expr=m.fs.shipping_distance * m.fs.shipping_unit_cost,
        doc="Shipping cost per kg (as Expression)"
    )
    m.fs.costing.register_flow_type("shipping", m.fs.shipping_cost)
    m.fs.costing.cost_flow(m.fs.annual_concentrated_brine_outflow, "shipping")
    
    # Fix global costing parameters
    m.fs.costing.plant_lifetime.fix(35)
    m.fs.costing.wacc.fix(0.07)
    m.fs.costing.electricity_cost.fix(0.16)
    m.fs.costing.electrical_carbon_intensity.fix(0.229)
    m.fs.costing.utilization_factor.fix(0.98)
    m.fs.costing.maintenance_labor_chemical_factor.fix(0.01) 