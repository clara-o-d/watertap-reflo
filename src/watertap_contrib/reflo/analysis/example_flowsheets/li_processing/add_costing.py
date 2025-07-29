from idaes.core import UnitModelCostingBlock
from watertap_contrib.reflo.costing.watertap_reflo_costing_package import REFLOCosting


def add_costing(m):
    # Attach costing blocks to all major units
    m.fs.costing = REFLOCosting()
    for unit in [
        m.fs.storage, m.fs.boron_removal, m.fs.softening, m.fs.carbonation,
        m.fs.carbonation_sep, m.fs.drying
        # LiOH units commented out since they are not in the current flowsheet
        # m.fs.lioh_reactor, m.fs.lioh_clarifier, m.fs.lioh_filter, 
        # m.fs.lioh_evap, m.fs.lioh_centrifuge, m.fs.lioh_dryer
    ]:
        if hasattr(unit, "costing"):
            continue
        try:
            unit.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)
        except Exception:
            pass
    m.fs.costing.plant_lifetime.fix(20)
    m.fs.costing.wacc.fix(0.07)
    m.fs.costing.electricity_cost.fix(0.16)
    m.fs.costing.electrical_carbon_intensity.fix(0.229)
    m.fs.costing.utilization_factor.fix(0.98)
    m.fs.costing.maintenance_labor_chemical_factor.fix(0.01) 