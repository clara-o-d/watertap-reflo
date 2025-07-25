from idaes.core import UnitModelCostingBlock
from watertap_contrib.reflo.costing.watertap_reflo_costing_package import REFLOCosting
from watertap.unit_models.pressure_changer import Pump

def add_costing(m):
    m.fs.costing = REFLOCosting()
    m.fs.pond.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)
    m.fs.pump.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)
    # Fix global costing parameters
    m.fs.costing.plant_lifetime.fix(20)
    m.fs.costing.wacc.fix(0.07)
    m.fs.costing.electricity_cost.fix(0.16)
    m.fs.costing.electrical_carbon_intensity.fix(0.229)
    m.fs.costing.utilization_factor.fix(0.98)
    m.fs.costing.maintenance_labor_chemical_factor.fix(0.01) 