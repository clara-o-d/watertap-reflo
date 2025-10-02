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
from idaes.models.unit_models import Feed, Pump
from idaes.core.util.initialization import propagate_state
from idaes.core.util.model_statistics import degrees_of_freedom
from idaes.core import MaterialFlowBasis

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
from watertap.unit_models.stoichiometric_reactor import StoichiometricReactor
from watertap.core.wt_database import Database

# ============================================================================
# FIX UNIT MODEL VARIABLES
# ============================================================================

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
        "HCO3": 61.0168 * pyunits.g/pyunits.mol,
        "CO3": 60.0092 * pyunits.g/pyunits.mol,
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
        "HCO3": 100,
        "CO3": 50,  # Typical carbonate concentration in brine
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
    
    # Load default parameters from database (this fixes storage_time and surge_capacity)
    m.fs.brine_storage.load_parameters_from_database()
    
    # ============================================================================
    # PUMP
    # ============================================================================
    
    m.fs.brine_pump.deltaP[0].fix(3e5 * units.Pa)
    m.fs.brine_pump.efficiency_pump[0].fix(0.75)
    
    # ============================================================================
    # SOFTENING REACTOR
    # ============================================================================
    
    # Fix reagent doses (typical values for water softening)
    m.fs.softening_reactor.reagent_dose["Na2CO3"].fix(1e-3 * units.kg / units.L)  # 1 g/L
    m.fs.softening_reactor.reagent_dose["CaO"].fix(1e-3 * units.kg / units.L)      # 1 g/L
    
    # Fix precipitate formation rates (based on expected removal)
    m.fs.softening_reactor.flow_mass_precipitate["Calcite"].fix(0.5e-3 * units.kg / units.s)   # CaCO3
    m.fs.softening_reactor.flow_mass_precipitate["Brucite"].fix(0.3e-3 * units.kg / units.s)   # Mg(OH)2
    
    # Fix waste stream solids fraction
    m.fs.softening_reactor.waste_mass_frac_precipitate.fix(0.2)  # 20% solids in waste stream
    
    # ============================================================================
    # LITHIUM CARBONATE REACTOR
    # ============================================================================
    
    # Fix soda ash dose for lithium carbonate precipitation
    m.fs.lithium_carbonate_reactor.reagent_dose["Na2CO3"].fix(2e-3 * units.kg / units.L)  # 2 g/L
    
    # Fix lithium carbonate formation rate (based on expected lithium recovery)
    m.fs.lithium_carbonate_reactor.flow_mass_precipitate["Li2CO3"].fix(10e-3 * units.kg / units.s)   # Li2CO3
    
    # Fix waste stream solids fraction
    m.fs.lithium_carbonate_reactor.waste_mass_frac_precipitate.fix(0.15)  # 15% solids in waste stream
    
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
    m.fs.brine_props.set_default_scaling("flow_mol_phase_comp", 1e-4, index=("Liq", "HCO3"))
    
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
    m.fs.brine_props.set_default_scaling("conc_mass_phase_comp", 1e-2, index=("Liq", "HCO3"))
    
    m.fs.brine_props.set_default_scaling("temperature", 1e-2)
    m.fs.brine_props.set_default_scaling("pressure", 1e-5)
    m.fs.brine_props.set_default_scaling("dens_mass_phase", 1e-3, index=("Liq",))
    
    
    
    # ============================================================================
    # UNIT MODEL SCALING
    # ============================================================================
    
    iscale.set_scaling_factor(m.fs.brine_storage.storage_time[0], 1e-4)
    iscale.set_scaling_factor(m.fs.brine_storage.surge_capacity[0], 10.0)
    
    iscale.set_scaling_factor(m.fs.brine_pump.deltaP[0], 1e-5)
    iscale.set_scaling_factor(m.fs.brine_pump.efficiency_pump[0], 1.0)
    iscale.set_scaling_factor(m.fs.brine_pump.control_volume.work[0], 1e-3)
    
    # Softening reactor scaling factors
    iscale.set_scaling_factor(m.fs.softening_reactor.reagent_dose["Na2CO3"], 1e3)
    iscale.set_scaling_factor(m.fs.softening_reactor.reagent_dose["CaO"], 1e3)
    iscale.set_scaling_factor(m.fs.softening_reactor.flow_mass_precipitate["Calcite"], 1e3)
    iscale.set_scaling_factor(m.fs.softening_reactor.flow_mass_precipitate["Brucite"], 1e3)
    iscale.set_scaling_factor(m.fs.softening_reactor.waste_mass_frac_precipitate, 10.0)
    
    # Lithium carbonate reactor scaling factors
    iscale.set_scaling_factor(m.fs.lithium_carbonate_reactor.reagent_dose["Na2CO3"], 1e3)
    iscale.set_scaling_factor(m.fs.lithium_carbonate_reactor.flow_mass_precipitate["Li2CO3"], 1e3)
    iscale.set_scaling_factor(m.fs.lithium_carbonate_reactor.waste_mass_frac_precipitate, 10.0)
    
    
    
    # ============================================================================
    # FEED STREAM SCALING
    # ============================================================================
    
    iscale.set_scaling_factor(m.fs.brine_feed.properties[0].flow_vol_phase["Liq"], 1e-2)
    iscale.set_scaling_factor(m.fs.brine_feed.properties[0].temperature, 1e-2)
    iscale.set_scaling_factor(m.fs.brine_feed.properties[0].pressure, 1e-5)
    
    
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
    
    m.fs.brine_props = MCASParameterBlock(
        solute_list=["Na", "K", "Mg", "Li", "Ca", "Cl", "SO4", "B", "H", "HCO3", "CO3"],
        charge={"Na": 1, "K": 1, "Mg": 2, "Li": 1, "Ca": 2, "Cl": -1, "SO4": -2, "B": 0, "H": 1, "HCO3": -1, "CO3": -2},
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
            "HCO3": 61.0168e-3,
            "CO3": 60.0092e-3,
        },
        material_flow_basis=MaterialFlowBasis.molar,
    )
    
    
    # ============================================================================
    # UNIT MODELS
    # ============================================================================
    
    m.fs.brine_feed = Feed(property_package=m.fs.brine_props)
    
    # Create database for zero-order unit models
    m.db = Database()
    
    m.fs.brine_storage = StorageTank(
        property_package=m.fs.brine_props,
        database=m.db,
    )
    
    m.fs.brine_pump = Pump(
        property_package=m.fs.brine_props,
    )
    
    # Define reagents for softening
    reagents = {
        "Na2CO3": {
            "mw": 105.99 * pyunits.g / pyunits.mol,
            "dissolution_stoichiometric": {"Na": 2, "HCO3": 1},
            "density_reagent": 1.2 * pyunits.kg / pyunits.L,
        },
        "CaO": {
            "mw": 56.0774 * pyunits.g / pyunits.mol,
            "dissolution_stoichiometric": {"Ca": 1, "H2O": 1},
            "density_reagent": 1.2 * pyunits.kg / pyunits.L,
        },
    }
    
    # Define precipitants for softening
    precipitants = {
        "Calcite": {
            "mw": 100.09 * pyunits.g / pyunits.mol,
            "precipitation_stoichiometric": {"Ca": 1, "HCO3": 1},
        },
        "Brucite": {
            "mw": 58.3197 * pyunits.g / pyunits.mol,
            "precipitation_stoichiometric": {"Mg": 1, "H2O": 1},
        },
    }
    
    m.fs.softening_reactor = StoichiometricReactor(
        property_package=m.fs.brine_props,
        reagent=reagents,
        precipitate=precipitants,
    )
    
    # Define reagents for lithium carbonate precipitation
    lithium_reagents = {
        "Na2CO3": {
            "mw": 105.99 * pyunits.g / pyunits.mol,
            "dissolution_stoichiometric": {"Na": 2, "CO3": 1},
            "density_reagent": 1.2 * pyunits.kg / pyunits.L,
        },
    }
    
    # Define precipitates for lithium carbonate precipitation
    lithium_precipitants = {
        "Li2CO3": {
            "mw": 73.89 * pyunits.g / pyunits.mol,
            "precipitation_stoichiometric": {"Li": 2, "CO3": 1},
            "density_precipitate": 2.11 * pyunits.kg / pyunits.L,
        },
    }
    
    m.fs.lithium_carbonate_reactor = StoichiometricReactor(
        property_package=m.fs.brine_props,
        reagent=lithium_reagents,
        precipitate=lithium_precipitants,
    )
    
    # The lithium carbonate product will be available at the waste outlet of the reactor
    # In a real process, this would be connected to a dryer
    
    
    # ============================================================================
    # CONNECT UNIT MODELS
    # ============================================================================
    
    m.fs.brine_feed_to_storage = Arc(source=m.fs.brine_feed.outlet, destination=m.fs.brine_storage.inlet)
    m.fs.storage_to_pump = Arc(source=m.fs.brine_storage.outlet, destination=m.fs.brine_pump.inlet)
    m.fs.pump_to_softening = Arc(source=m.fs.brine_pump.outlet, destination=m.fs.softening_reactor.inlet)
    m.fs.softening_to_lithium = Arc(source=m.fs.softening_reactor.outlet, destination=m.fs.lithium_carbonate_reactor.inlet)
    # Note: lithium carbonate product is available at m.fs.lithium_carbonate_reactor.waste
    
    TransformationFactory("network.expand_arcs").apply_to(m)
    
    # ============================================================================
    # SET CONDITIONS
    # ============================================================================
    
    set_brine_feed_conditions(m)
    fix_unit_model_variables(m)
    set_scaling_factors(m)
    
    return m

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

