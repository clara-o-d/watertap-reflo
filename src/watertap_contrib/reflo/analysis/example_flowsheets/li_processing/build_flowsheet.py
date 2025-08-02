#################################################################################
# Lithium Carbonate Plant Flowsheet
# Salar de Carmen (Antofagasta) Process
#################################################################################

import pyomo.environ as pyo
from pyomo.environ import units
from pyomo.network import Arc

# IDAES imports
from idaes.core import FlowsheetBlock
from idaes.models.unit_models import Feed, Pump, Mixer, StoichiometricReactor
from idaes.core.util.initialization import propagate_state
from idaes.core import Component, LiquidPhase, PhysicalParameterBlock, StateBlock, StateBlockData, declare_process_block_class, MaterialFlowBasis
from pyomo.environ import Param, Var, units, Constraint, PositiveReals

# WaterTAP imports
from watertap.property_models.multicomp_aq_sol_prop_pack import (
    MCASParameterBlock,
    MCASStateBlock,
)

# PROMMIS imports (will be added when we get to solvent extraction)
# from prommis.solvent_extraction import SolventExtraction

# ============================================================================
# ORGANIC PROPERTY PACKAGE FOR ISO-OCTANOL/KEROSENE MIXTURE
# ============================================================================

@declare_process_block_class("OrganicSolventParameters")
class OrganicSolventParameterData(PhysicalParameterBlock):
    """
    Property package for organic solvent mixture (50% iso-octanol + 50% kerosene).
    
    Components:
    - IsoOctanol (C8H18O): 50% by volume
    - Kerosene (C10H22): 50% by volume
    """
    
    # Set the state block class
    _state_block_class = None
    
    def build(self):
        super().build()
        
        self.organic = LiquidPhase()
        
        # Organic solvents
        self.IsoOctanol = Component()
        self.Kerosene = Component()
        
        # Molecular weights (g/mol)
        self.mw = Param(
            self.component_list,
            units=units.kg / units.mol,
            initialize={
                "IsoOctanol": 130.23e-3,  # C8H18O
                "Kerosene": 142.29e-3,     # C10H22
            },
        )
        
        # Density of organic mixture (g/mL)
        self.dens_mass = Param(
            units=units.kg / units.m**3,
            initialize=850.0,  # 0.85 g/mL = 850 kg/m³
        )
        
        # Set the state block class
        self._state_block_class = OrganicSolventStateBlock
    
    @classmethod
    def define_metadata(cls, obj):
        obj.add_properties(
            {
                "flow_mass": {"method": None},
                "conc_mass_comp": {"method": None},
                "dens_mass": {"method": None},
            }
        )
        obj.add_default_units(
            {
                "time": units.s,
                "length": units.m,
                "mass": units.kg,
                "amount": units.mol,
                "temperature": units.K,
            }
        )

class _OrganicSolventStateBlock(StateBlock):
    def fix_initialization_states(self):
        pass

@declare_process_block_class("OrganicSolventStateBlock", block_class=_OrganicSolventStateBlock)
class OrganicSolventStateBlockData(StateBlockData):
    def build(self):
        super().build()
        
        # State variables
        self.flow_mass = Var(
            initialize=1.0,
            units=units.kg / units.s,
            bounds=(0, None),
            doc="Mass flow rate",
        )
        
        self.conc_mass_comp = Var(
            self.params.component_list,
            initialize=1.0,
            units=units.kg / units.m**3,
            bounds=(0, None),
            doc="Mass concentration of component",
        )
        
        self.dens_mass = Var(
            initialize=850.0,
            units=units.kg / units.m**3,
            bounds=(0, None),
            doc="Mass density",
        )
        
        # Volume flow rate (calculated)
        self.flow_vol = Var(
            initialize=1.0,
            units=units.m**3 / units.s,
            bounds=(0, None),
            doc="Volumetric flow rate",
        )
        
        # Temperature and pressure
        self.temperature = Var(
            initialize=298.15,
            bounds=(273.15, 373.15),
            doc="Temperature [K]",
            units=units.K,
        )
        
        self.pressure = Var(
            initialize=101325.0,
            bounds=(1e3, 1e6),
            doc="Pressure [Pa]",
            units=units.Pa,
        )
        
        # Constraints
        @self.Constraint()
        def density_constraint(b):
            return b.dens_mass == sum(b.conc_mass_comp[j] for j in self.params.component_list)
        
        @self.Constraint()
        def volume_flow_constraint(b):
            return b.flow_vol * b.dens_mass == b.flow_mass
    
    def get_material_flow_basis(self):
        return MaterialFlowBasis.mass
    
    def define_state_vars(self):
        return {
            "flow_mass": self.flow_mass,
            "conc_mass_comp": self.conc_mass_comp,
            "dens_mass": self.dens_mass,
            "temperature": self.temperature,
            "pressure": self.pressure,
        }

