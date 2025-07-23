#################################################################################
# WaterTAP Copyright (c) 2020-2025, The Regents of the University of California,
# through Lawrence Berkeley National Laboratory, Oak Ridge National Laboratory,
# National Renewable Energy Laboratory, and National Energy Technology
# Laboratory (subject to receipt of any required approvals from the U.S. Dept.
# of Energy). All rights reserved.
#
# Please see the files COPYRIGHT.md and LICENSE.md for full copyright and license
# information, respectively. These files are also available online at the URL
# "https://github.com/watertap-org/watertap/"
#################################################################################

from pyomo.environ import (
    Constraint, Param, Var, Expression, units as pyunits
)
from watertap.costing.util import register_costing_parameter_block
from ..util import make_capital_cost_var, make_fixed_operating_cost_var

def build_brine_extraction_cost_param_block(blk):
    # No extra parameters for now
    pass

@register_costing_parameter_block(
    build_rule=build_brine_extraction_cost_param_block,
    parameter_block_name="brine_extraction",
)
def cost_brine_extraction(blk):
    # Costing parameters (now defined here)
    blk.well_capital_cost = Param(
        initialize=9.357143e+05, mutable=True, units=blk.costing_package.base_currency,
        doc="Capital cost per extraction well ($/well)"
    )
    blk.piping_unit_cost = Param(
        initialize=120000, mutable=True, units=blk.costing_package.base_currency,
        doc="Piping cost per km ($/km)"
    )
    # Capital cost: wells + piping
    blk.capital_cost = make_capital_cost_var(blk)
    blk.fixed_operating_cost = make_fixed_operating_cost_var(blk)
    blk.total_well_capital_cost = Var(
        initialize=1e7, units=blk.costing_package.base_currency, doc="Total wellfield capital cost ($)"
    )
    blk.total_piping_capital_cost = Var(
        initialize=1e6, units=blk.costing_package.base_currency, doc="Total piping capital cost ($)"
    )
    blk.pumping_cost = Var(
        initialize=1, units=blk.costing_package.base_currency/pyunits.year, doc="Secondly pumping cost ($/s)"
    )
    blk.eq_total_well_capital_cost = Constraint(
        expr=blk.total_well_capital_cost == blk.unit_model.number_of_wells * blk.well_capital_cost
    )
    blk.eq_total_piping_capital_cost = Constraint(
        expr=blk.total_piping_capital_cost == blk.unit_model.piping_length * blk.piping_unit_cost
    )
    blk.eq_pumping_cost = Constraint(
        expr=blk.pumping_cost == (
            blk.unit_model.flow_vol * blk.unit_model.rho * 9.81 * blk.unit_model.pumping_head / blk.unit_model.pumping_efficiency
            * blk.flowsheet().costing.electricity_cost
        )
    )
    blk.capital_cost_constraint = Constraint(
        expr=blk.capital_cost == blk.total_well_capital_cost + blk.total_piping_capital_cost
    )
    blk.fixed_operating_cost_constraint = Constraint(
        expr=blk.fixed_operating_cost == pyunits.convert(blk.pumping_cost, to_units=blk.costing_package.base_currency / pyunits.year)
    )
    # WaterTAP/IDAES requires direct_capital_cost for aggregation
    blk.direct_capital_cost = Expression(expr=blk.capital_cost) 
    # import idaes.core.util.scaling as iscale
    # iscale.set_scaling_factor(blk.total_well_capital_cost, 1e-7)
    # iscale.set_scaling_factor(blk.total_piping_capital_cost, 1e-6)
    # iscale.set_scaling_factor(blk.annual_pumping_cost, 1e-6)
    # iscale.set_scaling_factor(blk.capital_cost, 1e-7
    # iscale.set_scaling_factor(blk.fixed_operating_cost, 1e-6)
    # iscale.set_scaling_factor(blk.eq_annual_pumping_cost, 1e-6)