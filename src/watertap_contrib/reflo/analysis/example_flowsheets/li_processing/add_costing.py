from idaes.core import UnitModelCostingBlock
from watertap_contrib.reflo.costing import TreatmentCosting  # For standard WaterTAP units like BoronRemoval
from watertap_contrib.reflo.costing.watertap_reflo_costing_package import REFLOCosting  # For REFLO custom units
from pyomo.environ import Param, Var, Constraint, Expression
from pyomo.environ import units as pyunits

def add_costing(m):
    # Use TreatmentCosting for standard WaterTAP units
    m.fs.treatment_costing = TreatmentCosting()
    
    # Use REFLOCosting for REFLO custom units  
    m.fs.reflo_costing = REFLOCosting()
    
    # Add costing to BoronRemoval (standard WaterTAP unit)
    if hasattr(m.fs, 'boron_removal'):
        m.fs.boron_removal.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.treatment_costing)
    
    # Add costing to ChemicalSoftening (REFLO custom unit with default_costing_method)
    if hasattr(m.fs, 'softening'):
        m.fs.softening.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.reflo_costing)
    
    # Note: Zero-order units (StorageTankZO, ClarifierZO) are skipped for now
    # as they require database configuration which is complex to set up
    
    # Fix global costing parameters for both packages
    for costing in [m.fs.treatment_costing, m.fs.reflo_costing]:
        costing.plant_lifetime.fix(20)
        costing.wacc.fix(0.07)
        costing.electricity_cost.fix(0.16)
        costing.electrical_carbon_intensity.fix(0.229)
        costing.utilization_factor.fix(0.98)
        costing.maintenance_labor_chemical_factor.fix(0.01) 