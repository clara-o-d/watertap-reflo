#################################################################################
# Lithium Carbonate Plant Flowsheet
# Salar de Carmen (Antofagasta) Process
#################################################################################

import pyomo.environ as pyo
from pyomo.environ import units as pyunits
from pyomo.network import Arc
from pyomo.environ import units
from pyomo.core import TransformationFactory
import idaes.core.util.scaling as iscale
import idaes.logger as idaeslog

# IDAES imports
from idaes.core import FlowsheetBlock
from idaes.models.unit_models import Feed, Pump, Mixer, StoichiometricReactor
from idaes.core.util.initialization import propagate_state
from idaes.core.util.model_statistics import degrees_of_freedom
from idaes.core import Component, LiquidPhase, PhysicalParameterBlock, StateBlock, StateBlockData, declare_process_block_class, MaterialFlowBasis
from pyomo.environ import Param, Var, units, Constraint, PositiveReals
from idaes.core import MaterialBalanceType, EnergyBalanceType, MomentumBalanceType
from idaes.models.unit_models.mixer import MixingType, MomentumMixingType

# IDAES reaction imports
from idaes.models.properties.modular_properties.base.generic_reaction import (
    GenericReactionParameterBlock,
)
from idaes.models.properties.modular_properties.base.utility import ConcentrationForm

# PROMMIS imports for heterogeneous reaction packages
from idaes.core import ProcessBlockData, ProcessBlock, declare_process_block_class
from pyomo.environ import Set, Param, Var, Constraint
from pyomo.common.config import ConfigValue
from idaes.core.util.misc import add_object_reference
from math import log10
from pyomo.environ import Expression

# WaterTAP imports
from watertap.property_models.multicomp_aq_sol_prop_pack import (
    MCASParameterBlock,
    MCASParameterData,
    MCASStateBlockData,
    _MCASStateBlock,
)

# WaterTAP unit models
from watertap.unit_models.zero_order.storage_tank_zo import StorageTankZO as StorageTank
from watertap.unit_models.pressure_changer import Pump

# PROMMIS imports (will be added when we get to solvent extraction)
from prommis.solvent_extraction.solvent_extraction import SolventExtraction
from idaes.core import FlowDirection
from prommis.solvent_extraction.solvent_extraction import SolventExtractionInitializer



# ============================================================================
# MSContactor Variable Fixing Pattern
# ============================================================================
# For MSContactor units, fix volume[i], heterogeneous_reaction_extent, 
# distribution_coefficient, and volume_frac_stream variables to achieve DOF=0
# ============================================================================

# ============================================================================
# ACIDIFICATION REACTION PACKAGE
# ============================================================================

acidification_reaction_config = {
    "base_units": {
        "time": units.s,
        "length": units.m,
        "mass": units.kg,
        "amount": units.mol,
        "temperature": units.K,
    },
    "rate_reactions": {
        "HCl_dissociation": {
            "stoichiometry": {
                ("Liq", "H"): 1,      # H+ from HCl dissociation
                ("Liq", "Cl"): 1,      # Cl- from HCl dissociation
                ("Liq", "H2O"): 0,     # Water (unchanged)
                ("Liq", "Na"): 0,      # Na+ (unchanged)
                ("Liq", "K"): 0,       # K+ (unchanged)
                ("Liq", "Mg"): 0,      # Mg2+ (unchanged)
                ("Liq", "Li"): 0,      # Li+ (unchanged)
                ("Liq", "Ca"): 0,      # Ca2+ (unchanged)
                ("Liq", "SO4"): 0,     # SO4 2- (unchanged)
                ("Liq", "B"): 0,       # B (unchanged)
            },
            "heat_of_reaction": 0.0 * units.J / units.mol,
            "rate_form": "power_law_rate",
            "concentration_form": ConcentrationForm.molarity,
            "parameter_data": {
                "reaction_order": {
                    ("Liq", "H"): 0,
                    ("Liq", "Cl"): 0,
                    ("Liq", "H2O"): 0,
                    ("Liq", "Na"): 0,
                    ("Liq", "K"): 0,
                    ("Liq", "Mg"): 0,
                    ("Liq", "Li"): 0,
                    ("Liq", "Ca"): 0,
                    ("Liq", "SO4"): 0,
                    ("Liq", "B"): 0,
                },
                "rate_constant": 1.0e6,  # Fast reaction (essentially instantaneous)
                "rate_constant_units": units.mol / units.m**3 / units.s,
            },
        },
    },
}

# ============================================================================
# BORON EXTRACTION REACTION PACKAGE
# ============================================================================

@declare_process_block_class("BoronExtractionReactions")
class BoronExtractionReactions(ProcessBlockData):
    """
    Heterogeneous reaction package for boron extraction from aqueous to organic phase.
    """
    
    CONFIG = ProcessBlockData.CONFIG()
    CONFIG.declare(
        "dynamic",
        ConfigValue(
            default=False,
            domain=bool,
            description="Dynamic model flag - indicates if this model will be used "
            "to get a dynamic form",
            doc="""Indicates whether this model will be used to get a dynamic form,
**default** - False. The default is False.""",
        ),
    )
    
    def build(self):
        super().build()
        
        self._reaction_block_class = BoronExtractionReactionsBlock
        
        # Define elements and reactions
        self.element_list = Set(initialize=["B"])
        self.reaction_idx = Set(initialize=["B_mass_transfer"])
        
        # Define reaction stoichiometry
        reaction_stoichiometry = {}
        
        # Boron transfers from aqueous to organic phase
        reaction_stoichiometry[("B_mass_transfer", "aqueous", "B")] = -1    # B removed from aqueous
        reaction_stoichiometry[("B_mass_transfer", "organic", "B_o")] = 1    # B added to organic
        reaction_stoichiometry[("B_mass_transfer", "aqueous", "H")] = -1     # H+ consumed
        reaction_stoichiometry[("B_mass_transfer", "organic", "IsoOctanol")] = -1  # Iso-octanol consumed
        
        self.reaction_stoichiometry = reaction_stoichiometry
        
        # pH-dependent distribution coefficient parameters
        self.pH_coeff_a = Param(
            self.element_list,
            initialize={"B": 0.5},  # pH coefficient a
            units=units.dimensionless,
            doc="pH coefficient a for distribution coefficient calculation",
        )
        
        self.pH_coeff_b = Param(
            self.element_list,
            initialize={"B": 0.0},  # pH coefficient b
            units=units.dimensionless,
            doc="pH coefficient b for distribution coefficient calculation",
        )

    @classmethod
    def define_metadata(cls, obj):
        obj.add_default_units(
            {
                "time": pyo.units.s,
                "length": pyo.units.m,
                "mass": pyo.units.kg,
                "amount": pyo.units.mol,
                "temperature": pyo.units.K,
            }
        )

    @property
    def reaction_block_class(self):
        if self._reaction_block_class is not None:
            return self._reaction_block_class
        else:
            raise AttributeError(
                "{} has not assigned a ReactionBlock class to be associated "
                "with this reaction package. Please contact the developer of "
                "the reaction package.".format(self.name)
            )

    def build_reaction_block(self, *args, **kwargs):
        """
        Methods to construct a ReactionBlock associated with this
        ReactionParameterBlock. This will automatically set the parameters
        construction argument for the ReactionBlock.

        Returns:
            ReactionBlock

        """
        default = kwargs.pop("default", {})
        initialize = kwargs.pop("initialize", {})

        if initialize == {}:
            default["parameters"] = self
        else:
            for i in initialize.keys():
                initialize[i]["parameters"] = self

        return self.reaction_block_class(
            *args, **kwargs, **default, initialize=initialize
        )


class _BoronExtractionReactionsBlock(ProcessBlock):
    pass