# Set the state block class for the parameter block
# OrganicSolventParameters._state_block_class = OrganicSolventStateBlock

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
    
    # MCAS Property Package for brine streams
    m.fs.brine_props = MCASParameterBlock(
        solute_list=["Na", "K", "Mg", "Li", "Ca", "Cl", "SO4", "B", "H"],
        charge={"Na": 1, "K": 1, "Mg": 2, "Li": 1, "Ca": 2, "Cl": -1, "SO4": -2, "B": 0, "H": 1},
    )
    
    # Custom Organic Property Package for iso-octanol/kerosene mixture
    m.fs.organic_props = OrganicSolventParameters()
    
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
    # SET OPERATING CONDITIONS
    # ============================================================================
    
    set_brine_feed_conditions(m)
    set_hcl_feed_conditions(m)
    set_organic_feed_conditions(m)
    set_reextraction_feed_conditions(m)
    
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
    
    # Set flow rate (will be scaled based on plant capacity)
    # Using 1000 L/min as base flow rate
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
    
    # Set flow rate (will be calculated based on target 0.1 N H+ in final mixture)
    # Using 100 L/min as base flow rate for HCl feed
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
    """
    Set the organic feed conditions for the solvent extraction process.
    
    Organic Feed:
    - 50% iso-octanol (C8H18O) by volume
    - 50% kerosene (C10H22) by volume
    - Density: 0.85 g/mL
    """
    
    # Reference conditions
    T_ref = 298.15 * units.K  # 25°C
    P_ref = 101325 * units.Pa  # 1 atm
    
    # Set temperature and pressure
    m.fs.organic_feed.properties[0].temperature.fix(T_ref)
    m.fs.organic_feed.properties[0].pressure.fix(P_ref)
    
    # Set flow rate (will be scaled based on plant capacity)
    # Using 100 L/min as base flow rate for organic feed
    flow_rate = 100 * units.L / units.minute
    m.fs.organic_feed.properties[0].flow_vol.fix(flow_rate)
    
    # Density of organic solvent mixture
    # Density = 0.85 g/mL = 850 kg/m³
    density = 850.0 * units.kg / units.m**3
    m.fs.organic_feed.properties[0].dens_mass.fix(density)
    
    # Calculate mass concentrations for 50% iso-octanol + 50% kerosene by volume
    # Iso-octanol (C8H18O): density ≈ 0.83 g/mL = 830 kg/m³
    # Kerosene (C10H22): density ≈ 0.81 g/mL = 810 kg/m³
    
    # For 50% by volume mixture:
    iso_octanol_conc = 0.5 * 830.0 * units.kg / units.m**3  # 50% of 830 kg/m³
    kerosene_conc = 0.5 * 810.0 * units.kg / units.m**3  # 50% of 810 kg/m³
    
    # Set mass concentrations
    m.fs.organic_feed.properties[0].conc_mass_comp["IsoOctanol"].fix(iso_octanol_conc)
    m.fs.organic_feed.properties[0].conc_mass_comp["Kerosene"].fix(kerosene_conc)
    
    # Set mass flow rate
    mass_flow = flow_rate * density
    m.fs.organic_feed.properties[0].flow_mass.fix(mass_flow)

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
    
    # Set flow rate (will be scaled based on plant capacity)
    # Using 100 L/min as base flow rate for reextraction feed
    flow_rate = 100 * units.L / units.minute
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
    
    # Print brine feed conditions
    print("\nBrine Feed Conditions:")
    print(f"Temperature: {m.fs.brine_feed.properties[0].temperature.value} K")
    print(f"Pressure: {m.fs.brine_feed.properties[0].pressure.value} Pa")
    print(f"Flow rate: {m.fs.brine_feed.properties[0].flow_vol_phase['Liq'].value} L/min")
    print(f"pH: 6.50")
    print(f"Density: 1.252 kg/L")
    
    # Print HCl feed conditions
    print("\nHCl Feed Conditions:")
    print(f"Temperature: {m.fs.hcl_feed.properties[0].temperature.value} K")
    print(f"Pressure: {m.fs.hcl_feed.properties[0].pressure.value} Pa")
    print(f"Flow rate: {m.fs.hcl_feed.properties[0].flow_vol_phase['Liq'].value} L/min")
    print(f"HCl concentration: 12 M (concentrated hydrochloric acid)")
    print(f"pH: ~-1.08 (very acidic)")
    print(f"Density: 1.18 g/mL")
    
    # Print organic feed conditions
    print("\nOrganic Feed Conditions:")
    print(f"Temperature: {m.fs.organic_feed.properties[0].temperature.value} K")
    print(f"Pressure: {m.fs.organic_feed.properties[0].pressure.value} Pa")
    print(f"Flow rate: {m.fs.organic_feed.properties[0].flow_vol.value} L/min")
    print(f"Mass flow rate: {m.fs.organic_feed.properties[0].flow_mass.value} kg/min")
    print(f"Density: 0.85 g/mL")
    print(f"Composition: 50% iso-octanol + 50% kerosene by volume")
    print(f"Iso-octanol concentration: {m.fs.organic_feed.properties[0].conc_mass_comp['IsoOctanol'].value} kg/m³")
    print(f"Kerosene concentration: {m.fs.organic_feed.properties[0].conc_mass_comp['Kerosene'].value} kg/m³")
    
    # Print reextraction feed conditions
    print("\nReextraction Feed Conditions:")
    print(f"Temperature: {m.fs.reextraction_feed.properties[0].temperature.value} K")
    print(f"Pressure: {m.fs.reextraction_feed.properties[0].pressure.value} Pa")
    print(f"Flow rate: {m.fs.reextraction_feed.properties[0].flow_vol_phase['Liq'].value} L/min")
    print(f"Density: 1.02 g/mL")
    print(f"Composition: 0.02 N NaOH solution")
    print(f"pH: ~12.3 (basic)")
    print(f"NaOH concentration: {m.fs.reextraction_feed.properties[0].conc_mass_phase_comp['Liq', 'Na'].value} g/L")
    
    return m

if __name__ == "__main__":
    m = main()
