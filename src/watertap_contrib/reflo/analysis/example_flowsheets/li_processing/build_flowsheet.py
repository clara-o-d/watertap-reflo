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
)

# WaterTAP unit models
from watertap.unit_models.zero_order.storage_tank_zo import StorageTankZO as StorageTank
from watertap.unit_models.pressure_changer import Pump

# PROMMIS imports (will be added when we get to solvent extraction)
from prommis.solvent_extraction.solvent_extraction import SolventExtraction
from idaes.core import FlowDirection

# ============================================================================
# ACIDIFICATION REACTION PACKAGE FOR HCl DISSOCIATION
# ============================================================================

# Acidification reaction package configuration
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
# BORON EXTRACTION HETEROGENEOUS REACTION PACKAGE
# ============================================================================

@declare_process_block_class("BoronExtractionReactions")
class BoronExtractionReactions(ProcessBlockData):
    """
    Heterogeneous reaction package for boron extraction from aqueous to organic phase.
    
    This reaction package defines the mass transfer of boron from the aqueous phase
    to the organic phase during solvent extraction. The distribution coefficient
    is defined as the ratio of the concentration in the organic phase to the
    concentration in the aqueous phase.
    
    D[B] = C_organic[B]/C_aqueous[B]
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
        
        # Distribution coefficient parameters
        self.distribution_coefficient = Param(
            self.element_list,
            initialize={"B": 10.0},  # pH-dependent distribution coefficient
            units=units.dimensionless,
            doc="Distribution coefficient for boron extraction",
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
        
        def distribution_expression(b, e):
            """
            Distribution coefficient expression for boron extraction.
            Based on pH-dependent extraction with iso-octanol.
            """
            # Use the distribution coefficient parameter directly
            return b.distribution_coefficient[e] == b.params.distribution_coefficient[e]
        
        self.distribution_expression_constraint = Constraint(
            self.params.element_list, 
            rule=distribution_expression
        )
    
    @property
    def params(self):
        return self._params

# ============================================================================
# CUSTOM MCAS STATE BLOCK WITH MISSING METHODS
# ============================================================================

@declare_process_block_class("CustomMCASStateBlock", block_class=StateBlock)
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
# ORGANIC PROPERTY PACKAGE FOR ISO-OCTANOL/KEROSENE MIXTURE
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

@declare_process_block_class("OrganicSolventStateBlock", block_class=StateBlock)
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

# Set the state block class for the parameter block
# OrganicSolventParameters._state_block_class = OrganicSolventStateBlock

# ============================================================================
# FIX REQUIRED VARIABLES FOR UNIT MODELS
# ============================================================================

def fix_unit_model_variables(m):
    """
    Fix the required variables for each unit model in the flowsheet.
    
    This function fixes the degrees of freedom for each unit model based on
    IDAES, WaterTAP, and PROMMIS documentation and best practices.
    
    Parameters are adjusted based on the Chilean laboratory study by Orrego et al. (1994),
    scaled up to industrial operation at Salar de Atacama lithium processing plant:
    - 50 vol% iso-octanol with kerosene
    - One-to-one (by volume) ratio of solvent to acidified brine
    - Four countercurrent extraction stages
    - Target: reduce boron to less than 5 ppm
    - Three stages of reextraction with 0.02 N NaOH
    """
    
    # ============================================================================
    # FEED UNITS - Fix inlet state variables
    # ============================================================================
    
    # Brine feed - all state variables are already fixed in set_brine_feed_conditions()
    # HCl feed - all state variables are already fixed in set_hcl_feed_conditions()
    # Organic feed - all state variables are already fixed in set_organic_feed_conditions()
    # Reextraction feed - all state variables are already fixed in set_reextraction_feed_conditions()
    
    # ============================================================================
    # STORAGE TANK - Fix performance variables
    # ============================================================================
    
    # Storage tank performance variables
    m.fs.brine_storage.storage_time[0].fix(24.0 * units.hour)  # 24 hour storage time
    m.fs.brine_storage.surge_capacity[0].fix(0.1)  # 10% surge capacity
    
    # ============================================================================
    # PUMP - Fix pressure and efficiency variables
    # ============================================================================
    
    # Pump pressure difference (outlet pressure - inlet pressure)
    # Industrial-scale pressure increase for Salar de Atacama plant
    m.fs.brine_pump.deltaP[0].fix(3e5 * units.Pa)  # 3 bar pressure increase
    
    # Pump efficiency (isentropic efficiency)
    m.fs.brine_pump.efficiency_pump[0].fix(0.75)  # 75% efficiency
    
    # ============================================================================
    # MIXER - Fix outlet state variables
    # ============================================================================
    
    # Mixer outlet pressure (use minimum of inlet pressures)
    m.fs.acid_brine_mixer.outlet.pressure[0].fix(101325 * units.Pa)
    
    # Mixer outlet temperature (use average of inlet temperatures)
    m.fs.acid_brine_mixer.outlet.temperature[0].fix(298.15 * units.K)
    
    # ============================================================================
    # STOICHIOMETRIC REACTOR - Fix reaction extent
    # ============================================================================
    
    # Acidification reactor - HCl dissociation reaction extent
    # This reaction is essentially instantaneous, so we fix the extent to 1.0
    # (complete reaction)
    m.fs.acidification_reactor.rate_reaction_extent[0, "HCl_dissociation"].fix(1.0)
    
    # ============================================================================
    # SOLVENT EXTRACTION UNITS - Fix volume and performance variables
    # ============================================================================
    
    # Boron extraction unit - fix tank volumes for each stage
    # Industrial-scale volumes based on Chilean study scaled up to Salar de Atacama plant
    for i in range(1, 5):  # 4 stages (1-4)
        m.fs.boron_extraction.mscontactor.volume[i].fix(50.0 * units.m**3)  # 50 m³ per stage
    
    # Boron extraction unit - set cross-sectional area and elevation (these are Parameters, not Variables)
    m.fs.boron_extraction.area_cross_stage[1].value = 25.0  # 25 m² cross-sectional area
    m.fs.boron_extraction.elevation[1].value = 0.0
    
    # Boron reextraction unit - fix tank volumes for each stage
    for i in range(1, 4):  # 3 stages (1-3)
        m.fs.boron_reextraction.mscontactor.volume[i].fix(40.0 * units.m**3)  # 40 m³ per stage
    
    # Boron reextraction unit - set cross-sectional area and elevation (these are Parameters, not Variables)
    m.fs.boron_reextraction.area_cross_stage[1].value = 20.0  # 20 m² cross-sectional area
    m.fs.boron_reextraction.elevation[1].value = 0.0
    
    # ============================================================================
    # REACTION PACKAGE VARIABLES - Fix distribution coefficients
    # ============================================================================
    
    # Set distribution coefficient for boron extraction (this is a Parameter, not a Variable)
    # Based on Chilean study with iso-octanol at pH ~1 (0.1 N H+)
    # Distribution coefficient for boron with iso-octanol typically ranges from 8-12
    # at acidic pH conditions
    m.fs.boron_extraction_reactions.distribution_coefficient["B"].value = 9.5
    
    print("Unit model variables fixed successfully!")

def set_scaling_factors(m):
    """
    Set scaling factors for the lithium processing flowsheet.
    
    This function sets appropriate scaling factors for all variables and constraints
    to ensure proper numerical conditioning for the solver.
    """
    
    # ============================================================================
    # PROPERTY PACKAGE SCALING - Set default scaling for chemical species
    # ============================================================================
    
    # Set default scaling for brine properties (MCAS)
    # Flow rates are typically in m³/s, so scale by 1e-2 to get values around 1
    m.fs.brine_props.set_default_scaling("flow_vol_phase", 1e-2, index=("Liq",))
    m.fs.brine_props.set_default_scaling("flow_mol_phase_comp", 1e-2, index=("Liq", "H2O"))
    m.fs.brine_props.set_default_scaling("flow_mol_phase_comp", 1e-4, index=("Liq", "Na"))
    m.fs.brine_props.set_default_scaling("flow_mol_phase_comp", 1e-4, index=("Liq", "K"))
    m.fs.brine_props.set_default_scaling("flow_mol_phase_comp", 1e-4, index=("Liq", "Mg"))
    m.fs.brine_props.set_default_scaling("flow_mol_phase_comp", 1e-4, index=("Liq", "Li"))
    m.fs.brine_props.set_default_scaling("flow_mol_phase_comp", 1e-4, index=("Liq", "Ca"))
    m.fs.brine_props.set_default_scaling("flow_mol_phase_comp", 1e-4, index=("Liq", "Cl"))
    m.fs.brine_props.set_default_scaling("flow_mol_phase_comp", 1e-4, index=("Liq", "SO4"))
    m.fs.brine_props.set_default_scaling("flow_mol_phase_comp", 1e-6, index=("Liq", "B"))  # Boron is trace
    m.fs.brine_props.set_default_scaling("flow_mol_phase_comp", 1e-6, index=("Liq", "H"))  # H+ is dilute
    
    # Concentration scaling (mass concentrations in g/L)
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
    
    # Temperature and pressure scaling
    m.fs.brine_props.set_default_scaling("temperature", 1e-2)
    m.fs.brine_props.set_default_scaling("pressure", 1e-5)
    m.fs.brine_props.set_default_scaling("dens_mass_phase", 1e-3, index=("Liq",))
    
    # Set default scaling for organic properties
    m.fs.organic_props.set_default_scaling("flow_vol", 1e-2)
    m.fs.organic_props.set_default_scaling("flow_mol_comp", 1e-2, index="iso_octanol")
    m.fs.organic_props.set_default_scaling("flow_mol_comp", 1e-2, index="kerosene")
    m.fs.organic_props.set_default_scaling("flow_mol_comp", 1e-6, index="B_o")  # Boron in organic
    m.fs.organic_props.set_default_scaling("conc_mol_comp", 1e-1, index="iso_octanol")
    m.fs.organic_props.set_default_scaling("conc_mol_comp", 1e-1, index="kerosene")
    m.fs.organic_props.set_default_scaling("conc_mol_comp", 1e-6, index="B_o")
    m.fs.organic_props.set_default_scaling("temperature", 1e-2)
    m.fs.organic_props.set_default_scaling("pressure", 1e-5)
    m.fs.organic_props.set_default_scaling("dens_mass", 1e-3)
    
    # ============================================================================
    # REACTION SCALING - Scale stoichiometric reactions
    # ============================================================================
    
    # Scale HCl dissociation reaction (stoichiometric reaction)
    # This reaction is essentially instantaneous, so scale by 1
    iscale.set_scaling_factor(m.fs.acidification_reactor.control_volume.rate_reaction_extent[0, "HCl_dissociation"], 1.0)
    
    # ============================================================================
    # UNIT MODEL SCALING - Scale specific unit model variables
    # ============================================================================
    
    # Storage tank scaling
    iscale.set_scaling_factor(m.fs.brine_storage.storage_time[0], 1e-4)  # 24 hours = 86400 s
    iscale.set_scaling_factor(m.fs.brine_storage.surge_capacity[0], 10.0)  # 0.1 = 10%
    
    # Pump scaling
    iscale.set_scaling_factor(m.fs.brine_pump.deltaP[0], 1e-5)  # 3e5 Pa = 3 bar
    iscale.set_scaling_factor(m.fs.brine_pump.efficiency_pump[0], 1.0)  # 0.75 = 75%
    iscale.set_scaling_factor(m.fs.brine_pump.control_volume.work[0], 1e-3)  # Pump work in W
    
    # Mixer scaling
    iscale.set_scaling_factor(m.fs.acid_brine_mixer.outlet.pressure[0], 1e-5)
    iscale.set_scaling_factor(m.fs.acid_brine_mixer.outlet.temperature[0], 1e-2)
    
    # Solvent extraction scaling
    # Tank volumes are in m³, so scale by 1e-2
    for i in range(1, 5):  # 4 stages
        iscale.set_scaling_factor(m.fs.boron_extraction.mscontactor.volume[i], 1e-2)
    for i in range(1, 4):  # 3 stages
        iscale.set_scaling_factor(m.fs.boron_reextraction.mscontactor.volume[i], 1e-2)
    
    # Cross-sectional areas are in m², so scale by 1e-1
    iscale.set_scaling_factor(m.fs.boron_extraction.area_cross_stage[1], 1e-1)
    iscale.set_scaling_factor(m.fs.boron_reextraction.area_cross_stage[1], 1e-1)
    
    # Elevation scaling
    iscale.set_scaling_factor(m.fs.boron_extraction.elevation[1], 1.0)
    iscale.set_scaling_factor(m.fs.boron_reextraction.elevation[1], 1.0)
    
    # Solvent extraction additional scaling
    # Scale distribution coefficient
    iscale.set_scaling_factor(m.fs.boron_extraction_reactions.distribution_coefficient["B"], 1e-1)
    
    # Scale MSContactor variables if they exist
    if hasattr(m.fs.boron_extraction.mscontactor, "height"):
        for i in range(1, 5):
            iscale.set_scaling_factor(m.fs.boron_extraction.mscontactor.height[i], 1.0)
    if hasattr(m.fs.boron_reextraction.mscontactor, "height"):
        for i in range(1, 4):
            iscale.set_scaling_factor(m.fs.boron_reextraction.mscontactor.height[i], 1.0)
    
    # ============================================================================
    # FEED STREAM SCALING - Scale feed stream variables
    # ============================================================================
    
    # Brine feed scaling
    iscale.set_scaling_factor(m.fs.brine_feed.properties[0].flow_vol_phase["Liq"], 1e-2)
    iscale.set_scaling_factor(m.fs.brine_feed.properties[0].temperature, 1e-2)
    iscale.set_scaling_factor(m.fs.brine_feed.properties[0].pressure, 1e-5)
    
    # HCl feed scaling
    iscale.set_scaling_factor(m.fs.hcl_feed.properties[0].flow_vol_phase["Liq"], 1e-2)
    iscale.set_scaling_factor(m.fs.hcl_feed.properties[0].temperature, 1e-2)
    iscale.set_scaling_factor(m.fs.hcl_feed.properties[0].pressure, 1e-5)
    
    # Organic feed scaling
    iscale.set_scaling_factor(m.fs.organic_feed.properties[0].flow_vol, 1e-2)
    iscale.set_scaling_factor(m.fs.organic_feed.properties[0].temperature, 1e-2)
    iscale.set_scaling_factor(m.fs.organic_feed.properties[0].pressure, 1e-5)
    
    # Reextraction feed scaling
    iscale.set_scaling_factor(m.fs.reextraction_feed.properties[0].flow_vol_phase["Liq"], 1e-2)
    iscale.set_scaling_factor(m.fs.reextraction_feed.properties[0].temperature, 1e-2)
    iscale.set_scaling_factor(m.fs.reextraction_feed.properties[0].pressure, 1e-5)
    
    # ============================================================================
    # CALCULATE AND PROPAGATE SCALING FACTORS
    # ============================================================================
    
    # Calculate scaling factors for all blocks in the flowsheet
    iscale.calculate_scaling_factors(m)
    
    print("Scaling factors set successfully!")

def build_flowsheet():
    """
    Build the lithium carbonate plant flowsheet.
    
    Process Description:
    - Brine feed from Salar de Atacama
    - Acidification to pH ~1 for boron extraction
    - 4-stage countercurrent boron solvent extraction
    - Solvent regeneration with NaOH
    """
    
    # Create the model and flowsheet
    m = pyo.ConcreteModel()
    m.fs = FlowsheetBlock(dynamic=False)
    
    # ============================================================================
    # PROPERTY PACKAGES
    # ============================================================================
    
    # Brine property package for aqueous solution
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
    
    # Custom Organic Property Package for iso-octanol/kerosene mixture
    m.fs.organic_props = OrganicSolventParameters()
    
    # ============================================================================
    # REACTION PACKAGES
    # ============================================================================
    
    # Acidification reaction package for HCl dissociation
    m.fs.acidification_reactions = GenericReactionParameterBlock(
        property_package=m.fs.brine_props,
        **acidification_reaction_config
    )
    
    # Boron extraction reaction package for heterogeneous solvent extraction
    m.fs.boron_extraction_reactions = BoronExtractionReactions(component=m.fs)
    m.fs.boron_extraction_reactions.build()
    
    # ============================================================================
    # UNIT MODELS - STEP 1: BRINE FEED BLOCK
    # ============================================================================
    
    # Brine feed from Salar de Atacama
    m.fs.brine_feed = Feed(property_package=m.fs.brine_props)
    
    # ============================================================================
    # UNIT MODELS - STEP 2: ACID FEED BLOCK
    # ============================================================================
    
    # HCl acid feed for acidification (following PROMMIS CMI Process example)
    m.fs.hcl_feed = Feed(property_package=m.fs.brine_props)
    
    # ============================================================================
    # UNIT MODELS - STEP 3: ORGANIC FEED BLOCK
    # ============================================================================
    
    # Organic solvent feed for boron extraction
    # 50% iso-octanol + 50% kerosene by volume
    m.fs.organic_feed = Feed(property_package=m.fs.organic_props)
    
    # ============================================================================
    # UNIT MODELS - STEP 4: REEXTRACTION FEED BLOCK
    # ============================================================================
    
    # NaOH reextraction feed for boron stripping from organic phase
    # 0.02 N NaOH solution
    m.fs.reextraction_feed = Feed(property_package=m.fs.brine_props)
    
    # ============================================================================
    # UNIT MODELS - STEP 8: STORAGE TANK UNIT MODEL
    # ============================================================================
    
    # Storage tank for inlet brine
    # Simple storage tank with holdup for brine feed
    m.fs.brine_storage = StorageTank(
        property_package=m.fs.brine_props,
    )
    
    # ============================================================================
    # UNIT MODELS - STEP 9: PUMP UNIT MODEL
    # ============================================================================
    
    # Pump for brine after storage tank
    # Standard IDAES pump for pressure increase
    m.fs.brine_pump = Pump(
        property_package=m.fs.brine_props,
    )
    
    # ============================================================================
    # UNIT MODELS - STEP 10: ACID AND BRINE MIXER UNIT MODEL
    # ============================================================================
    
    # Mixer for acid and brine feeds before acidification reactor
    # Follows CMI pattern with inlet_list for multiple inlets
    m.fs.acid_brine_mixer = Mixer(
        property_package=m.fs.brine_props,
        inlet_list=["brine_feed", "acid_feed"],
        material_balance_type=MaterialBalanceType.componentTotal,
        energy_mixing_type=MixingType.none,
        momentum_mixing_type=MomentumMixingType.none,
    )
    
    # ============================================================================
    # UNIT MODELS - STEP 11: ACIDIFICATION STOICHIOMETRIC REACTOR
    # ============================================================================
    
    # Acidification stoichiometric reactor for HCl dissociation
    # Follows CMI pattern for stoichiometric reactors
    m.fs.acidification_reactor = StoichiometricReactor(
        property_package=m.fs.brine_props,
        reaction_package=m.fs.acidification_reactions,
        has_heat_of_reaction=False,
        has_heat_transfer=False,
        has_pressure_change=False,
    )
    
    # ============================================================================
    # UNIT MODELS - STEP 12: BORON SOLVENT EXTRACTION UNIT MODEL
    # ============================================================================
    
    # Boron solvent extraction unit using PROMMIS solvent extraction model
    # Uses acidified brine as aqueous stream and organic stream for boron removal
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
    
    # Boron reextraction unit using PROMMIS solvent extraction model
    # Uses NaOH solution as aqueous stream and boron-rich organic stream for boron removal from organic
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
    # CONNECT UNIT MODELS WITH ARCS
    # ============================================================================
    
    # Connect brine feed to storage tank
    m.fs.brine_feed_to_storage = Arc(source=m.fs.brine_feed.outlet, destination=m.fs.brine_storage.inlet)
    
    # Connect storage tank to pump
    m.fs.storage_to_pump = Arc(source=m.fs.brine_storage.outlet, destination=m.fs.brine_pump.inlet)
    
    # Connect pump to mixer (brine side)
    m.fs.pump_to_mixer = Arc(source=m.fs.brine_pump.outlet, destination=m.fs.acid_brine_mixer.brine_feed)
    
    # Connect HCl feed to mixer (acid side)
    m.fs.hcl_to_mixer = Arc(source=m.fs.hcl_feed.outlet, destination=m.fs.acid_brine_mixer.acid_feed)
    
    # Connect mixer to acidification reactor
    m.fs.mixer_to_reactor = Arc(source=m.fs.acid_brine_mixer.outlet, destination=m.fs.acidification_reactor.inlet)
    
    # Connect acidification reactor to boron extraction (aqueous stream)
    m.fs.reactor_to_extraction = Arc(source=m.fs.acidification_reactor.outlet, destination=m.fs.boron_extraction.aqueous_inlet)
    
    # Connect organic feed to boron extraction (organic stream)
    m.fs.organic_to_extraction = Arc(source=m.fs.organic_feed.outlet, destination=m.fs.boron_extraction.organic_inlet)
    
    # Connect reextraction feed to reextraction (aqueous stream)
    m.fs.reextraction_feed_to_reextraction = Arc(source=m.fs.reextraction_feed.outlet, destination=m.fs.boron_reextraction.aqueous_inlet)
    
    # Connect boron extraction organic outlet to reextraction (organic stream)
    m.fs.extraction_organic_to_reextraction = Arc(source=m.fs.boron_extraction.organic_outlet, destination=m.fs.boron_reextraction.organic_inlet)
    
    # Expand arcs to create the full flowsheet
    TransformationFactory("network.expand_arcs").apply_to(m)
    
    # ============================================================================
    # SET OPERATING CONDITIONS
    # ============================================================================
    
    set_brine_feed_conditions(m)
    set_hcl_feed_conditions(m)
    set_organic_feed_conditions(m)
    set_reextraction_feed_conditions(m)
    
    # ============================================================================
    # FIX UNIT MODEL VARIABLES
    # ============================================================================
    
    fix_unit_model_variables(m)
    
    # ============================================================================
    # SET SCALING FACTORS
    # ============================================================================
    
    set_scaling_factors(m)
    
    return m

def set_brine_feed_conditions(m):
    """
    Set the brine feed conditions based on Salar de Carmen specifications.
    
    Feed Conditions:
    - Na: 570 ppm
    - K: 160 ppm  
    - Mg: 19200 ppm
    - Li: 60000 ppm
    - Ca: 530 ppm
    - Cl: 351000 ppm
    - SO4: 220 ppm
    - B: 6270 ppm
    - Density: 1.252 kg/L
    - pH: 6.50
    """
    
    # Reference conditions
    T_ref = 298.15 * units.K  # 25°C
    P_ref = 101325 * units.Pa  # 1 atm
    
    # Set temperature and pressure
    m.fs.brine_feed.properties[0].temperature.fix(T_ref)
    m.fs.brine_feed.properties[0].pressure.fix(P_ref)
    
    # Set flow rate based on industrial-scale operation at Salar de Atacama
    # Using 1000 L/min as base flow rate for industrial-scale operation
    flow_rate = 1000 * units.L / units.minute
    m.fs.brine_feed.properties[0].flow_vol_phase["Liq"].fix(flow_rate)
    
    # Convert ppm to mass concentration (mg/L = ppm)
    # Density = 1.252 kg/L = 1252 g/L
    density = 1252 * units.g / units.L
    
    # Calculate mass concentrations from ppm
    # mass_conc = ppm * density / 1e6
    mass_conc_Na = 570 * density / 1e6  # ppm to g/L
    mass_conc_K = 160 * density / 1e6
    mass_conc_Mg = 19200 * density / 1e6
    mass_conc_Li = 60000 * density / 1e6
    mass_conc_Ca = 530 * density / 1e6
    mass_conc_Cl = 351000 * density / 1e6
    mass_conc_SO4 = 220 * density / 1e6
    mass_conc_B = 6270 * density / 1e6
    
    # Set mass concentrations
    m.fs.brine_feed.properties[0].conc_mass_phase_comp["Liq", "Na"].fix(mass_conc_Na)
    m.fs.brine_feed.properties[0].conc_mass_phase_comp["Liq", "K"].fix(mass_conc_K)
    m.fs.brine_feed.properties[0].conc_mass_phase_comp["Liq", "Mg"].fix(mass_conc_Mg)
    m.fs.brine_feed.properties[0].conc_mass_phase_comp["Liq", "Li"].fix(mass_conc_Li)
    m.fs.brine_feed.properties[0].conc_mass_phase_comp["Liq", "Ca"].fix(mass_conc_Ca)
    m.fs.brine_feed.properties[0].conc_mass_phase_comp["Liq", "Cl"].fix(mass_conc_Cl)
    m.fs.brine_feed.properties[0].conc_mass_phase_comp["Liq", "SO4"].fix(mass_conc_SO4)
    m.fs.brine_feed.properties[0].conc_mass_phase_comp["Liq", "B"].fix(mass_conc_B)
    
    # Set H+ concentration based on pH = 6.50
    # pH = -log10([H+])
    # [H+] = 10^(-pH) = 10^(-6.50) = 3.16e-7 mol/L
    H_conc_mol = 3.16e-7 * units.mol / units.L
    # Convert to mass concentration (H+ has MW = 1.008 g/mol)
    H_conc_mass = H_conc_mol * 1.008 * units.g / units.mol
    m.fs.brine_feed.properties[0].conc_mass_phase_comp["Liq", "H"].fix(H_conc_mass)
    
    # Set water concentration (remaining mass)
    # Total mass concentration = density
    total_conc = (mass_conc_Na + mass_conc_K + mass_conc_Mg + mass_conc_Li + 
                  mass_conc_Ca + mass_conc_Cl + mass_conc_SO4 + mass_conc_B + H_conc_mass)
    water_conc = density - total_conc
    m.fs.brine_feed.properties[0].conc_mass_phase_comp["Liq", "H2O"].fix(water_conc)

def set_hcl_feed_conditions(m):
    """
    Set the HCl acid feed conditions for acidification.
    
    Target: 0.1 N H+ concentration for optimal boron extraction
    HCl concentration: ~12 M HCl (concentrated hydrochloric acid)
    """
    
    # Reference conditions
    T_ref = 298.15 * units.K  # 25°C
    P_ref = 101325 * units.Pa  # 1 atm
    
    # Set temperature and pressure
    m.fs.hcl_feed.properties[0].temperature.fix(T_ref)
    m.fs.hcl_feed.properties[0].pressure.fix(P_ref)
    
    # Set flow rate based on target 0.1 N H+ in final mixture
    # For industrial-scale operation, using 100 L/min for HCl feed
    # This will achieve approximately 0.1 N H+ concentration in the mixed stream
    flow_rate = 100 * units.L / units.minute
    m.fs.hcl_feed.properties[0].flow_vol_phase["Liq"].fix(flow_rate)
    
    # HCl concentration: 12 M HCl (concentrated hydrochloric acid)
    # 12 M = 12 mol/L
    HCl_conc_mol = 12.0 * units.mol / units.L
    
    # Convert to mass concentration (HCl has MW = 36.46 g/mol)
    HCl_conc_mass = HCl_conc_mol * 36.46 * units.g / units.mol
    m.fs.hcl_feed.properties[0].conc_mass_phase_comp["Liq", "H"].fix(HCl_conc_mass)
    
    # Cl- concentration (same as HCl concentration)
    Cl_conc_mass = HCl_conc_mol * 35.45 * units.g / units.mol  # Cl- MW = 35.45 g/mol
    m.fs.hcl_feed.properties[0].conc_mass_phase_comp["Liq", "Cl"].fix(Cl_conc_mass)
    
    # Set other components to zero (HCl feed contains only HCl and H2O)
    m.fs.hcl_feed.properties[0].conc_mass_phase_comp["Liq", "Na"].fix(0 * units.g / units.L)
    m.fs.hcl_feed.properties[0].conc_mass_phase_comp["Liq", "K"].fix(0 * units.g / units.L)
    m.fs.hcl_feed.properties[0].conc_mass_phase_comp["Liq", "Mg"].fix(0 * units.g / units.L)
    m.fs.hcl_feed.properties[0].conc_mass_phase_comp["Liq", "Li"].fix(0 * units.g / units.L)
    m.fs.hcl_feed.properties[0].conc_mass_phase_comp["Liq", "Ca"].fix(0 * units.g / units.L)
    m.fs.hcl_feed.properties[0].conc_mass_phase_comp["Liq", "SO4"].fix(0 * units.g / units.L)
    m.fs.hcl_feed.properties[0].conc_mass_phase_comp["Liq", "B"].fix(0 * units.g / units.L)
    
    # Set water concentration (remaining mass)
    # Density of 12 M HCl ≈ 1.18 g/mL = 1180 g/L
    density = 1180 * units.g / units.L
    total_conc = HCl_conc_mass + Cl_conc_mass
    water_conc = density - total_conc
    m.fs.hcl_feed.properties[0].conc_mass_phase_comp["Liq", "H2O"].fix(water_conc)

def set_organic_feed_conditions(m):
    """Set organic feed conditions for iso-octanol/kerosene mixture"""
    # Temperature and pressure
    m.fs.organic_feed.properties[0].temperature.fix(298.15 * units.K)
    m.fs.organic_feed.properties[0].pressure.fix(101325.0 * units.Pa)
    
    # Flow rate: 1000 L/min (one-to-one volume ratio with acidified brine)
    # Based on Chilean study scaled to industrial: one-to-one (by volume) ratio of solvent to acidified brine
    m.fs.organic_feed.properties[0].flow_vol.fix(1000.0 * units.L / units.min)
    
    # Composition: 50% iso-octanol + 50% kerosene by volume
    # Molecular weights: iso-octanol = 130.23 g/mol, kerosene = 142.29 g/mol
    # Densities: iso-octanol = 0.83 g/mL, kerosene = 0.81 g/mL
    # For 50% by volume mixture:
    # iso-octanol: 415 kg/m³ / 130.23 g/mol = 3.19 mol/L
    # kerosene: 405 kg/m³ / 142.29 g/mol = 2.85 mol/L
    
    m.fs.organic_feed.properties[0].conc_mol_comp["iso_octanol"].fix(3.19 * units.mol / units.L)
    m.fs.organic_feed.properties[0].conc_mol_comp["kerosene"].fix(2.85 * units.mol / units.L)
    
    # Set molar flow rates based on concentration and volume flow
    m.fs.organic_feed.properties[0].flow_mol_comp["iso_octanol"].fix(3190.0 * units.mol / units.min)  # 3.19 mol/L * 1000 L/min
    m.fs.organic_feed.properties[0].flow_mol_comp["kerosene"].fix(2850.0 * units.mol / units.min)     # 2.85 mol/L * 1000 L/min

def set_reextraction_feed_conditions(m):
    """
    Set the reextraction feed conditions for the NaOH reextraction process.
    
    Reextraction Feed:
    - 0.02 N NaOH solution
    - pH: ~12.3 (basic)
    - Density: 1.02 g/mL
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
    
    # # Propagate state to storage tank
    # print("\n2. Propagating state to storage tank...")
    # propagate_state(m.fs.brine_feed_to_storage)
    # m.fs.brine_storage.initialize()
    # m.fs.brine_storage.report()
    
    # # Propagate state to pump
    # print("\n3. Propagating state to pump...")
    # propagate_state(m.fs.storage_to_pump)
    # m.fs.brine_pump.initialize()
    # m.fs.brine_pump.report()
    
    # # Propagate state to mixer (brine side)
    # print("\n4. Propagating state to mixer (brine side)...")
    # propagate_state(m.fs.pump_to_mixer)
    
    # # Initialize HCl feed
    # print("\n5. Initializing HCl feed...")
    # m.fs.hcl_feed.initialize()
    # m.fs.hcl_feed.report()
    
    # # Propagate state to mixer (acid side)
    # print("\n6. Propagating state to mixer (acid side)...")
    # propagate_state(m.fs.hcl_to_mixer)
    
    # # Initialize mixer
    # print("\n7. Initializing mixer...")
    # m.fs.acid_brine_mixer.initialize()
    # m.fs.acid_brine_mixer.report()
    
    # # Propagate state to acidification reactor
    # print("\n8. Propagating state to acidification reactor...")
    # propagate_state(m.fs.mixer_to_reactor)
    # m.fs.acidification_reactor.initialize()
    # m.fs.acidification_reactor.report()
    
    # # Initialize organic feed
    # print("\n9. Initializing organic feed...")
    # m.fs.organic_feed.initialize()
    # m.fs.organic_feed.report()
    
    # # Propagate state to boron extraction (aqueous stream)
    # print("\n10. Propagating state to boron extraction (aqueous stream)...")
    # propagate_state(m.fs.reactor_to_extraction)
    
    # # Propagate state to boron extraction (organic stream)
    # print("\n11. Propagating state to boron extraction (organic stream)...")
    # propagate_state(m.fs.organic_to_extraction)
    
    # # Initialize boron extraction
    # print("\n12. Initializing boron extraction...")
    # m.fs.boron_extraction.initialize()
    # m.fs.boron_extraction.report()
    
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
    print(f"\nDOF after initialization: {degrees_of_freedom(m)}")
    print("Expected DOF: 0 (all variables should be fixed)")
    
    print("\n" + "="*60)
    print("INITIALIZATION COMPLETE")
    print("="*60)
    
    # Print brine feed conditions
    print("\nBrine Feed Conditions:")
    print(f"Temperature: {m.fs.brine_feed.properties[0].temperature.value} K")
    print(f"Pressure: {m.fs.brine_feed.properties[0].pressure.value} Pa")
    print(f"Flow rate: {m.fs.brine_feed.properties[0].flow_vol_phase['Liq'].value} m³/s ({m.fs.brine_feed.properties[0].flow_vol_phase['Liq'].value * 60000:.0f} L/min)")
    print(f"pH: 6.50")
    print(f"Density: 1.252 kg/L")
    
    # Print HCl feed conditions
    print("\nHCl Feed Conditions:")
    print(f"Temperature: {m.fs.hcl_feed.properties[0].temperature.value} K")
    print(f"Pressure: {m.fs.hcl_feed.properties[0].pressure.value} Pa")
    print(f"Flow rate: {m.fs.hcl_feed.properties[0].flow_vol_phase['Liq'].value} m³/s ({m.fs.hcl_feed.properties[0].flow_vol_phase['Liq'].value * 60000:.0f} L/min)")
    print(f"HCl concentration: 12 M (concentrated hydrochloric acid)")
    print(f"pH: ~-1.08 (very acidic)")
    print(f"Density: 1.18 g/mL")
    
    # Print organic feed conditions
    print("\nOrganic Feed Conditions:")
    print(f"Temperature: {m.fs.organic_feed.properties[0].temperature.value} K")
    print(f"Pressure: {m.fs.organic_feed.properties[0].pressure.value} Pa")
    print(f"Flow rate: {m.fs.organic_feed.properties[0].flow_vol.value} L/min")
    print(f"Density: 0.85 g/mL")
    print(f"Composition: 50% iso-octanol + 50% kerosene by volume")
    print(f"Iso-octanol concentration: {m.fs.organic_feed.properties[0].conc_mol_comp['iso_octanol'].value} mol/L")
    print(f"Kerosene concentration: {m.fs.organic_feed.properties[0].conc_mol_comp['kerosene'].value} mol/L")
    
    # Print reextraction feed conditions
    print("\nReextraction Feed Conditions:")
    print(f"Temperature: {m.fs.reextraction_feed.properties[0].temperature.value} K")
    print(f"Pressure: {m.fs.reextraction_feed.properties[0].pressure.value} Pa")
    print(f"Flow rate: {m.fs.reextraction_feed.properties[0].flow_vol_phase['Liq'].value} m³/s ({m.fs.reextraction_feed.properties[0].flow_vol_phase['Liq'].value * 60000:.0f} L/min)")
    print(f"Density: 1.02 g/mL")
    print(f"Composition: 0.02 N NaOH solution")
    print(f"pH: ~12.3 (basic)")
    print(f"NaOH concentration: {m.fs.reextraction_feed.properties[0].conc_mass_phase_comp['Liq', 'Na'].value} g/L")
    
    # Print unit model fixed variables summary
    print("\n" + "="*60)
    print("UNIT MODEL FIXED VARIABLES SUMMARY")
    print("="*60)
    print("Storage Tank:")
    print(f"  - Storage time: {m.fs.brine_storage.storage_time[0].value} hours")
    print(f"  - Surge capacity: {m.fs.brine_storage.surge_capacity[0].value*100:.1f}%")
    
    print("\nPump:")
    print(f"  - Pressure increase: {m.fs.brine_pump.deltaP[0].value/1e5:.1f} bar")
    print(f"  - Efficiency: {m.fs.brine_pump.efficiency_pump[0].value*100:.1f}%")
    
    print("\nMixer:")
    print(f"  - Outlet pressure: {m.fs.acid_brine_mixer.outlet.pressure[0].value/1e5:.2f} bar")
    print(f"  - Outlet temperature: {m.fs.acid_brine_mixer.outlet.temperature[0].value:.1f} K")
    
    print("\nStoichiometric Reactor:")
    print(f"  - HCl dissociation extent: {m.fs.acidification_reactor.rate_reaction_extent[0, 'HCl_dissociation'].value}")
    
    print("\nSolvent Extraction Units:")
    print(f"  - Boron extraction tank volumes: {[m.fs.boron_extraction.mscontactor.volume[i].value for i in range(1, 5)]} m³")
    print(f"  - Boron reextraction tank volumes: {[m.fs.boron_reextraction.mscontactor.volume[i].value for i in range(1, 4)]} m³")
    print(f"  - Distribution coefficient (B): {m.fs.boron_extraction_reactions.distribution_coefficient['B'].value}")
    print(f"  - Target boron reduction: < 5 ppm (from 6270 ppm)")
    print(f"  - Solvent composition: 50% iso-octanol + 50% kerosene")
    print(f"  - Flow ratio: 1:1 (solvent:acidified brine)")
    
    # Print scaling summary
    print("\n" + "="*60)
    print("SCALING FACTORS SUMMARY")
    print("="*60)
    print("Property Package Scaling:")
    print("  - Flow rates: 1e-2 (m³/s)")
    print("  - Concentrations: 1e-1 to 1e-9 (g/L)")
    print("  - Temperature: 1e-2 (K)")
    print("  - Pressure: 1e-5 (Pa)")
    print("  - Density: 1e-3 (kg/m³)")
    
    print("\nReaction Scaling:")
    print("  - HCl dissociation: 1.0 (stoichiometric)")
    print("  - Boron distribution: 1e-1")
    
    print("\nUnit Model Scaling:")
    print("  - Storage time: 1e-4 (s)")
    print("  - Pump work: 1e-3 (W)")
    print("  - Tank volumes: 1e-2 (m³)")
    print("  - Cross-sectional areas: 1e-1 (m²)")
    
    print("\nFeed Stream Scaling:")
    print("  - All flow rates: 1e-2 (m³/s)")
    print("  - All temperatures: 1e-2 (K)")
    print("  - All pressures: 1e-5 (Pa)")
    
    return m

if __name__ == "__main__":
    m = main()