@declare_process_block_class(
    "BoronExtractionReactionsBlock", 
    block_class=_BoronExtractionReactionsBlock
)
class BoronExtractionReactionsBlockData(ProcessBlockData):
    """
    Reaction block for boron solvent extraction.
    """
    
    CONFIG = ProcessBlockData.CONFIG()
    CONFIG.declare(
        "parameters",
        ConfigValue(
            description="A reference to an instance of the Boron Extraction Reaction Parameter Block.",
        ),
    )
    
    def build(self):
        """
        Reaction block for boron solvent extraction.
        """
        super().build()
        
        add_object_reference(self, "_params", self.config.parameters)
        
        # Distribution coefficient variable for boron
        self.distribution_coefficient = Var(
            self.params.element_list,
            initialize=1.0,
            doc="Distribution coefficient for boron"
        )
        
        # Set distribution coefficient to a fixed value for now
        # This will be replaced by a more sophisticated pH-dependent model later
        def distribution_expression(b, e):
            return b.distribution_coefficient[e] == 1.0
        
        self.distribution_expression_constraint = Constraint(
            self.params.element_list, 
            rule=distribution_expression
        )
        
        # Note: The reaction block should have the same number of variables and constraints
        # The distribution_coefficient variable is already constrained by the distribution_expression_constraint
    
    @property
    def params(self):
        return self._params

# ============================================================================
# CUSTOM MCAS STATE BLOCK
# ============================================================================

class _CustomMCASStateBlock(_MCASStateBlock):
    """
    Custom MCAS state block class.
    """
    
    def get_material_density_terms(self, p, j):
        """Create material density terms for MSContactor compatibility."""
        # Use concentration as density terms
        return self.conc_mol_phase_comp[p, j]
    
    def _conc_mol_comp(self):
        """Create conc_mol_comp property for MSContactor compatibility."""
        # Map conc_mol_phase_comp["Liq", j] to conc_mol_comp[j]
        self.conc_mol_comp = Expression(
            self.params.component_list,
            rule=lambda b, j: b.conc_mol_phase_comp["Liq", j],
            doc="Component molar concentration (summed over phases)",
        )
    
    def _pH_phase(self):
        """Create pH_phase property for reaction package compatibility."""
        # Add pH calculation based on H+ concentration
        self.pH_phase = Var(
            self.params.phase_list,
            domain=pyo.Reals,
            initialize=7.0,
            doc="pH of the solution",
            units=pyunits.dimensionless
        )
        
        @self.Constraint(self.params.phase_list)
        def pH_constraint(b, p):
            # pH = -log10([H+])
            # [H+] = 10^(-pH)
            return 10**(-b.pH_phase[p]) == b.conc_mol_phase_comp[p, "H"] * pyunits.L / pyunits.mol
    
    def initialize(self, *args, **kwargs):
        return super().initialize(*args, **kwargs)

@declare_process_block_class("CustomMCASStateBlock", block_class=_CustomMCASStateBlock)
class CustomMCASStateBlockData(MCASStateBlockData):
    """
    Custom MCAS state block that implements missing methods for MSContactor compatibility.
    """
    
    def get_material_density_terms(self, p, j):
        """Create material density terms for MSContactor compatibility."""
        # Use concentration as density terms
        return self.conc_mol_phase_comp[p, j]
    
    def _conc_mol_comp(self):
        """Create conc_mol_comp property for MSContactor compatibility."""
        # Map conc_mol_phase_comp["Liq", j] to conc_mol_comp[j]
        self.conc_mol_comp = Expression(
            self.params.component_list,
            rule=lambda b, j: b.conc_mol_phase_comp["Liq", j],
            doc="Component molar concentration (summed over phases)",
        )
    
    def _pH_phase(self):
        """Create pH_phase property for reaction package compatibility."""
        # Add pH calculation based on H+ concentration
        self.pH_phase = Var(
            self.params.phase_list,
            domain=pyo.Reals,
            initialize=7.0,
            doc="pH of the solution",
            units=pyunits.dimensionless
        )
        
        @self.Constraint(self.params.phase_list)
        def pH_constraint(b, p):
            # pH = -log10([H+])
            # [H+] = 10^(-pH)
            return 10**(-b.pH_phase[p]) == b.conc_mol_phase_comp[p, "H"] * pyunits.L / pyunits.mol

@declare_process_block_class("CustomMCASParameterBlock")
class CustomMCASParameterData(MCASParameterData):
    """
    Custom MCAS parameter block that uses the custom state block with missing methods.
    """
    
    def build(self):
        super().build()
        self._state_block_class = CustomMCASStateBlock
    
    @property
    def dens_mass(self):
        # Return a reference to the dens_mass_phase['Liq'] of the first state block
        try:
            state_block = next(iter(self._state_block.values()))
            return state_block.dens_mass_phase["Liq"]
        except Exception:
            # If no state block exists yet, create a fallback Param with units
            if not hasattr(self, "_dens_mass_fallback"):
                from pyomo.environ import Param
                self._dens_mass_fallback = Param(
                    initialize=1000.0,
                    mutable=True,
                    units=pyunits.kg / pyunits.m**3,
                    doc="Fallback density for PROMMIS compatibility",
                )
            return self._dens_mass_fallback

    @classmethod
    def define_metadata(cls, obj):
        """Define properties supported and units."""
        obj.add_properties(
            {
                "flow_mol_phase_comp": {"method": "_flow_mol_phase_comp"},
                "temperature": {"method": None},
                "pressure": {"method": None},
                "flow_mass_phase_comp": {"method": "_flow_mass_phase_comp"},
                "flow_mass_comp": {"method": "_flow_mass_comp"},
                "mass_frac_phase_comp": {"method": "_mass_frac_phase_comp"},
                "dens_mass_phase": {"method": "_dens_mass_phase"},
                "flow_vol": {"method": "_flow_vol"},
                "flow_vol_phase": {"method": "_flow_vol_phase"},
                "conc_mol_phase_comp": {"method": "_conc_mol_phase_comp"},
                "conc_mol_comp": {"method": "_conc_mol_comp"},  # Added for MSContactor compatibility
                "pH_phase": {"method": "_pH_phase"},  # Added for reaction package compatibility
                "conc_mass_phase_comp": {"method": "_conc_mass_phase_comp"},
                "mole_frac_phase_comp": {"method": "_mole_frac_phase_comp"},
                "molality_phase_comp": {"method": "_molality_phase_comp"},
                "diffus_phase_comp": {"method": "_diffus_phase_comp"},
                "visc_d_phase": {"method": "_visc_d_phase"},
                "visc_k_phase": {"method": "_visc_k_phase"},
                "pressure_osm_phase": {"method": "_pressure_osm_phase"},
                "mw_comp": {"method": "_mw_comp"},
                "act_coeff_phase_comp": {"method": "_act_coeff_phase_comp"},
                "enth_mass_phase": {"method": "_enth_mass_phase"},
                "pressure_sat": {"method": "_pressure_sat"},
            }
        )
        obj.add_default_units(
            {
                "time": pyunits.s,
                "length": pyunits.m,
                "mass": pyunits.kg,
                "amount": pyunits.mol,
                "temperature": pyunits.K,
            }
        )

# ============================================================================
# ORGANIC PROPERTY PACKAGE
# ============================================================================

