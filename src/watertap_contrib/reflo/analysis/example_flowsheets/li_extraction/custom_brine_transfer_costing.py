import pyomo.environ as pyo
from watertap.costing.unit_models.pump import cost_low_pressure_pump
from watertap.costing.util import make_capital_cost_var, register_costing_parameter_block
from watertap.costing.util import cost_by_flow_volume
from pyomo.environ import units as pyunits
from pyomo.environ import value

def build_brine_transfer_cost_param_block(blk):
    """Build parameter block for brine transfer system costing"""
    
    # Pipeline cost parameters for 12 cm HDPE pipe
    blk.pipeline_cost_per_meter = pyo.Var(
        initialize=75,  # USD/m - typical for 12 cm HDPE pipe
        doc="Pipeline cost per meter length",
        units=pyunits.USD_2018 / pyunits.m,
    )
    
    blk.pipeline_diameter = pyo.Var(
        initialize=0.12,  # 12 cm diameter
        doc="Pipeline diameter",
        units=pyunits.m,
    )
    
    blk.pipeline_length = pyo.Var(
        initialize=1000,  # 1 km
        doc="Pipeline length",
        units=pyunits.m,
    )
    
    # Installation costs only (no maintenance/labor)
    blk.installation_factor = pyo.Var(
        initialize=2.0,  # Installation typically 2x material cost for HDPE
        doc="Installation cost factor",
        units=pyunits.dimensionless,
    )


@register_costing_parameter_block(
    build_rule=build_brine_transfer_cost_param_block,
    parameter_block_name="brine_transfer",
)
def cost_brine_transfer_system(blk, pipeline_length_km=1.0, pipeline_diameter_m=0.12):
    """
    Simplified brine transfer costing method with basic pipeline costs for 12 cm HDPE pipe
    
    Args:
        pipeline_length_km: Pipeline length in kilometers
        pipeline_diameter_m: Pipeline diameter in meters (default 0.12 m = 12 cm)
    """
    
    # Create capital cost variable
    make_capital_cost_var(blk)
    
    # Get flow rate
    t0 = blk.flowsheet().time.first()
    flow_vol = pyunits.convert(
        blk.unit_model.control_volume.properties_in[t0].flow_vol,
        to_units=pyunits.m**3 / pyunits.s,
    )
    
    # Simplified pipeline cost calculation for 12 cm HDPE pipe
    # Based on typical costs for HDPE pipelines
    pipeline_cost_per_meter = 75 * pyunits.USD_2018 / pyunits.m  # HDPE pipe cost
    installation_factor = 2.0  # Installation typically 2x material cost for HDPE
    
    pipeline_length = pipeline_length_km * 1000 * pyunits.m
    pipeline_diameter = pipeline_diameter_m * pyunits.m
    
    # Calculate total pipeline cost (material + installation only)
    pipeline_material_cost = (
        pipeline_cost_per_meter 
        * pipeline_length 
        * pipeline_diameter
    )
    
    total_pipeline_cost = pipeline_material_cost * installation_factor
    
    # Use low pressure pump costing for the pump component
    cost_low_pressure_pump(blk, cost_electricity_flow=True)
    
    # Store pump capital cost as a parameter
    blk.pump_capital_cost = pyo.Param(
        initialize=889,
        doc="Pump capital cost",
        units=pyunits.USD_2018/(pyunits.liter/pyunits.second),
    )
    t0 = blk.flowsheet().time.first()
    cost_by_flow_volume(
        blk,
        blk.costing_package.low_pressure_pump.cost,
        pyo.units.convert(
            blk.unit_model.control_volume.properties_in[t0].flow_vol,
            (pyo.units.m**3 / pyo.units.s),
        ),
    )
    
    # Wellfield capital cost
    blk.well_capital_cost = pyo.Param(
        initialize=9.357143e+05, mutable=True, units=blk.costing_package.base_currency,
        doc="Capital cost per extraction well ($/well)"
    )

    blk.number_of_wells = pyo.Param(
        initialize=320,
        mutable=True,
        units=pyunits.dimensionless,
        doc="Number of extraction wells"
    )

    blk.total_well_capital_cost = pyo.Var(
        initialize=1e6, units=blk.costing_package.base_currency, bounds=(0, None), 
        doc="Total wellfield capital cost"
    )

    @blk.Constraint(doc="Total wellfield capital cost")
    def total_well_capital_cost_constraint(b):
        return b.total_well_capital_cost == b.number_of_wells * b.well_capital_cost

    # Create new constraint that includes both pump and pipeline
    blk.capital_cost_constraint.deactivate()
    
    blk.capital_cost_constraint = pyo.Constraint(
        expr=blk.capital_cost == blk.total_well_capital_cost + 
        blk.cost_factor * (pyunits.convert(
            blk.pump_capital_cost * pyunits.convert(
                blk.unit_model.control_volume.properties_in[t0].flow_vol,
                to_units=pyunits.m**3 / pyunits.s,
            ),
            to_units=blk.costing_package.base_currency,
        )
        + total_pipeline_cost)
    )