def initialize_flowsheet(m):
    """
    Initialize the flowsheet by setting up all unit models in sequence.
    
    Args:
        m: The flowsheet model to initialize
        
    Returns:
        m: The initialized flowsheet model
    """
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
    print(f"DOF after brine storage: {degrees_of_freedom(m)}")

    # Propagate state to pump
    print("\n3. Propagating state to pump...")
    propagate_state(m.fs.storage_to_pump)
    m.fs.brine_pump.initialize()
    m.fs.brine_pump.report()
    print(f"DOF after brine pump: {degrees_of_freedom(m)}")
    
    # Propagate state to softening reactor
    print("\n4. Propagating state to softening reactor...")
    propagate_state(m.fs.pump_to_softening)
    m.fs.softening_reactor.initialize()
    # Note: report() method has an issue with reactor_outlet attribute, so we'll skip it for now
    print("Softening reactor initialized successfully!")
    print(f"DOF after softening reactor: {degrees_of_freedom(m)}")
    
    # Propagate state to lithium carbonate reactor
    print("\n5. Propagating state to lithium carbonate reactor...")
    propagate_state(m.fs.softening_to_lithium)
    m.fs.lithium_carbonate_reactor.initialize()
    # Note: report() method has an issue with reactor_outlet attribute, so we'll skip it for now
    print("Lithium carbonate reactor initialized successfully!")
    print(f"DOF after lithium carbonate reactor: {degrees_of_freedom(m)}")
    
    # Check degrees of freedom
    print("\n" + "="*60)
    print("INITIALIZATION COMPLETE")
    print("="*60)
    
    # Check final degrees of freedom
    dof = degrees_of_freedom(m)
    print(f"\nFinal Degrees of Freedom: {dof}")
    if dof == 0:
        print("✓ All variables are properly fixed!")
    else:
        print(f"⚠ Warning: {dof} degrees of freedom remaining")
        check_unfixed_variables(m, "entire flowsheet")
    
    # Print feed conditions summary
    print("\nBrine Feed Conditions:")
    print(f"Temperature: {pyo.value(m.fs.brine_feed.properties[0].temperature)} K")
    print(f"Pressure: {pyo.value(m.fs.brine_feed.properties[0].pressure)} Pa")
    print(f"Flow rate: {pyo.value(m.fs.brine_feed.properties[0].flow_vol_phase['Liq'])} m³/s ({pyo.value(m.fs.brine_feed.properties[0].flow_vol_phase['Liq']) * 60000:.0f} L/min)")
    print(f"pH: 6.50")
    print(f"Density: 1.252 kg/L")
    
    
    print("\n" + "="*60)
    print("UNIT MODEL FIXED VARIABLES SUMMARY")
    print("="*60)
    print("Storage Tank:")
    print(f"  - Storage time: {pyo.value(m.fs.brine_storage.storage_time[0])} hours")
    print(f"  - Surge capacity: {pyo.value(m.fs.brine_storage.surge_capacity[0])*100:.1f}%")
    
    print("\nPump:")
    print(f"  - Pressure increase: {pyo.value(m.fs.brine_pump.deltaP[0])/1e5:.1f} bar")
    print(f"  - Efficiency: {pyo.value(m.fs.brine_pump.efficiency_pump[0])*100:.1f}%")
    
    print("\nSoftening Reactor:")
    print(f"  - Na2CO3 dose: {pyo.value(m.fs.softening_reactor.reagent_dose['Na2CO3'])*1e3:.1f} g/L")
    print(f"  - CaO dose: {pyo.value(m.fs.softening_reactor.reagent_dose['CaO'])*1e3:.1f} g/L")
    print(f"  - Calcite formation: {pyo.value(m.fs.softening_reactor.flow_mass_precipitate['Calcite'])*1e3:.3f} g/s")
    print(f"  - Brucite formation: {pyo.value(m.fs.softening_reactor.flow_mass_precipitate['Brucite'])*1e3:.3f} g/s")
    print(f"  - Waste solids fraction: {pyo.value(m.fs.softening_reactor.waste_mass_frac_precipitate)*100:.1f}%")
    
    print("\nLithium Carbonate Reactor:")
    print(f"  - Na2CO3 dose: {pyo.value(m.fs.lithium_carbonate_reactor.reagent_dose['Na2CO3'])*1e3:.1f} g/L")
    print(f"  - Li2CO3 formation: {pyo.value(m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3'])*1e3:.3f} g/s")
    print(f"  - Waste solids fraction: {pyo.value(m.fs.lithium_carbonate_reactor.waste_mass_frac_precipitate)*100:.1f}%")
    
    print("\n" + "="*60)
    print("SCALING FACTORS SUMMARY")
    print("="*60)
    print("Property Package Scaling:")
    print(f"  - Flow rates: 1e-2 (m³/s)")
    print(f"  - Concentrations: 1e-1 to 1e-9 (g/L)")
    print(f"  - Temperature: 1e-2 (K)")
    print(f"  - Pressure: 1e-5 (Pa)")
    print(f"  - Density: 1e-3 (kg/m³)")
    
    
    print("\nUnit Model Scaling:")
    print(f"  - Storage time: 1e-4 (s)")
    print(f"  - Pump work: 1e-3 (W)")
    print(f"  - Tank volumes: 1e-2 (m³)")
    print(f"  - Cross-sectional areas: 1e-1 (m²)")
    print(f"  - Reagent doses: 1e3 (kg/m³)")
    print(f"  - Precipitate flows: 1e3 (kg/s)")
    print(f"  - Lithium carbonate formation: 1e3 (kg/s)")
    
    print("\nFeed Stream Scaling:")
    print(f"  - All flow rates: 1e-2 (m³/s)")
    print(f"  - All temperatures: 1e-2 (K)")
    print(f"  - All pressures: 1e-5 (Pa)")
    
    return m

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
    
    # Initialize the flowsheet
    m = initialize_flowsheet(m)
    
    return m

if __name__ == "__main__":
    m = main()