@declare_process_block_class("OrganicSolventParameters")
class OrganicSolventParameterData(PhysicalParameterBlock):
    """Parameter block for organic solvent properties"""

    def build(self):
        super().build()

        self._state_block_class = OrganicSolventStateBlock

        # Define components
        self.iso_octanol = Component()
        self.kerosene = Component()
        self.B_o = Component()  # Boron in organic phase
        
        # Define component list
        self.component_list = Set(initialize=["iso_octanol", "kerosene", "B_o"])

        # Define phases
        self.Liq = LiquidPhase()
        
        # Define phase list
        self.phase_list = Set(initialize=["Liq"])

        # Define custom properties
        self.define_custom_properties()
        
        # Define molecular weights
        self.mw = Param(
            self.component_list,
            units=units.kg / units.mol,
            initialize={
                "iso_octanol": 0.13023,  # C8H18O
                "kerosene": 0.14228,      # C10H22 (approximate)
                "B_o": 10.81e-3,          # Boron in organic phase
            },
            doc="Molecular weight of components",
        )

    def define_custom_properties(self):
        """Define custom properties for organic solvent"""
        # Add density property
        self.dens_mass = Var(
            units=units.kg / units.m**3,
            doc="Mass density of organic solvent",
            initialize=850.0,
        )

        # Add flow volume property
        self.flow_vol = Var(
            units=units.L / units.min,
            doc="Volumetric flow rate",
            initialize=1.0,
        )

    @classmethod
    def define_metadata(cls, obj):
        """Define metadata for the organic solvent property package"""
        obj.add_properties(
            {
                "flow_mol_comp": {"method": None},
                "conc_mol_comp": {"method": None},
                "flow_vol": {"method": None},
                "dens_mass": {"method": None},
                "temperature": {"method": None},
                "pressure": {"method": None},
            }
        )
        obj.add_default_units(
            {
                "time": pyunits.s,
                "length": pyunits.m,
                "mass": pyunits.kg,
                "amount": pyunits.mol,
                "temperature": pyunits.K,
            }
        )

    @classmethod
    def get_material_flow_basis(cls):
        return MaterialFlowBasis.molar

class _OrganicSolventStateBlock(StateBlock):
    def fix_initialization_states(self):
        pass

    def initialize(self, *args, **kwargs):
        """Initialize the state block"""
        # For organic solvents, we typically just need to ensure state variables are set
        # No complex initialization needed for this simple property package
        return None

@declare_process_block_class("OrganicSolventStateBlock", block_class=_OrganicSolventStateBlock)
class OrganicSolventStateBlockData(StateBlockData):
    """State block for organic solvent properties"""

    def build(self):
        super().build()

        # Define state variables
        self.temperature = Var(
            units=units.K,
            doc="Temperature",
            initialize=298.15,
        )
        self.pressure = Var(
            units=units.Pa,
            doc="Pressure",
            initialize=101325.0,
        )

        # Define flow variables (molar basis to match MCAS)
        self.flow_mol_comp = Var(
            self.component_list,
            units=units.mol / units.min,
            doc="Molar flow rate of each component",
            initialize=1.0,
        )

        # Define concentration variables (molar basis)
        self.conc_mol_comp = Var(
            self.component_list,
            units=units.mol / units.L,
            doc="Molar concentration of each component",
            initialize=1.0,
        )

        # Define volume flow rate
        self.flow_vol = Var(
            units=units.L / units.min,
            doc="Volumetric flow rate",
            initialize=1.0,
        )

    def define_state_vars(self):
        """Define state variables"""
        return {
            "temperature": self.temperature,
            "pressure": self.pressure,
            "flow_mol_comp": self.flow_mol_comp,
        }

    def get_material_flow_basis(self):
        return MaterialFlowBasis.molar

    def get_material_flow_terms(self, p, j):
        """Get material flow terms for component j in phase p"""
        if j == "kerosene":
            return self.flow_vol * self.params.dens_mass / self.params.mw[j]
        else:
            return units.convert(
                self.flow_vol * self.conc_mol_comp[j],
                to_units=units.mol / units.min,
            )

    def get_material_density_terms(self, p, j):
        """Get material density terms for component j in phase p"""
        if j == "kerosene":
            return units.convert(
                self.params.dens_mass / self.params.mw[j],
                to_units=units.mol / units.m**3,
            )
        else:
            return units.convert(
                self.conc_mol_comp[j],
                to_units=units.mol / units.m**3,
            )

    def initialize(self, *args, **kwargs):
        """Initialize the state block"""
        # For organic solvents, we typically just need to ensure state variables are set
        # No complex initialization needed for this simple property package
        return None

# Set the state block class for the parameter block
# OrganicSolventParameters._state_block_class = OrganicSolventStateBlock

# ============================================================================
# FIX UNIT MODEL VARIABLES
# ============================================================================

def fix_unit_model_variables(m):
    """
    Fix the required variables for each unit model in the flowsheet.
    """
    
    # ============================================================================
    # FEED UNITS
    # ============================================================================
    
    # Feed conditions are set in separate functions
    
    # ============================================================================
    # STORAGE TANK
    # ============================================================================
    
    m.fs.brine_storage.storage_time[0].fix(24.0 * units.hour)
    m.fs.brine_storage.surge_capacity[0].fix(0.1)
    
    # ============================================================================
    # PUMP
    # ============================================================================
    
    m.fs.brine_pump.deltaP[0].fix(3e5 * units.Pa)
    m.fs.brine_pump.efficiency_pump[0].fix(0.75)
    
    # ============================================================================
    # MIXER
    # ============================================================================
    
    m.fs.acid_brine_mixer.outlet.pressure[0].fix(101325 * units.Pa)
    m.fs.acid_brine_mixer.outlet.temperature[0].fix(298.15 * units.K)
    
    # ============================================================================
    # STOICHIOMETRIC REACTOR
    # ============================================================================
    
    m.fs.acidification_reactor.rate_reaction_extent[0, "HCl_dissociation"].fix(1.0)
    
    # ============================================================================
    # SOLVENT EXTRACTION UNITS
    # ============================================================================
    
    for i in range(1, 5):  # 4 stages
        m.fs.boron_extraction.mscontactor.volume[i].fix(50.0 * units.m**3)
        m.fs.boron_extraction.area_cross_stage[i].set_value(25.0)
        m.fs.boron_extraction.elevation[i].set_value(0.0)
    
    for i in range(1, 4):  # 3 stages
        m.fs.boron_reextraction.mscontactor.volume[i].fix(40.0 * units.m**3)
        m.fs.boron_reextraction.area_cross_stage[i].value = 20.0
        m.fs.boron_reextraction.elevation[i].value = 0.0
    
    # ============================================================================
    # REACTION PACKAGE VARIABLES
    # ============================================================================
    
    m.fs.boron_extraction_reactions.pH_coeff_a["B"].value = 0.5
    m.fs.boron_extraction_reactions.pH_coeff_b["B"].value = 0.0
    
    print("Unit model variables fixed successfully!")

