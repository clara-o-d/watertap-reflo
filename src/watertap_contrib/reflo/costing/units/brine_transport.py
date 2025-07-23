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

def build_brine_transport_cost_param_block(blk):
    # No extra parameters for now
    pass

@register_costing_parameter_block(
    build_rule=build_brine_transport_cost_param_block,
    parameter_block_name="brine_transport",
)
def cost_brine_transport(blk):
    # Costing parameters (now defined here)
    blk.shipping_distance = Param(
        initialize=200, mutable=True, units=blk.costing_package.base_currency/pyunits.km,
        doc="Shipping distance to next facility (km)"
    )
    blk.shipping_unit_cost = Param(
        initialize=0.025, mutable=True, units=blk.costing_package.base_currency/pyunits.t/pyunits.km,
        doc="Shipping cost per ton per km ($/t/km)"
    )
    blk.density_concentrated_brine = Param(
        initialize=1323, mutable=True, units=pyunits.kg/pyunits.m**3,
        doc="Density of concentrated brine for Li+ volume calculation"
    )
    blk.capital_cost = make_capital_cost_var(blk)
    blk.fixed_operating_cost = make_fixed_operating_cost_var(blk)
    blk.annual_shipping_cost = Var(
        initialize=1e5, units=blk.costing_package.base_currency/pyunits.year, doc="Annual shipping cost ($/year)"
    )
    blk.eq_annual_shipping_cost = Constraint(
        expr=blk.annual_shipping_cost == (
            blk.unit_model.brine_outflow_t_per_year * blk.shipping_distance * blk.shipping_unit_cost
        )
    )
    blk.capital_cost_constraint = Constraint(
        expr=blk.capital_cost == 0  # Assume no capital cost for transport (trucking)
    )
    blk.fixed_operating_cost_constraint = Constraint(
        expr=blk.fixed_operating_cost == blk.annual_shipping_cost
    )
    # WaterTAP/IDAES requires direct_capital_cost for aggregation
    blk.direct_capital_cost = Expression(expr=blk.capital_cost) 