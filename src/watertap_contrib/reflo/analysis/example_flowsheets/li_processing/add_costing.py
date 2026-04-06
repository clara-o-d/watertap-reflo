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
- Softening waste Product block (waste handling: capital + OPEX vs dry salt, USD/metric tonne)
"""

import math
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


def _yaml_float(mapping, key, default=0.0):
    """YAML values may be numpy scalars or null; Pyomo Var initialize() needs native float."""
    v = mapping.get(key, default)
    if v is None:
        return float(default)
    return float(v)

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


def _dry_salt_mass_flow_kg_s(props, water_component_name="H2O"):
    """Mass flow of dry salt / solids (liquid phase, excluding water) [kg/s]."""
    return sum(
        props.flow_mass_phase_comp["Liq", j]
        for j in props.params.component_list
        if j != water_component_name
    )


def build_waste_handling_cost_params(costing_package, params=None):
    """Attach global waste-handling correlation parameters to the costing package (dry metric tonne basis)."""
    if params is None:
        params = load_costing_parameters()
    wh_params = params.get("waste_handling", {})

    if not hasattr(costing_package, "waste_handling"):
        costing_package.waste_handling = Block()

        costing_package.waste_handling.capital_fixed_usd = Var(
            initialize=_yaml_float(wh_params, "capital_fixed_usd", 0.0),
            doc="Fixed capital adder for waste handling (before TIC)",
            units=pyunits.USD_2023,
        )
        costing_package.waste_handling.capital_fixed_usd.fix()

        # USD per (metric tonne dry salt / s) — same as USD * s / tonne
        _per_dry_tonne_rate_units = pyunits.USD_2023 * pyunits.s / pyunits.tonne
        cap_init = wh_params.get("capital_usd_per_dry_metric_ton_salt_rate")
        if cap_init is None:
            cap_init = wh_params.get("capital_per_dry_metric_ton_salt_rate")
        if cap_init is None:
            cap_init = wh_params.get("capital_per_flow_vol", 0.0)
        if cap_init is None:
            cap_init = 0.0
        else:
            cap_init = float(cap_init)
        costing_package.waste_handling.capital_usd_per_dry_metric_ton_salt_rate = Var(
            initialize=cap_init,
            doc="Capital coefficient [USD] per [metric tonne dry salt / s] (dry = liquid phase mass excluding water)",
            units=_per_dry_tonne_rate_units,
        )
        costing_package.waste_handling.capital_usd_per_dry_metric_ton_salt_rate.fix()


def cost_waste_product(blk, cost_dry_salt_mass_flow=True, params=None):
    """
    Costing for the softening waste Product block (IDAES Product).

    Default economics (dry salt = liquid-phase mass excluding ``water_component_name``, typically H2O):

    - Capital: TIC * (capital_fixed_usd
      + capital_usd_per_dry_metric_ton_salt_rate * ṁ_dry [metric tonne/s]).
    - Operating: cost_flow on ṁ_dry [kg/s] at ``waste_handling`` cost registered as $/kg dry salt
      (= operating_cost_usd_per_dry_metric_ton_salt / 1000).

    Replace or extend by deactivating ``capital_cost_constraint`` (and optionally the mass-flow
    registration) and adding custom constraints on ``blk.capital_cost`` / other components.
    """
    if params is None:
        params = load_costing_parameters()
    build_waste_handling_cost_params(blk.costing_package, params)

    make_capital_cost_var(blk)
    blk.costing_package.add_cost_factor(blk, "TIC")

    t0 = blk.flowsheet().time.first()
    props = blk.unit_model.properties[t0]
    wh = blk.costing_package.waste_handling
    wh_params = params.get("waste_handling", {})
    water_name = wh_params.get("water_component_name", "H2O")

    m_dot_dry = _dry_salt_mass_flow_kg_s(props, water_component_name=water_name)
    m_dot_dry_tonnes_s = pyunits.convert(m_dot_dry, to_units=pyunits.tonne / pyunits.s)

    blk.capital_cost_constraint = Constraint(
        expr=blk.capital_cost
        == blk.cost_factor
        * pyunits.convert(
            wh.capital_fixed_usd
            + wh.capital_usd_per_dry_metric_ton_salt_rate * m_dot_dry_tonnes_s,
            to_units=blk.costing_package.base_currency,
        )
    )

    if cost_dry_salt_mass_flow:
        blk.costing_package.cost_flow(m_dot_dry, "waste_handling")


def make_waste_product_costing_method(params=None, cost_dry_salt_mass_flow=None):
    """Factory for :func:`cost_waste_product` (WaterTAP costing_method hook)."""

    if params is None:
        params = load_costing_parameters()
    wh = params.get("waste_handling", {})
    if cost_dry_salt_mass_flow is None:
        cost_dry_salt_mass_flow = wh.get(
            "cost_dry_salt_mass_flow", wh.get("cost_mass_flow", True)
        )

    def costing_method(blk):
        cost_waste_product(
            blk, cost_dry_salt_mass_flow=cost_dry_salt_mass_flow, params=params
        )

    return costing_method


def register_waste_handling_flow_cost(m, params=None):
    """
    Register ``waste_handling`` flow type before attaching ``UnitModelCostingBlock`` to ``softening_waste``.

    ``m.fs.waste_handling_cost`` is [currency]/kg **dry salt** (metric tonne basis / 1000).
    """
    if params is None:
        params = load_costing_parameters()
    if not hasattr(m.fs, "softening_waste"):
        return
    wh_params = params.get("waste_handling", {})
    per_tonne = wh_params.get("operating_cost_usd_per_dry_metric_ton_salt")
    if per_tonne is not None:
        per_kg = float(per_tonne) / 1000.0
    elif wh_params.get("operating_cost_per_kg") is not None:
        per_kg = _yaml_float(wh_params, "operating_cost_per_kg", 0.02)
    else:
        per_kg = 0.02
    m.fs.waste_handling_cost = Param(
        initialize=per_kg,
        mutable=True,
        units=pyunits.USD_2023 / pyunits.kg,
        doc="Waste handling variable cost per kg dry salt (excludes water; from $/dry metric tonne)",
    )
    m.fs.costing.register_flow_type("waste_handling", m.fs.waste_handling_cost)
    # For reporting (display_results): dry-salt mass excludes this species
    m.fs.waste_handling_water_component_name = wh_params.get("water_component_name", "H2O")


def add_flow_costs(m, params=None):
    if params is None:
        params = load_costing_parameters()
    flow_costs = params['flow_costs']
    
    if hasattr(m.fs.brine_pump.control_volume, 'work'):
        original_lb = m.fs.brine_pump.control_volume.work[0].lb
        m.fs.brine_pump.control_volume.work[0].setlb(0)
    
    if hasattr(m.fs, 'second_pump') and hasattr(m.fs.second_pump.control_volume, 'work'):
        m.fs.second_pump.control_volume.work[0].setlb(0)
    
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
    
    if hasattr(m.fs, 'second_pump'):
        m.fs.costing.cost_flow(m.fs.second_pump.control_volume.work[0], "electricity")
    
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
            units=pyunits.USD_1991,
        )
        costing_package.reactor_cost_params.capital_a_parameter.fix()
        
        costing_package.reactor_cost_params.capital_n_exponent = Var(
            initialize=reactor_params['capital_n_exponent'],
            doc="Exponent (n) in reactor capital cost correlation",
            units=pyunits.dimensionless,
        )
        costing_package.reactor_cost_params.capital_n_exponent.fix()

        costing_package.reactor_cost_params.capital_b_parameter = Var(
            initialize=reactor_params['capital_b_parameter'],
            doc="Variable cost parameter (b) in reactor capital cost correlation",
            units=pyunits.USD_1991 / (pyunits.m**3)**reactor_params['capital_n_exponent'],
        )
        costing_package.reactor_cost_params.capital_b_parameter.fix()

def apply_dewatering_split_costing(m):
    """Replace dewatering capital cost constraints with split-unit versions when flow exceeds equipment max capacity."""
    t0 = m.fs.time.first()

    # max capacities per unit (single unit)
    _MAX_CENTRIFUGE_GAL_HR   = 54000.0
    _MAX_BELT_PRESS_GAL_HR   = 53000.0
    _MAX_PLATE_PRESS_GAL_HR  =  6600.0
    _MAX_RDVF_M3_DAY         =  5000.0

    # --- RDVF vacuum filter (soda_ash_vacuum_filter) ---
    if hasattr(m.fs, 'soda_ash_vacuum_filter') and hasattr(m.fs.soda_ash_vacuum_filter, 'costing'):
        unit = m.fs.soda_ash_vacuum_filter
        blk = unit.costing
        if hasattr(blk, 'capital_cost_constraint'):
            flow_m3_day = value(pyunits.convert(unit.mixed_state[t0].flow_vol, to_units=pyunits.m**3 / pyunits.day))
            n_units = max(1, math.ceil(flow_m3_day / _MAX_RDVF_M3_DAY))
            blk.num_units_for_costing = Param(
                initialize=n_units,
                doc="Number of parallel units for costing",
                units=pyunits.dimensionless,
            )
            if n_units > 1:
                print(f"  → soda_ash_vacuum_filter: flow {flow_m3_day:.1f} m³/day exceeds max {_MAX_RDVF_M3_DAY:.0f} m³/day; splitting into {n_units} units for costing")
                blk.capital_cost_constraint.deactivate()
                cost_blk = blk.costing_package.rdvf
                blk.capital_cost_constraint_split = Constraint(
                    expr=blk.capital_cost
                    == n_units
                    * blk.cost_factor
                    * pyunits.convert(
                        cost_blk.capital_a_parameter * blk.number_of_drums * cost_blk.drum_unit_cost,
                        to_units=blk.costing_package.base_currency,
                    )
                )

    # --- Centrifuge units (soda_ash_centrifuge, lime_centrifuge) ---
    for unit_name in ['soda_ash_centrifuge', 'lime_centrifuge']:
        if not (hasattr(m.fs, unit_name) and hasattr(getattr(m.fs, unit_name), 'costing')):
            continue
        unit = getattr(m.fs, unit_name)
        blk = unit.costing
        if not hasattr(blk, 'capital_cost_constraint'):
            continue
        flow_gal_hr = value(pyunits.convert(unit.mixed_state[t0].flow_vol, to_units=pyunits.gallon / pyunits.hr))
        n_units = max(1, math.ceil(flow_gal_hr / _MAX_CENTRIFUGE_GAL_HR))
        blk.num_units_for_costing = Param(
            initialize=n_units,
            doc="Number of parallel units for costing",
            units=pyunits.dimensionless,
        )
        if n_units > 1:
            print(f"  → {unit_name}: flow {flow_gal_hr:.1f} gal/hr exceeds max {_MAX_CENTRIFUGE_GAL_HR:.0f} gal/hr; splitting into {n_units} units for costing")
            blk.capital_cost_constraint.deactivate()
            cost_blk = blk.costing_package.centrifuge
            x = pyunits.convert(unit.mixed_state[t0].flow_vol, to_units=pyunits.gallon / pyunits.hr)
            blk.capital_cost_constraint_split = Constraint(
                expr=blk.capital_cost
                == blk.cost_factor
                * pyunits.convert(
                    cost_blk.capital_a_parameter * x + n_units * cost_blk.capital_b_parameter,
                    to_units=blk.costing_package.base_currency,
                )
            )

    # --- Belt filter press (li_dewatering) ---
    if hasattr(m.fs, 'li_dewatering') and hasattr(m.fs.li_dewatering, 'costing'):
        unit = m.fs.li_dewatering
        blk = unit.costing
        if hasattr(blk, 'capital_cost_constraint'):
            flow_gal_hr = value(pyunits.convert(unit.mixed_state[t0].flow_vol, to_units=pyunits.gallon / pyunits.hr))
            n_units = max(1, math.ceil(flow_gal_hr / _MAX_BELT_PRESS_GAL_HR))
            blk.num_units_for_costing = Param(
                initialize=n_units,
                doc="Number of parallel units for costing",
                units=pyunits.dimensionless,
            )
            if n_units > 1:
                print(f"  → li_dewatering: flow {flow_gal_hr:.1f} gal/hr exceeds max {_MAX_BELT_PRESS_GAL_HR:.0f} gal/hr; splitting into {n_units} units for costing")
                blk.capital_cost_constraint.deactivate()
                cost_blk = blk.costing_package.filter_belt_press
                x = pyunits.convert(unit.mixed_state[t0].flow_vol, to_units=pyunits.gallon / pyunits.hr)
                blk.capital_cost_constraint_split = Constraint(
                    expr=blk.capital_cost
                    == blk.cost_factor
                    * pyunits.convert(
                        cost_blk.capital_a_parameter * x + n_units * cost_blk.capital_b_parameter,
                        to_units=blk.costing_package.base_currency,
                    )
                )

    # --- Plate filter press (lime_press_filter) ---
    if hasattr(m.fs, 'lime_press_filter') and hasattr(m.fs.lime_press_filter, 'costing'):
        unit = m.fs.lime_press_filter
        blk = unit.costing
        if hasattr(blk, 'capital_cost_constraint'):
            x_units = pyunits.gallon / pyunits.hr
            flow_gal_hr = value(pyunits.convert(unit.mixed_state[t0].flow_vol, to_units=x_units))
            n_units = max(1, math.ceil(flow_gal_hr / _MAX_PLATE_PRESS_GAL_HR))
            blk.num_units_for_costing = Param(
                initialize=n_units,
                doc="Number of parallel units for costing",
                units=pyunits.dimensionless,
            )
            if n_units > 1:
                print(f"  → lime_press_filter: flow {flow_gal_hr:.1f} gal/hr exceeds max {_MAX_PLATE_PRESS_GAL_HR:.0f} gal/hr; splitting into {n_units} units for costing")
                blk.capital_cost_constraint.deactivate()
                cost_blk = blk.costing_package.filter_plate_press
                x = pyunits.convert(unit.mixed_state[t0].flow_vol, to_units=x_units)
                blk.capital_cost_constraint_split = Constraint(
                    expr=blk.capital_cost
                    == n_units
                    * blk.cost_factor
                    * pyunits.convert(
                        cost_blk.capital_a_parameter
                        * x_units
                        * (x / x_units / n_units) ** cost_blk.capital_b_parameter,
                        to_units=blk.costing_package.base_currency,
                    )
                )

def add_costing(m, yaml_path=None):
    """Add costing blocks to all unit models and register flow costs."""
    params = load_costing_parameters(yaml_path)
    general_params = params['general']
    
    m.fs.costing = REFLOCosting()
    m.fs.costing.base_currency = pyunits.USD_2023
    
    build_reactor_cost_params(m.fs.costing, params)
    # Must register waste_handling flow before UnitModelCostingBlock on softening_waste (uses cost_flow).
    register_waste_handling_flow_cost(m, params)

    m.fs.brine_storage.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)
    m.fs.brine_pump.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)
    
    if hasattr(m.fs, 'second_pump'):
        m.fs.second_pump.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)
    
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

        m.fs.softening_waste.costing = UnitModelCostingBlock(
            flowsheet_costing_block=m.fs.costing,
            costing_method=make_waste_product_costing_method(params=params),
        )
    
    add_flow_costs(m, params)
    
    v_max_m3 = params['reactor_cost'].get('v_max_m3', float('inf'))
    v_min_m3 = params['reactor_cost'].get('v_min_m3', 0.0)

    for reactor_name in ['soda_ash_reactor', 'lime_reactor', 'lithium_carbonate_reactor']:
        if hasattr(m.fs, reactor_name):
            reactor = getattr(m.fs, reactor_name)
            if hasattr(reactor, 'costing') and hasattr(reactor.costing, 'capital_cost_constraint'):
                print(f"Replacing capital cost constraint for {reactor_name} with volume-based correlation")
                blk = reactor.costing
                blk.capital_cost_constraint.deactivate()

                if hasattr(reactor, 'reactor_volume'):
                    reactor_vol_m3 = value(pyunits.convert(reactor.reactor_volume, to_units=pyunits.m**3))
                    n_reactors = max(1, math.ceil(reactor_vol_m3 / v_max_m3))

                    if reactor_vol_m3 > v_max_m3:
                        print(f"  → {reactor_name}: volume {reactor_vol_m3:.3f} m³ exceeds max {v_max_m3:.3f} m³; splitting into {n_reactors} reactors for costing")
                    elif reactor_vol_m3 < v_min_m3:
                        print(f"  → {reactor_name}: volume {reactor_vol_m3:.3f} m³ below min {v_min_m3:.3f} m³; applying correlation (extrapolation)")

                    blk.num_reactors_for_costing = Param(
                        initialize=n_reactors,
                        doc="Number of parallel reactors for costing",
                        units=pyunits.dimensionless,
                    )

                    blk.capital_cost_constraint_volume = Constraint(
                        expr=blk.capital_cost
                        == blk.cost_factor
                        * n_reactors
                        * (
                            blk.costing_package.reactor_cost_params.capital_a_parameter
                            + blk.costing_package.reactor_cost_params.capital_b_parameter
                            * (pyunits.convert(reactor.reactor_volume, to_units=pyunits.m**3) / n_reactors)
                            ** blk.costing_package.reactor_cost_params.capital_n_exponent
                        )
                    )
                    print(f"  → Volume-based cost constraint created for {reactor_name} ({n_reactors} reactor(s))")
                else:
                    print(f"  → Warning: reactor_volume not found for {reactor_name}, keeping original constraint")
                    blk.capital_cost_constraint.activate()

    apply_dewatering_split_costing(m)

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