def set_scaling_factors(m):
    """
    Set scaling factors for the lithium processing flowsheet.
    """
    
    # ============================================================================
    # PROPERTY PACKAGE SCALING
    # ============================================================================
    
    m.fs.brine_props.set_default_scaling("flow_vol_phase", 1e-2, index=("Liq",))
    m.fs.brine_props.set_default_scaling("flow_mol_phase_comp", 1e-2, index=("Liq", "H2O"))
    m.fs.brine_props.set_default_scaling("flow_mol_phase_comp", 1e-4, index=("Liq", "Na"))
    m.fs.brine_props.set_default_scaling("flow_mol_phase_comp", 1e-4, index=("Liq", "K"))
    m.fs.brine_props.set_default_scaling("flow_mol_phase_comp", 1e-4, index=("Liq", "Mg"))
    m.fs.brine_props.set_default_scaling("flow_mol_phase_comp", 1e-4, index=("Liq", "Li"))
    m.fs.brine_props.set_default_scaling("flow_mol_phase_comp", 1e-4, index=("Liq", "Ca"))
    m.fs.brine_props.set_default_scaling("flow_mol_phase_comp", 1e-4, index=("Liq", "Cl"))
    m.fs.brine_props.set_default_scaling("flow_mol_phase_comp", 1e-4, index=("Liq", "SO4"))
    m.fs.brine_props.set_default_scaling("flow_mol_phase_comp", 1e-6, index=("Liq", "B"))
    m.fs.brine_props.set_default_scaling("flow_mol_phase_comp", 1e-6, index=("Liq", "H"))
    
    m.fs.brine_props.set_default_scaling("conc_mass_phase_comp", 1e-3, index=("Liq", "H2O"))
    m.fs.brine_props.set_default_scaling("conc_mass_phase_comp", 1e-1, index=("Liq", "Na"))
    m.fs.brine_props.set_default_scaling("conc_mass_phase_comp", 1e-2, index=("Liq", "K"))
    m.fs.brine_props.set_default_scaling("conc_mass_phase_comp", 1e-1, index=("Liq", "Mg"))
    m.fs.brine_props.set_default_scaling("conc_mass_phase_comp", 1e-1, index=("Liq", "Li"))
    m.fs.brine_props.set_default_scaling("conc_mass_phase_comp", 1e-2, index=("Liq", "Ca"))
    m.fs.brine_props.set_default_scaling("conc_mass_phase_comp", 1e-1, index=("Liq", "Cl"))
    m.fs.brine_props.set_default_scaling("conc_mass_phase_comp", 1e-3, index=("Liq", "SO4"))
    m.fs.brine_props.set_default_scaling("conc_mass_phase_comp", 1e-3, index=("Liq", "B"))
    m.fs.brine_props.set_default_scaling("conc_mass_phase_comp", 1e-9, index=("Liq", "H"))
    
    m.fs.brine_props.set_default_scaling("temperature", 1e-2)
    m.fs.brine_props.set_default_scaling("pressure", 1e-5)
    m.fs.brine_props.set_default_scaling("dens_mass_phase", 1e-3, index=("Liq",))
    
    m.fs.organic_props.set_default_scaling("flow_vol", 1e-2)
    m.fs.organic_props.set_default_scaling("flow_mol_comp", 1e-2, index="iso_octanol")
    m.fs.organic_props.set_default_scaling("flow_mol_comp", 1e-2, index="kerosene")
    m.fs.organic_props.set_default_scaling("flow_mol_comp", 1e-6, index="B_o")
    m.fs.organic_props.set_default_scaling("conc_mol_comp", 1e-1, index="iso_octanol")
    m.fs.organic_props.set_default_scaling("conc_mol_comp", 1e-1, index="kerosene")
    m.fs.organic_props.set_default_scaling("conc_mol_comp", 1e-6, index="B_o")
    m.fs.organic_props.set_default_scaling("temperature", 1e-2)
    m.fs.organic_props.set_default_scaling("pressure", 1e-5)
    m.fs.organic_props.set_default_scaling("dens_mass", 1e-3)
    
    # ============================================================================
    # REACTION SCALING
    # ============================================================================
    
    iscale.set_scaling_factor(m.fs.acidification_reactor.control_volume.rate_reaction_extent[0, "HCl_dissociation"], 1.0)
    
    # ============================================================================
    # UNIT MODEL SCALING
    # ============================================================================
    
    iscale.set_scaling_factor(m.fs.brine_storage.storage_time[0], 1e-4)
    iscale.set_scaling_factor(m.fs.brine_storage.surge_capacity[0], 10.0)
    
    iscale.set_scaling_factor(m.fs.brine_pump.deltaP[0], 1e-5)
    iscale.set_scaling_factor(m.fs.brine_pump.efficiency_pump[0], 1.0)
    iscale.set_scaling_factor(m.fs.brine_pump.control_volume.work[0], 1e-3)
    
    iscale.set_scaling_factor(m.fs.acid_brine_mixer.outlet.pressure[0], 1e-5)
    iscale.set_scaling_factor(m.fs.acid_brine_mixer.outlet.temperature[0], 1e-2)
    
    for i in range(1, 5):
        iscale.set_scaling_factor(m.fs.boron_extraction.mscontactor.volume[i], 1e-2)
    for i in range(1, 4):
        iscale.set_scaling_factor(m.fs.boron_reextraction.mscontactor.volume[i], 1e-2)
    
    for i in range(1, 5):
        iscale.set_scaling_factor(m.fs.boron_extraction.area_cross_stage[i], 1e-1)
    for i in range(1, 4):
        iscale.set_scaling_factor(m.fs.boron_reextraction.area_cross_stage[i], 1e-1)
    
    for i in range(1, 5):
        iscale.set_scaling_factor(m.fs.boron_extraction.elevation[i], 1.0)
    for i in range(1, 4):
        iscale.set_scaling_factor(m.fs.boron_reextraction.elevation[i], 1.0)
    
    iscale.set_scaling_factor(m.fs.boron_extraction_reactions.pH_coeff_a["B"], 1.0)
    iscale.set_scaling_factor(m.fs.boron_extraction_reactions.pH_coeff_b["B"], 1.0)
    
    if hasattr(m.fs.boron_extraction.mscontactor, "height"):
        for i in range(1, 5):
            iscale.set_scaling_factor(m.fs.boron_extraction.mscontactor.height[i], 1.0)
    if hasattr(m.fs.boron_reextraction.mscontactor, "height"):
        for i in range(1, 4):
            iscale.set_scaling_factor(m.fs.boron_reextraction.mscontactor.height[i], 1.0)
    
    # ============================================================================
    # FEED STREAM SCALING
    # ============================================================================
    
    iscale.set_scaling_factor(m.fs.brine_feed.properties[0].flow_vol_phase["Liq"], 1e-2)
    iscale.set_scaling_factor(m.fs.brine_feed.properties[0].temperature, 1e-2)
    iscale.set_scaling_factor(m.fs.brine_feed.properties[0].pressure, 1e-5)
    
    iscale.set_scaling_factor(m.fs.hcl_feed.properties[0].flow_vol_phase["Liq"], 1e-2)
    iscale.set_scaling_factor(m.fs.hcl_feed.properties[0].temperature, 1e-2)
    iscale.set_scaling_factor(m.fs.hcl_feed.properties[0].pressure, 1e-5)
    
    iscale.set_scaling_factor(m.fs.organic_feed.properties[0].flow_vol, 1e-2)
    iscale.set_scaling_factor(m.fs.organic_feed.properties[0].temperature, 1e-2)
    iscale.set_scaling_factor(m.fs.organic_feed.properties[0].pressure, 1e-5)
    
    iscale.set_scaling_factor(m.fs.reextraction_feed.properties[0].flow_vol_phase["Liq"], 1e-2)
    iscale.set_scaling_factor(m.fs.reextraction_feed.properties[0].temperature, 1e-2)
    iscale.set_scaling_factor(m.fs.reextraction_feed.properties[0].pressure, 1e-5)
    
    # ============================================================================
    # CALCULATE SCALING FACTORS
    # ============================================================================
    
    iscale.calculate_scaling_factors(m)
    
    print("Scaling factors set successfully!")

