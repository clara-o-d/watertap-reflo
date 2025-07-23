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
    Param, Var, Constraint, units as pyunits
)
from pyomo.common.config import ConfigBlock, ConfigValue, In
from idaes.core import (
    declare_process_block_class,
    UnitModelBlockData,
    useDefault,
)
from watertap.core import InitializationMixin

@declare_process_block_class("BrineTransport")
class BrineTransportData(InitializationMixin, UnitModelBlockData):
    """
    Minimal brine transport unit model for flowsheet integration and costing.
    """
    CONFIG = ConfigBlock()
    CONFIG.declare(
        "dynamic",
        ConfigValue(
            domain=In([False]),
            default=False,
            description="Dynamic model flag - must be False",
        ),
    )
    CONFIG.declare(
        "has_holdup",
        ConfigValue(
            default=False,
            domain=In([False]),
            description="Holdup construction flag - must be False",
        ),
    )
    CONFIG.declare(
        "property_package",
        ConfigValue(
            default=useDefault,
            description="Property package to use for control volume",
        ),
    )
    CONFIG.declare(
        "property_package_args",
        ConfigBlock(implicit=True, description="Arguments for property package"),
    )

    def build(self):
        super().build()
        # Variables
        self.concentrated_brine_outflow = Var(
            initialize=1.0, bounds=(0, None), units=pyunits.kg/pyunits.s,
            doc="Total concentrated brine outflow for shipping (kg/s)"
        )
        # Expressions for ton/year
        self.brine_outflow_t_per_year = Var(
            initialize=1000, bounds=(0, None), units=pyunits.t/pyunits.year,
            doc="Brine outflow in ton/year"
        )
        @self.Constraint(doc="Brine outflow ton/year = outflow (kg/s) * conversion")
        def eq_brine_outflow_t_per_year(b):
            return b.brine_outflow_t_per_year == b.concentrated_brine_outflow * 3600 * 24 * 365 / 1000
        # Costing block will be attached externally
    @property
    def default_costing_method(self):
        from watertap_contrib.reflo.costing.units.brine_transport import cost_brine_transport
        return cost_brine_transport 