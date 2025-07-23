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

@declare_process_block_class("BrineExtraction")
class BrineExtractionData(InitializationMixin, UnitModelBlockData):
    """
    Minimal brine extraction unit model for flowsheet integration and costing.
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
        # Parameters
        self.number_of_wells = Param(
            initialize=320, mutable=True, units=pyunits.dimensionless,
            doc="Number of extraction wells"
        )
        self.piping_length = Param(
            initialize=1, mutable=True, units=pyunits.km,
            doc="Piping length from wells to pond (km)"
        )
        self.pumping_efficiency = Param(
            initialize=0.7, mutable=True, units=pyunits.dimensionless,
            doc="Pumping efficiency (fraction)"
        )
        self.pumping_head = Param(
            initialize=50, mutable=True, units=pyunits.m,
            doc="Pumping head (m)"
        )
        self.rho = Param(
            initialize=1227, mutable=True, units=pyunits.kg/pyunits.m**3,
            doc="Brine density (kg/m3)"
        )
        # Variables
        self.flow_vol = Var(
            initialize=1.0, bounds=(0, None), units=pyunits.m**3/pyunits.s,
            doc="Brine volumetric flow rate (m3/s)"
        )
        self.brine_mass_flow = Var(
            initialize=1000, bounds=(0, None), units=pyunits.kg/pyunits.s,
            doc="Brine mass flow (kg/s)"
        )
        # Constraints
        @self.Constraint(doc="Brine mass flow = volumetric flow * density")
        def eq_brine_mass_flow(b):
            return b.brine_mass_flow == b.flow_vol * b.rho
        # Costing block will be attached externally
        # import idaes.core.util.scaling as iscale
        # iscale.set_scaling_factor(self.flow_vol, 1)
        # iscale.set_scaling_factor(self.brine_mass_flow, 1e-3)
        # iscale.set_scaling_factor(self.eq_brine_mass_flow, 1e-3)
    @property
    def default_costing_method(self):
        from watertap_contrib.reflo.costing.units.brine_extraction import cost_brine_extraction
        return cost_brine_extraction 