def build_flowsheet():
    """
    Build the lithium carbonate plant flowsheet.
    """
    
    # Create the model and flowsheet
    m = pyo.ConcreteModel()
    m.fs = FlowsheetBlock(dynamic=False)
    
    # ============================================================================
    # PROPERTY PACKAGES
    # ============================================================================
    
    m.fs.brine_props = CustomMCASParameterBlock(
        solute_list=["Na", "K", "Mg", "Li", "Ca", "Cl", "SO4", "B", "H"],
        charge={"Na": 1, "K": 1, "Mg": 2, "Li": 1, "Ca": 2, "Cl": -1, "SO4": -2, "B": 0, "H": 1},
        mw_data={
            "H2O": 18e-3,
            "Na": 23e-3,
            "K": 39.1e-3,
            "Mg": 24.3e-3,
            "Li": 6.94e-3,
            "Ca": 40.08e-3,
            "Cl": 35.45e-3,
            "SO4": 96.06e-3,
            "B": 10.81e-3,
            "H": 1.008e-3,
        },
        material_flow_basis=MaterialFlowBasis.molar,
    )
    
    m.fs.organic_props = OrganicSolventParameters()
    
    # ============================================================================
    # REACTION PACKAGES
    # ============================================================================
    
    m.fs.acidification_reactions = GenericReactionParameterBlock(
        property_package=m.fs.brine_props,
        **acidification_reaction_config
    )
    
    m.fs.boron_extraction_reactions = BoronExtractionReactions(component=m.fs)
    m.fs.boron_extraction_reactions.build()
    
    # ============================================================================
    # UNIT MODELS
    # ============================================================================
    
    m.fs.brine_feed = Feed(property_package=m.fs.brine_props)
    
    m.fs.hcl_feed = Feed(property_package=m.fs.brine_props)
    
    m.fs.organic_feed = Feed(property_package=m.fs.organic_props)
    
    m.fs.reextraction_feed = Feed(property_package=m.fs.brine_props)
    
    m.fs.brine_storage = StorageTank(
        property_package=m.fs.brine_props,
    )
    
    m.fs.brine_pump = Pump(
        property_package=m.fs.brine_props,
    )
    
    m.fs.acid_brine_mixer = Mixer(
        property_package=m.fs.brine_props,
        inlet_list=["brine_feed", "acid_feed"],
        material_balance_type=MaterialBalanceType.componentTotal,
        energy_mixing_type=MixingType.none,
        momentum_mixing_type=MomentumMixingType.none,
    )
    
    m.fs.acidification_reactor = StoichiometricReactor(
        property_package=m.fs.brine_props,
        reaction_package=m.fs.acidification_reactions,
        has_heat_of_reaction=False,
        has_heat_transfer=False,
        has_pressure_change=False,
    )
    
    m.fs.boron_extraction = SolventExtraction(
        number_of_finite_elements=4,  # Four-stage countercurrent extraction
        dynamic=False,
        aqueous_stream={
            "property_package": m.fs.brine_props,
            "flow_direction": FlowDirection.forward,
            "has_energy_balance": False,
            "has_pressure_balance": False,
        },
        organic_stream={
            "property_package": m.fs.organic_props,
            "flow_direction": FlowDirection.backward,
            "has_energy_balance": False,
            "has_pressure_balance": False,
        },
        heterogeneous_reaction_package=m.fs.boron_extraction_reactions,
        has_holdup=True,
    )
    
    m.fs.boron_reextraction = SolventExtraction(
        number_of_finite_elements=3,  # Three-stage countercurrent reextraction
        dynamic=False,
        aqueous_stream={
            "property_package": m.fs.brine_props,  # Use MCAS for NaOH solution
            "flow_direction": FlowDirection.forward,
            "has_energy_balance": False,
            "has_pressure_balance": False,
        },
        organic_stream={
            "property_package": m.fs.organic_props,
            "flow_direction": FlowDirection.backward,
            "has_energy_balance": False,
            "has_pressure_balance": False,
        },
        heterogeneous_reaction_package=m.fs.boron_extraction_reactions,  # Same reaction package (reverse direction)
        has_holdup=True,
    )
    
    # ============================================================================
    # CONNECT UNIT MODELS
    # ============================================================================
    
    m.fs.brine_feed_to_storage = Arc(source=m.fs.brine_feed.outlet, destination=m.fs.brine_storage.inlet)
    m.fs.storage_to_pump = Arc(source=m.fs.brine_storage.outlet, destination=m.fs.brine_pump.inlet)
    m.fs.pump_to_mixer = Arc(source=m.fs.brine_pump.outlet, destination=m.fs.acid_brine_mixer.brine_feed)
    m.fs.hcl_to_mixer = Arc(source=m.fs.hcl_feed.outlet, destination=m.fs.acid_brine_mixer.acid_feed)
    m.fs.mixer_to_reactor = Arc(source=m.fs.acid_brine_mixer.outlet, destination=m.fs.acidification_reactor.inlet)
    m.fs.reactor_to_extraction = Arc(source=m.fs.acidification_reactor.outlet, destination=m.fs.boron_extraction.aqueous_inlet)
    m.fs.organic_to_extraction = Arc(source=m.fs.organic_feed.outlet, destination=m.fs.boron_extraction.organic_inlet)
    m.fs.reextraction_feed_to_reextraction = Arc(source=m.fs.reextraction_feed.outlet, destination=m.fs.boron_reextraction.aqueous_inlet)
    m.fs.extraction_organic_to_reextraction = Arc(source=m.fs.boron_extraction.organic_outlet, destination=m.fs.boron_reextraction.organic_inlet)
    
    TransformationFactory("network.expand_arcs").apply_to(m)
    
    # ============================================================================
    # SET CONDITIONS
    # ============================================================================
    
    set_brine_feed_conditions(m)
    set_hcl_feed_conditions(m)
    set_organic_feed_conditions(m)
    set_reextraction_feed_conditions(m)
    fix_unit_model_variables(m)
    set_scaling_factors(m)
    
    return m

def set_brine_feed_conditions(m):
    """
    Set the brine feed conditions.
    """
    
    # Reference conditions
    T_ref = 298.15 * pyunits.K  # 25°C
    P_ref = 101325 * pyunits.Pa  # 1 atm
    
    # Set temperature and pressure (state variables)
    m.fs.brine_feed.properties[0].temperature.fix(T_ref)
    m.fs.brine_feed.properties[0].pressure.fix(P_ref)
    
    # Calculate total flow rate based on industrial-scale operation
    total_flow_vol = 1000 * pyunits.L / pyunits.minute
    total_flow_vol = pyo.units.convert(total_flow_vol, to_units=pyunits.L/pyunits.s)
    
    # Density = 1.252 kg/L = 1252 g/L
    density = 1252 * pyunits.g / pyunits.L
    
    # MWs in g/mol (with pyunits)
    MW = {
        "Na": 23.0 * pyunits.g/pyunits.mol,
        "K": 39.1 * pyunits.g/pyunits.mol,
        "Mg": 24.3 * pyunits.g/pyunits.mol,
        "Li": 6.94 * pyunits.g/pyunits.mol,
        "Ca": 40.08 * pyunits.g/pyunits.mol,
        "Cl": 35.45 * pyunits.g/pyunits.mol,
        "SO4": 96.06 * pyunits.g/pyunits.mol,
        "B": 10.81 * pyunits.g/pyunits.mol,
        "H2O": 18.0 * pyunits.g/pyunits.mol,
        "H": 1.008 * pyunits.g/pyunits.mol,
    }
    ppm = {
        "Na": 570,
        "K": 160,
        "Mg": 19200,
        "Li": 60000,
        "Ca": 530,
        "Cl": 351000,
        "SO4": 220,
        "B": 6270,
    }
    # Calculate molar flow rates for each solute
    for comp in ppm:
        conc_g_L = ppm[comp] * density / 1e6  # g/L
        conc_mol_L = conc_g_L / MW[comp]      # mol/L
        flow_mol_s = conc_mol_L * total_flow_vol  # mol/s
        m.fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", comp].fix(pyo.value(flow_mol_s))
    # H+ from pH
    H_conc_mol_L = 3.16e-7 * pyunits.mol / pyunits.L
    H_flow_mol_s = H_conc_mol_L * total_flow_vol
    m.fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", "H"].fix(pyo.value(H_flow_mol_s))
    # Water: density - sum of all solute concentrations
    total_solute_g_L = sum(ppm[c] * density / 1e6 for c in ppm) + H_conc_mol_L * MW["H"]
    water_g_L = density - total_solute_g_L
    water_conc_mol_L = water_g_L / MW["H2O"]
    water_flow_mol_s = water_conc_mol_L * total_flow_vol
    m.fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", "H2O"].fix(pyo.value(water_flow_mol_s))

def set_hcl_feed_conditions(m):
    """
    Set the HCl acid feed conditions.
    """
    
    # Reference conditions
    T_ref = 298.15 * pyunits.K  # 25°C
    P_ref = 101325 * pyunits.Pa  # 1 atm
    
    # Set temperature and pressure
    m.fs.hcl_feed.properties[0].temperature.fix(T_ref)
    m.fs.hcl_feed.properties[0].pressure.fix(P_ref)
    
    # Set flow rate based on target 0.1 N H+ in final mixture
    # For industrial-scale operation, using 100 L/min for HCl feed
    # This will achieve approximately 0.1 N H+ concentration in the mixed stream
    total_flow_vol = 100 * pyunits.L / pyunits.minute
    total_flow_vol = pyo.units.convert(total_flow_vol, to_units=pyunits.L/pyunits.s)  # Convert to L/s
    
    # HCl concentration: 12 M HCl (concentrated hydrochloric acid)
    # 12 M = 12 mol/L
    HCl_conc_mol_L = 12.0 * pyunits.mol / pyunits.L
    
    # Convert to molar flow rate
    HCl_flow_mol_s = HCl_conc_mol_L * total_flow_vol
    m.fs.hcl_feed.properties[0].flow_mol_phase_comp["Liq", "H"].fix(pyo.value(HCl_flow_mol_s))
    
    # Cl- concentration (same as HCl concentration)
    Cl_flow_mol_s = HCl_conc_mol_L * total_flow_vol
    m.fs.hcl_feed.properties[0].flow_mol_phase_comp["Liq", "Cl"].fix(pyo.value(Cl_flow_mol_s))
    
    # Set other components to zero (HCl feed contains only HCl and H2O)
    m.fs.hcl_feed.properties[0].flow_mol_phase_comp["Liq", "Na"].fix(0.0)
    m.fs.hcl_feed.properties[0].flow_mol_phase_comp["Liq", "K"].fix(0.0)
    m.fs.hcl_feed.properties[0].flow_mol_phase_comp["Liq", "Mg"].fix(0.0)
    m.fs.hcl_feed.properties[0].flow_mol_phase_comp["Liq", "Li"].fix(0.0)
    m.fs.hcl_feed.properties[0].flow_mol_phase_comp["Liq", "Ca"].fix(0.0)
    m.fs.hcl_feed.properties[0].flow_mol_phase_comp["Liq", "SO4"].fix(0.0)
    m.fs.hcl_feed.properties[0].flow_mol_phase_comp["Liq", "B"].fix(0.0)
    
    # Set water concentration (remaining mass)
    # Density of 12 M HCl ≈ 1.18 g/mL = 1180 g/L
    density = 1180 * pyunits.g / pyunits.L
    
    # MWs with pyunits
    MW = {
        "H": 1.008 * pyunits.g/pyunits.mol,
        "Cl": 35.45 * pyunits.g/pyunits.mol,
        "H2O": 18.0 * pyunits.g/pyunits.mol,
    }
    
    # Calculate water concentration and flow
    HCl_conc_g_L = HCl_conc_mol_L * MW["H"]  # g/L of H+
    Cl_conc_g_L = HCl_conc_mol_L * MW["Cl"]   # g/L of Cl-
    total_solute_g_L = HCl_conc_g_L + Cl_conc_g_L
    water_g_L = density - total_solute_g_L
    water_conc_mol_L = water_g_L / MW["H2O"]
    water_flow_mol_s = water_conc_mol_L * total_flow_vol
    m.fs.hcl_feed.properties[0].flow_mol_phase_comp["Liq", "H2O"].fix(pyo.value(water_flow_mol_s))

def set_organic_feed_conditions(m):
    """Set organic feed conditions"""
    # Temperature and pressure
    m.fs.organic_feed.properties[0].temperature.fix(298.15 * pyunits.K)
    m.fs.organic_feed.properties[0].pressure.fix(101325.0 * pyunits.Pa)
    
    # Flow rate: 1000 L/min (one-to-one volume ratio with acidified brine)
    # Based on Chilean study scaled to industrial: one-to-one (by volume) ratio of solvent to acidified brine
    total_flow_vol = 1000.0 * pyunits.L / pyunits.min
    total_flow_vol = pyo.units.convert(total_flow_vol, to_units=pyunits.L/pyunits.s)  # Convert to L/s
    
    # Composition: 50% iso-octanol + 50% kerosene by volume
    # Molecular weights: iso-octanol = 130.23 g/mol, kerosene = 142.29 g/mol
    # Densities: iso-octanol = 0.83 g/mL, kerosene = 0.81 g/mL
    # For 50% by volume mixture:
    # iso-octanol: 415 kg/m³ / 130.23 g/mol = 3.19 mol/L
    # kerosene: 405 kg/m³ / 142.29 g/mol = 2.85 mol/L
    
    # Convert concentrations to molar flow rates
    iso_octanol_conc_mol_L = 3.19 * pyunits.mol / pyunits.L
    kerosene_conc_mol_L = 2.85 * pyunits.mol / pyunits.L
    
    iso_octanol_flow_mol_s = iso_octanol_conc_mol_L * total_flow_vol
    kerosene_flow_mol_s = kerosene_conc_mol_L * total_flow_vol
    
    m.fs.organic_feed.properties[0].flow_mol_comp["iso_octanol"].fix(pyo.value(iso_octanol_flow_mol_s))
    m.fs.organic_feed.properties[0].flow_mol_comp["kerosene"].fix(pyo.value(kerosene_flow_mol_s))
    
    # Set boron in organic phase to zero initially
    m.fs.organic_feed.properties[0].flow_mol_comp["B_o"].fix(0.0)

def set_reextraction_feed_conditions(m):
    """
    Set the reextraction feed conditions.
    """
    
    # Reference conditions
    T_ref = 298.15 * units.K  # 25°C
    P_ref = 101325 * units.Pa  # 1 atm
    
    # Set temperature and pressure
    m.fs.reextraction_feed.properties[0].temperature.fix(T_ref)
    m.fs.reextraction_feed.properties[0].pressure.fix(P_ref)
    
    # Set flow rate for reextraction feed
    # Using 500 L/min for reextraction (typically less than extraction flow)
    flow_rate = 500 * units.L / units.minute
    m.fs.reextraction_feed.properties[0].flow_vol_phase["Liq"].fix(flow_rate)
    
    # Density of 0.02 N NaOH solution
    # Density = 1.02 g/mL = 1020 g/L
    density = 1020 * units.g / units.L
    
    # Calculate NaOH concentration for 0.02 N NaOH
    # 0.02 N = 0.02 mol/L NaOH
    NaOH_conc_mol = 0.02 * units.mol / units.L
    
    # Convert to mass concentration (NaOH has MW = 40 g/mol)
    NaOH_conc_mass = NaOH_conc_mol * 40 * units.g / units.mol
    m.fs.reextraction_feed.properties[0].conc_mass_phase_comp["Liq", "Na"].fix(NaOH_conc_mass)
    
    # Set H+ concentration based on pH = 12.3 (basic)
    # pH = -log10([H+])
    # [H+] = 10^(-pH) = 10^(-12.3) = 5.01e-13 mol/L
    H_conc_mol = 5.01e-13 * units.mol / units.L
    # Convert to mass concentration (H+ has MW = 1.008 g/mol)
    H_conc_mass = H_conc_mol * 1.008 * units.g / units.mol
    m.fs.reextraction_feed.properties[0].conc_mass_phase_comp["Liq", "H"].fix(H_conc_mass)
    
    # Set other components to zero (NaOH solution contains only NaOH and H2O)
    m.fs.reextraction_feed.properties[0].conc_mass_phase_comp["Liq", "K"].fix(0 * units.g / units.L)
    m.fs.reextraction_feed.properties[0].conc_mass_phase_comp["Liq", "Mg"].fix(0 * units.g / units.L)
    m.fs.reextraction_feed.properties[0].conc_mass_phase_comp["Liq", "Li"].fix(0 * units.g / units.L)
    m.fs.reextraction_feed.properties[0].conc_mass_phase_comp["Liq", "Ca"].fix(0 * units.g / units.L)
    m.fs.reextraction_feed.properties[0].conc_mass_phase_comp["Liq", "SO4"].fix(0 * units.g / units.L)
    m.fs.reextraction_feed.properties[0].conc_mass_phase_comp["Liq", "B"].fix(0 * units.g / units.L)
    
    # Set Cl- concentration (minimal in NaOH solution)
    Cl_conc_mass = 1e-7 * units.g / units.L
    m.fs.reextraction_feed.properties[0].conc_mass_phase_comp["Liq", "Cl"].fix(Cl_conc_mass)
    
    # Set water concentration (remaining mass)
    total_conc = NaOH_conc_mass + H_conc_mass + Cl_conc_mass
    water_conc = density - total_conc
    m.fs.reextraction_feed.properties[0].conc_mass_phase_comp["Liq", "H2O"].fix(water_conc)

def check_unfixed_variables(block, name="block"):
    """Check which variables are not fixed in a block."""
    from idaes.core.util.model_statistics import degrees_of_freedom
    
    print(f"\n=== Checking unfixed variables in {name} ===")
    print(f"Total DOF: {degrees_of_freedom(block)}")
    
    unfixed_vars = []
    for var in block.component_objects(pyo.Var, descend_into=True):
        if hasattr(var, 'is_fixed'):
            # Scalar variable
            if not var.is_fixed():
                unfixed_vars.append(var.name)
        else:
            # Indexed variable - check each index
            for idx in var:
                if not var[idx].is_fixed():
                    unfixed_vars.append(f"{var.name}[{idx}]")
    
    if unfixed_vars:
        print(f"Unfixed variables ({len(unfixed_vars)}):")
        for var_name in unfixed_vars:
            print(f"  - {var_name}")
    else:
        print("All variables are fixed!")
    
    return unfixed_vars

def main():
    """
    Main function to build and run the flowsheet.
    """
    print("Building lithium carbonate plant flowsheet...")
    
    # Build the flowsheet
    m = build_flowsheet()
    
    print("Flowsheet built successfully!")
    print(f"Number of variables: {len(list(m.fs.component_data_objects(pyo.Var)))}")
    print(f"Number of constraints: {len(list(m.fs.component_data_objects(pyo.Constraint)))}")
    
    # ============================================================================
    # INITIALIZATION SEQUENCE
    # ============================================================================
    
    print("\n" + "="*60)
    print("INITIALIZATION SEQUENCE")
    print("="*60)
    
    # Initialize brine feed
    print("\n1. Initializing brine feed...")
    m.fs.brine_feed.initialize()
    m.fs.brine_feed.report()
    
    # Check for unfixed variables in the feed block
    check_unfixed_variables(m.fs.brine_feed.properties[0], "brine_feed.properties[0]")
    
    # Propagate state to storage tank
    print("\n2. Propagating state to storage tank...")
    propagate_state(m.fs.brine_feed_to_storage)
    m.fs.brine_storage.initialize()
    m.fs.brine_storage.report()
    
    # Propagate state to pump
    print("\n3. Propagating state to pump...")
    propagate_state(m.fs.storage_to_pump)
    m.fs.brine_pump.initialize()
    m.fs.brine_pump.report()
    
    # Propagate state to mixer (brine side)
    print("\n4. Propagating state to mixer (brine side)...")
    propagate_state(m.fs.pump_to_mixer)
    
    # Initialize HCl feed
    print("\n5. Initializing HCl feed...")
    m.fs.hcl_feed.initialize()
    m.fs.hcl_feed.report()
    
    # Propagate state to mixer (acid side)
    print("\n6. Propagating state to mixer (acid side)...")
    propagate_state(m.fs.hcl_to_mixer)
    
    # Initialize mixer
    print("\n7. Initializing mixer...")
    m.fs.acid_brine_mixer.initialize()
    m.fs.acid_brine_mixer.report()
    
    # Propagate state to acidification reactor
    print("\n8. Propagating state to acidification reactor...")
    propagate_state(m.fs.mixer_to_reactor)
    m.fs.acidification_reactor.initialize()
    m.fs.acidification_reactor.report()
    
    # Initialize organic feed
    print("\n9. Initializing organic feed...")
    m.fs.organic_feed.initialize()
    m.fs.organic_feed.report()
    
    # Propagate state to boron extraction (aqueous stream)
    print("\n10. Propagating state to boron extraction (aqueous stream)...")
    propagate_state(m.fs.reactor_to_extraction)
    
    # Propagate state to boron extraction (organic stream)
    print("\n11. Propagating state to boron extraction (organic stream)...")
    propagate_state(m.fs.organic_to_extraction)
    
    # Initialize boron extraction
    print("\n12. Initializing boron extraction...")
    
    # # # Check DOF and unfixed variables in MSContactor
    # from idaes.core.util.model_statistics import degrees_of_freedom
    # print(f"MSContactor DOF before initialization: {degrees_of_freedom(m.fs.boron_extraction.mscontactor)}")
    
    # # Check what variables are unfixed in the MSContactor
    # print("\nUnfixed variables in MSContactor:")
    # unfixed_count = 0
    # for var in m.fs.boron_extraction.mscontactor.component_objects(pyo.Var, descend_into=True):
    #     if hasattr(var, 'is_fixed'):
    #         # Scalar variable
    #         if not var.is_fixed():
    #             print(f"  - {var.name}")
    #             unfixed_count += 1
    #     else:
    #         # Indexed variable - check each index
    #         for idx in var:
    #             if not var[idx].is_fixed():
    #                 print(f"  - {var.name}[{idx}]")
    #                 unfixed_count += 1
    
    # print(f"Total unfixed variables: {unfixed_count}")
    
    # # Check active constraints in the MSContactor
    # print("\nActive constraints in MSContactor:")
    # active_count = 0
    # for con in m.fs.boron_extraction.mscontactor.component_objects(pyo.Constraint, descend_into=True):
    #     if hasattr(con, 'active'):
    #         # Scalar constraint
    #         if con.active:
    #             print(f"  - {con.name}")
    #             active_count += 1
    #     else:
    #         # Indexed constraint - check each index
    #         for idx in con:
    #             if con[idx].active:
    #                 print(f"  - {con.name}[{idx}]")
    #                 active_count += 1
    
    # print(f"Total active constraints: {active_count}")
    
    # # Debug: Check pH values and distribution coefficient constraints before initializer
    # print("\n" + "="*60)
    # print("DEBUGGING pH AND DISTRIBUTION COEFFICIENT BEFORE INITIALIZER")
    # print("="*60)
    
    # # Check pH values for each stage
    # for i in range(1, 5):  # 4 stages (1-4)
    #     try:
    #         # Get the aqueous state block for this stage
    #         aqueous_state = m.fs.boron_extraction.mscontactor.aqueous[0, i]
    #         if hasattr(aqueous_state, 'pH_phase'):
    #             pH_val = pyo.value(aqueous_state.pH_phase["Liq"])
    #             print(f"Stage {i} pH: {pH_val:.2f}")
    #         else:
    #             print(f"Stage {i}: No pH_phase property found")
    #     except Exception as e:
    #         print(f"Stage {i}: Error getting pH - {e}")
    
    # # Check distribution coefficient constraints
    # print("\nDistribution coefficient constraints:")
    # for i in range(1, 5):  # 4 stages (1-4)
    #     try:
    #         reaction_block = m.fs.boron_extraction.mscontactor.heterogeneous_reactions[0, i]
    #         if hasattr(reaction_block, 'distribution_expression_constraint'):
    #             constraint = reaction_block.distribution_expression_constraint["B"]
    #             print(f"Stage {i} distribution constraint: {constraint}")
    #             print(f"  - Constraint active: {constraint.active}")
    #             print(f"  - Distribution coefficient value: {pyo.value(reaction_block.distribution_coefficient['B'])}")
    #         else:
    #             print(f"Stage {i}: No distribution_expression_constraint found")
    #     except Exception as e:
    #         print(f"Stage {i}: Error checking distribution constraint - {e}")
    
    # # Check if distribution coefficients are fixed
    # print("\nDistribution coefficient fixed status:")
    # for i in range(1, 5):  # 4 stages (1-4)
    #     var = m.fs.boron_extraction.mscontactor.heterogeneous_reactions[0, i].distribution_coefficient["B"]
    #     print(f"Stage {i}: fixed={var.fixed}, value={pyo.value(var)}")

    # Use the default initializer for solvent extraction units
    # m.fs.boron_extraction.mscontactor.report() #volume.pprint()
    boron_init = m.fs.boron_extraction.default_initializer()
    boron_init.initialize(m.fs.boron_extraction)

    m.fs.boron_extraction.report()
    
    # # Initialize reextraction feed
    # print("\n13. Initializing reextraction feed...")
    # m.fs.reextraction_feed.initialize()
    # m.fs.reextraction_feed.report()
    
    # # Propagate state to reextraction (aqueous stream)
    # print("\n14. Propagating state to reextraction (aqueous stream)...")
    # propagate_state(m.fs.extraction_to_reextraction)
    # propagate_state(m.fs.reextraction_feed_to_reextraction)
    
    # # Propagate state to reextraction (organic stream)
    # print("\n15. Propagating state to reextraction (organic stream)...")
    # propagate_state(m.fs.extraction_organic_to_reextraction)
    
    # # Initialize boron reextraction
    # print("\n16. Initializing boron reextraction...")
    # m.fs.boron_reextraction.initialize()
    # m.fs.boron_reextraction.report()
    
    # Check degrees of freedom
    print("\n" + "="*60)
    print("INITIALIZATION COMPLETE")
    print("="*60)
    
    # Print feed conditions summary
    print("\nBrine Feed Conditions:")
    print(f"Temperature: {pyo.value(m.fs.brine_feed.properties[0].temperature)} K")
    print(f"Pressure: {pyo.value(m.fs.brine_feed.properties[0].pressure)} Pa")
    print(f"Flow rate: {pyo.value(m.fs.brine_feed.properties[0].flow_vol_phase['Liq'])} m³/s ({pyo.value(m.fs.brine_feed.properties[0].flow_vol_phase['Liq']) * 60000:.0f} L/min)")
    print(f"pH: 6.50")
    print(f"Density: 1.252 kg/L")
    
    print("\nHCl Feed Conditions:")
    print(f"Temperature: {pyo.value(m.fs.hcl_feed.properties[0].temperature)} K")
    print(f"Pressure: {pyo.value(m.fs.hcl_feed.properties[0].pressure)} Pa")
    print(f"Flow rate: {pyo.value(m.fs.hcl_feed.properties[0].flow_vol_phase['Liq'])} m³/s ({pyo.value(m.fs.hcl_feed.properties[0].flow_vol_phase['Liq']) * 6000:.0f} L/min)")
    print(f"HCl concentration: 12 M (concentrated hydrochloric acid)")
    print(f"pH: ~-1.08 (very acidic)")
    print(f"Density: 1.18 g/mL")
    
    print("\nOrganic Feed Conditions:")
    print(f"Temperature: {pyo.value(m.fs.organic_feed.properties[0].temperature)} K")
    print(f"Pressure: {pyo.value(m.fs.organic_feed.properties[0].pressure)} Pa")
    print(f"Flow rate: {pyo.value(m.fs.organic_feed.properties[0].flow_vol)} L/min")
    print(f"Density: 0.85 g/mL")
    print(f"Composition: 50% iso-octanol + 50% kerosene by volume")
    print(f"Iso-octanol concentration: {pyo.value(m.fs.organic_feed.properties[0].conc_mol_comp['iso_octanol'])} mol/L")
    print(f"Kerosene concentration: {pyo.value(m.fs.organic_feed.properties[0].conc_mol_comp['kerosene'])} mol/L")
    
    print("\nReextraction Feed Conditions:")
    print(f"Temperature: {pyo.value(m.fs.reextraction_feed.properties[0].temperature)} K")
    print(f"Pressure: {pyo.value(m.fs.reextraction_feed.properties[0].pressure)} Pa")
    print(f"Flow rate: {pyo.value(m.fs.reextraction_feed.properties[0].flow_vol_phase['Liq'])} m³/s ({pyo.value(m.fs.reextraction_feed.properties[0].flow_vol_phase['Liq']) * 60000:.0f} L/min)")
    print(f"Density: 1.02 g/mL")
    print(f"Composition: 0.02 N NaOH solution")
    print(f"pH: ~12.3 (basic)")
    print(f"NaOH concentration: {pyo.value(m.fs.reextraction_feed.properties[0].conc_mass_phase_comp['Liq', 'Na'])} g/L")
    
    print("\n" + "="*60)
    print("UNIT MODEL FIXED VARIABLES SUMMARY")
    print("="*60)
    print("Storage Tank:")
    print(f"  - Storage time: {pyo.value(m.fs.brine_storage.storage_time[0])} hours")
    print(f"  - Surge capacity: {pyo.value(m.fs.brine_storage.surge_capacity[0])*100:.1f}%")
    
    print("\nPump:")
    print(f"  - Pressure increase: {pyo.value(m.fs.brine_pump.deltaP[0])/1e5:.1f} bar")
    print(f"  - Efficiency: {pyo.value(m.fs.brine_pump.efficiency_pump[0])*100:.1f}%")
    
    print("\nMixer:")
    print(f"  - Outlet pressure: {pyo.value(m.fs.acid_brine_mixer.outlet.pressure[0])/1e5:.2f} bar")
    print(f"  - Outlet temperature: {pyo.value(m.fs.acid_brine_mixer.outlet.temperature[0]):.1f} K")
    
    print("\nStoichiometric Reactor:")
    print(f"  - HCl dissociation extent: {pyo.value(m.fs.acidification_reactor.rate_reaction_extent[0, 'HCl_dissociation']):.1f}")
    
    print("\nSolvent Extraction Units:")
    print(f"  - Boron extraction tank volumes: {[pyo.value(m.fs.boron_extraction.mscontactor.volume[i]) for i in range(1, 5)]} m³")
    print(f"  - Boron reextraction tank volumes: {[pyo.value(m.fs.boron_reextraction.mscontactor.volume[i]) for i in range(1, 4)]} m³")
    print(f"  - pH coefficient a (B): {pyo.value(m.fs.boron_extraction_reactions.pH_coeff_a['B']):.1f}")
    print(f"  - pH coefficient b (B): {pyo.value(m.fs.boron_extraction_reactions.pH_coeff_b['B']):.1f}")
    print(f"  - Target boron reduction: < 5 ppm (from 6270 ppm)")
    print(f"  - Solvent composition: 50% iso-octanol + 50% kerosene")
    print(f"  - Flow ratio: 1:1 (solvent:acidified brine)")
    
    print("\n" + "="*60)
    print("SCALING FACTORS SUMMARY")
    print("="*60)
    print("Property Package Scaling:")
    print(f"  - Flow rates: 1e-2 (m³/s)")
    print(f"  - Concentrations: 1e-1 to 1e-9 (g/L)")
    print(f"  - Temperature: 1e-2 (K)")
    print(f"  - Pressure: 1e-5 (Pa)")
    print(f"  - Density: 1e-3 (kg/m³)")
    
    print("\nReaction Scaling:")
    print(f"  - HCl dissociation: 1.0 (stoichiometric)")
    print(f"  - Boron distribution: 1e-1")
    
    print("\nUnit Model Scaling:")
    print(f"  - Storage time: 1e-4 (s)")
    print(f"  - Pump work: 1e-3 (W)")
    print(f"  - Tank volumes: 1e-2 (m³)")
    print(f"  - Cross-sectional areas: 1e-1 (m²)")
    
    print("\nFeed Stream Scaling:")
    print(f"  - All flow rates: 1e-2 (m³/s)")
    print(f"  - All temperatures: 1e-2 (K)")
    print(f"  - All pressures: 1e-5 (Pa)")
    
    return m

if __name__ == "__main__":
    m = main()
