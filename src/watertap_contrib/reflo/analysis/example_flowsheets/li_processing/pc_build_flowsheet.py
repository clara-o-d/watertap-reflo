#################################################################################
# Lithium Carbonate Plant Flowsheet
# Salar de Carmen (Antofagasta) Process
# 
    # Process Flow:
    ## 1. Brine feed -> Storage tank -> Pump
    ## 2. Soda ash reactor (Na2CO3 -> precipitates MgCO3)
    ## 3. Lime reactor (CaO -> precipitates Mg(OH)2 and CaSO4)
    ## 4. Lime dewatering (separates Mg(OH)2 and CaSO4 precipitates)
    ## 5. Lime centrifuge (further concentrates lime precipitates)
    ## 6. Lithium carbonate reactor (Na2CO3 -> precipitates Li2CO3)
    ## 7. Lithium dewatering (separates Li2CO3 slurry into solids and clarified liquid)
#
# Model Gaps:
## 1. Boron extraction
## 2. Lithium carbonate drying
## 3. Lithium carbonate compression
#################################################################################

import pyomo.environ as pyo
from pyomo.environ import units as pyunits
from pyomo.network import Arc
from pyomo.environ import units
from pyomo.core import TransformationFactory
import idaes.core.util.scaling as iscale
from idaes.core.scaling import AutoScaler
import idaes.logger as idaeslog
from io import StringIO

# IDAES imports
from idaes.core import FlowsheetBlock
from idaes.models.unit_models import Feed, Pump, Separator
from idaes.models.unit_models.separator import SplittingType
from idaes.core.util.initialization import propagate_state
from idaes.core.util.model_statistics import degrees_of_freedom
from idaes.core import MaterialFlowBasis
from idaes.core.scaling import report_scaling_factors
from idaes.core.util.model_diagnostics import SVDToolbox, svd_sparse, svd_dense, DiagnosticsToolbox

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

# Local imports
from pc_scaling_factors import set_scaling_factors

def modify_unit_models(m, stage=3):
    """
    Modify the unit models for the flowsheet.
    """
    if stage >= 3:
        # SODA ASH DEWATERING UNIT
        # Add electricity consumption variable for soda ash dewatering costing
        # Based on typical belt filter press: 0.006 kWh/m³
        m.fs.soda_ash_dewatering.electricity_consumption = pyo.Var(
            m.fs.time,
            initialize=0.1,
            units=pyunits.kW,
            bounds=(0, None),
            doc="Electricity consumption of soda ash dewatering unit"
        )
        
        m.fs.soda_ash_dewatering.energy_electric_flow_vol_inlet = pyo.Param(
            m.fs.time,
            initialize=0.006,
            units=pyunits.kWh / pyunits.m**3,
            mutable=True,
            doc="Specific electricity intensity for belt filter press"
        )
        
        @m.fs.soda_ash_dewatering.Constraint(m.fs.time, doc="Electricity consumption equation")
        def soda_ash_eq_electricity_consumption(blk, t):
            return blk.electricity_consumption[t] == pyunits.convert(
                blk.energy_electric_flow_vol_inlet[t] * blk.mixed_state[t].flow_vol,
                to_units=pyunits.kW,
            )
        
        # SODA ASH CENTRIFUGE DEWATERING UNIT
        # Add electricity consumption variable for centrifuge costing
        # Based on typical centrifuge: 0.015 kWh/m³ (higher than belt filter press)
        m.fs.soda_ash_centrifuge.electricity_consumption = pyo.Var(
            m.fs.time,
            initialize=0.1,
            units=pyunits.kW,
            bounds=(0, None),
            doc="Electricity consumption of soda ash centrifuge dewatering unit"
        )
        
        m.fs.soda_ash_centrifuge.energy_electric_flow_vol_inlet = pyo.Param(
            m.fs.time,
            initialize=0.015,
            units=pyunits.kWh / pyunits.m**3,
            mutable=True,
            doc="Specific electricity intensity for centrifuge"
        )
        
        @m.fs.soda_ash_centrifuge.Constraint(m.fs.time, doc="Electricity consumption equation")
        def soda_ash_centrifuge_eq_electricity_consumption(blk, t):
            return blk.electricity_consumption[t] == pyunits.convert(
                blk.energy_electric_flow_vol_inlet[t] * blk.mixed_state[t].flow_vol,
                to_units=pyunits.kW,
            )
        
        # LIME DEWATERING UNIT
        # Add electricity consumption variable for costing
        m.fs.lime_dewatering.electricity_consumption = pyo.Var(
            m.fs.time,
            initialize=0.1,
            units=pyunits.kW,
            bounds=(0, None),
            doc="Electricity consumption of softening dewatering unit"
        )
        
        m.fs.lime_dewatering.energy_electric_flow_vol_inlet = pyo.Param(
            m.fs.time,
            initialize=0.006,
            units=pyunits.kWh / pyunits.m**3,
            mutable=True,
            doc="Specific electricity intensity for belt filter press"
        )
        
        @m.fs.lime_dewatering.Constraint(m.fs.time, doc="Electricity consumption equation")
        def lime_dewatering_eq_electricity_consumption(blk, t):
            return blk.electricity_consumption[t] == pyunits.convert(
                blk.energy_electric_flow_vol_inlet[t] * blk.mixed_state[t].flow_vol,
                to_units=pyunits.kW,
            )
        
        # LIME CENTRIFUGE UNIT
        # Add electricity consumption variable for centrifuge costing
        # Based on typical centrifuge: 0.015 kWh/m³ (higher than belt filter press)
        m.fs.lime_centrifuge.electricity_consumption = pyo.Var(
            m.fs.time,
            initialize=0.1,
            units=pyunits.kW,
            bounds=(0, None),
            doc="Electricity consumption of centrifuge dewatering unit"
        )
        
        m.fs.lime_centrifuge.energy_electric_flow_vol_inlet = pyo.Param(
            m.fs.time,
            initialize=0.015,
            units=pyunits.kWh / pyunits.m**3,
            mutable=True,
            doc="Specific electricity intensity for centrifuge"
        )
        
        @m.fs.lime_centrifuge.Constraint(m.fs.time, doc="Electricity consumption equation")
        def lime_centrifuge_eq_electricity_consumption(blk, t):
            return blk.electricity_consumption[t] == pyunits.convert(
                blk.energy_electric_flow_vol_inlet[t] * blk.mixed_state[t].flow_vol,
                to_units=pyunits.kW,
            )
        
        # LITHIUM DEWATERING UNIT
        # Add electricity consumption variable for costing
        # Based on typical belt filter press: 0.006 kWh/m³
        m.fs.li_dewatering.electricity_consumption = pyo.Var(
            m.fs.time,
            initialize=0.1,
            units=pyunits.kW,
            bounds=(0, None),
            doc="Electricity consumption of lithium dewatering unit"
        )
        
        m.fs.li_dewatering.energy_electric_flow_vol_inlet = pyo.Param(
            m.fs.time,
            initialize=0.006,
            units=pyunits.kWh / pyunits.m**3,
            mutable=True,
            doc="Specific electricity intensity for belt filter press"
        )
        
        @m.fs.li_dewatering.Constraint(m.fs.time, doc="Electricity consumption equation")
        def li_eq_electricity_consumption(blk, t):
            return blk.electricity_consumption[t] == pyunits.convert(
                blk.energy_electric_flow_vol_inlet[t] * blk.mixed_state[t].flow_vol,
                to_units=pyunits.kW,
            )

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
    
    # Total mass flow rate
    total_flow_mass = 13.568 * pyunits.kg / pyunits.s
    
    # Density = 1.252 kg/L = 1252 g/L
    density = 1252 * pyunits.g / pyunits.L
    
    # Calculate volumetric flow rate from mass flow rate
    total_flow_vol = total_flow_mass / density  # L/s
    
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
    
    # Concentrations in ppm (mg/kg or parts per million by mass)
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
        "CO3": 50,
    }
    
    # Calculate molar flow rates for each solute based on mass flow rate
    for comp in ppm:
        # Convert ppm to mass fraction (kg/kg)
        mass_fraction = ppm[comp] / 1e6  # dimensionless
        # Calculate mass flow rate of component (kg/s)
        comp_mass_flow = mass_fraction * total_flow_mass # kg/s
        # Convert to molar flow rate (mol/s)
        comp_molar_flow = comp_mass_flow * 1000 / MW[comp]  # mol/s
        m.fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", comp].fix(pyo.value(comp_molar_flow))
    
    # H+ from pH (assuming pH = 6.5)
    H_conc_mol_L = 3.16e-7 * pyunits.mol / pyunits.L
    H_flow_mol_s = H_conc_mol_L * total_flow_vol
    m.fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", "H"].fix(pyo.value(H_flow_mol_s))
    
    # Water: Calculate water mass flow rate as difference from total
    total_solute_mass_fraction = sum(ppm[c] / 1e6 for c in ppm) + (H_conc_mol_L * MW["H"] / density)
    water_mass_fraction = 1.0 - total_solute_mass_fraction + 3.0 * total_flow_mass  # dimensionless
    water_mass_flow = water_mass_fraction * total_flow_mass  # kg/s
    water_molar_flow = water_mass_flow / MW["H2O"]  # mol/s
    m.fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", "H2O"].fix(pyo.value(water_molar_flow))

def modify_flowsheet(m, stage=3):
    """
    Modify the flowsheet for the flowsheet.
    """
    
    # Annual reagent inputs
    m.fs.annual_soda_ash_input = pyo.Var(
        initialize=381600000,
        bounds=(0, None),
        units=pyunits.kg / pyunits.year,
        doc="Annual soda ash input (381,600 tonnes/year)"
    )
    m.fs.annual_soda_ash_input.fix(381600000)
    
    m.fs.annual_lime_input = pyo.Var(
        initialize=15300000,
        bounds=(0, None),
        units=pyunits.kg / pyunits.year,
        doc="Annual lime input (15,300 tonnes/year)"
    )
    m.fs.annual_lime_input.fix(15300000)
    
    # Maximum total impurity concentration in Li2CO3 product (underflow from li_dewatering)
    # Sum of Na, Mg, and Ca mass fractions must be <= 0.05%
    m.fs.max_total_product_impurity = pyo.Var(
        initialize=0.0005,
        bounds=(0, 1.0),
        units=pyunits.dimensionless,
        doc="Maximum total mass fraction of Na, Mg, and Ca in Li2CO3 product (0.05%)"
    )
    m.fs.max_total_product_impurity.fix(0.0005)
    
    if stage >= 2:
        # Soda ash split fraction - proportion going to soda ash reactor vs lithium reactor
        m.fs.soda_ash_split_fraction = pyo.Var(
            initialize=0.9,
            bounds=(0, 1.0),
            units=pyunits.dimensionless,
            doc="Fraction of total soda ash going to soda ash reactor (vs lithium carbonate reactor)"
        )
        m.fs.soda_ash_split_fraction.fix(0.5)
        
        # Constraint: Total soda ash usage across both reactors
        # annual_soda_ash_input = soda_ash_to_soda_ash_reactor + soda_ash_to_lithium_reactor
        @m.fs.Constraint(doc="Total soda ash annual input constraint")
        def soda_ash_annual_input_constraint(fs):
            total_usage = fs.soda_ash_reactor.flow_mass_reagent["Na2CO3"] + fs.lithium_carbonate_reactor.flow_mass_reagent["Na2CO3"]
            
            return fs.annual_soda_ash_input == pyunits.convert(
                total_usage,
                to_units=pyunits.kg / pyunits.year
            )
        
        # Constraint: Relate soda ash flows through split fraction
        @m.fs.Constraint(doc="Soda ash split fraction constraint")
        def soda_ash_split_constraint(fs):
            total_usage = pyunits.convert(fs.annual_soda_ash_input, to_units=pyunits.kg / pyunits.s)
            
            return fs.soda_ash_reactor.flow_mass_reagent["Na2CO3"] == fs.soda_ash_split_fraction * total_usage
        
        # Constraint: Lime reactor reagent flow to match annual input
        @m.fs.Constraint(doc="Lime annual input constraint")
        def lime_annual_input_constraint(fs):
            return fs.annual_lime_input == pyunits.convert(
                fs.lime_reactor.flow_mass_reagent["CaO"],
                to_units=pyunits.kg / pyunits.year
            )
        
        # Lithium recovery target
        m.fs.target_li_recovery = pyo.Var(
            initialize=0.80,
            bounds=(0, 1.0),
            units=pyunits.dimensionless,
            doc="Target lithium recovery fraction (80%)"
        )
        m.fs.target_li_recovery.fix(0.80)
        
        # Constraint: Lithium recovery - Li2CO3 production based on feed and target recovery
        @m.fs.Constraint(doc="Lithium recovery constraint")
        def li_recovery_constraint(fs):
            # Li mass flow in feed (kg/s)
            li_in_mass = (
                fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", "Li"]
                * fs.brine_props.mw_comp["Li"]
            )
            
            # Li mass flow in Li2CO3 product (kg/s)
            li2co3_mw = 73.89e-3 * pyunits.kg / pyunits.mol
            li_mw = fs.brine_props.mw_comp["Li"]
            li_in_li2co3 = (
                fs.lithium_carbonate_reactor.flow_mass_precipitate["Li2CO3"]
                * (2 * li_mw / li2co3_mw)
            )
            
            return li_in_li2co3 == fs.target_li_recovery * li_in_mass
    
def fix_unit_model_variables(m, stage=3):
    """
    Fix the required variables for each unit model in the flowsheet.
    
    Args:
        stage: Stage of flowsheet being fixed
            1 - Feed, storage tank, and pump only
            2 - Stage 1 + stoichiometric reactors
            3 - Stage 2 + dewaterers (complete flowsheet)
    """
    
    # ============================================================================
    # STAGE 1: STORAGE TANK AND PUMP
    # ============================================================================
    
    # Load default parameters from database (this fixes storage_time and surge_capacity)
    m.fs.brine_storage.load_parameters_from_database()
    
    m.fs.brine_pump.deltaP[0].fix(3e5 * units.Pa)
    m.fs.brine_pump.efficiency_pump[0].fix(0.75)
    
    # ============================================================================
    # STAGE 2: STOICHIOMETRIC REACTORS
    # ============================================================================
    
    if stage >= 2:
        # SODA ASH REACTOR (First softening stage)
        # Minimize reagent to reduce volumetric flow disturbances
        # Feed Mg: 0.022068 mol/s (0.536 g/s), precipitate minimal amount
        
        # Fix precipitate formation - very small to minimize flow disturbance
        m.fs.soda_ash_reactor.flow_mass_precipitate["MgCO3"].fix(0.0185e-3 * units.kg / units.s)  # 0.0185 g/s MgCO3
        
        # Fix waste stream solids fraction to define separator behavior
        m.fs.soda_ash_reactor.waste_mass_frac_precipitate.fix(0.05)  # 5% solids in waste stream
        
        # LIME REACTOR (Second softening stage)
        
        # Fix precipitate formation rates - very small amounts
        # Brucite: Target 0.1% of Mg → 0.000022 mol/s × 58.32 g/mol = 0.0013 g/s
        m.fs.lime_reactor.flow_mass_precipitate["Brucite"].fix(1.3e-6 * units.kg / units.s)  # 0.0013 g/s Mg(OH)2
        
        # Gypsum: Use only 10% of available SO4 to minimize disturbance
        # 0.1 × 6.14 mg/s SO4 → 0.00061 g/s SO4 → 0.0011 g/s CaSO4·2H2O
        m.fs.lime_reactor.flow_mass_precipitate["Gypsum"].fix(1.1e-6 * units.kg / units.s)  # 0.0011 g/s CaSO4·2H2O
        
        # Fix waste stream solids fraction to define separator behavior
        m.fs.lime_reactor.waste_mass_frac_precipitate.fix(0.02)  # 2% solids (very low)
        
        # LITHIUM CARBONATE REACTOR
        # Note: Li2CO3 precipitation is now determined by the li_recovery_constraint in modify_flowsheet
        
        # Fix waste stream solids fraction to define separator behavior  
        m.fs.lithium_carbonate_reactor.waste_mass_frac_precipitate.fix(0.20)  # 20% solids in waste stream
    
    if stage >= 3:
        # SODA ASH DEWATERING UNIT (Separator for MgCO3 precipitates)
        # Fix component-specific split fractions for soda ash dewatering
        # Overflow (clarified liquid) gets most water and dissolved ions
        # Underflow (concentrated solids) retains MgCO3 precipitates
        # Index: [time, outlet, component] for componentFlow split basis
        
        # Water: 95% to overflow (clarified liquid), 5% to underflow (moisture in solids)
        m.fs.soda_ash_dewatering.split_fraction[0, "overflow", "H2O"].fix(0.95)
        
        # Dissolved ions: 90% to overflow (stay in solution), 10% to underflow (entrapped in filter cake)
        m.fs.soda_ash_dewatering.split_fraction[0, "overflow", "Na"].fix(0.10)
        m.fs.soda_ash_dewatering.split_fraction[0, "overflow", "K"].fix(0.10)
        m.fs.soda_ash_dewatering.split_fraction[0, "overflow", "Li"].fix(0.10)
        m.fs.soda_ash_dewatering.split_fraction[0, "overflow", "Cl"].fix(0.10)
        m.fs.soda_ash_dewatering.split_fraction[0, "overflow", "SO4"].fix(0.10)
        m.fs.soda_ash_dewatering.split_fraction[0, "overflow", "B"].fix(0.10)
        m.fs.soda_ash_dewatering.split_fraction[0, "overflow", "H"].fix(0.10)
        m.fs.soda_ash_dewatering.split_fraction[0, "overflow", "HCO3"].fix(0.10)
        m.fs.soda_ash_dewatering.split_fraction[0, "overflow", "CO3"].fix(0.10)
        m.fs.soda_ash_dewatering.split_fraction[0, "overflow", "Mg"].fix(0.10)
        m.fs.soda_ash_dewatering.split_fraction[0, "overflow", "Ca"].fix(0.10)
    
        
        # SODA ASH CENTRIFUGE DEWATERING UNIT (Further dewatering of soda ash precipitates)
        # Fix component-specific split fractions for soda ash centrifuge dewatering
        # More aggressive water removal than RDVF
        # Index: [time, outlet, component] for componentFlow split basis
        
        # Water: 90% to overflow (clarified liquid), 10% to underflow (moisture in solids)
        m.fs.soda_ash_centrifuge.split_fraction[0, "overflow", "H2O"].fix(0.90)
        
        # All ions: 5% to overflow (stay in solution), 95% to underflow (entrapped in filter cake)
        m.fs.soda_ash_centrifuge.split_fraction[0, "overflow", "Na"].fix(0.05)
        m.fs.soda_ash_centrifuge.split_fraction[0, "overflow", "K"].fix(0.05)
        m.fs.soda_ash_centrifuge.split_fraction[0, "overflow", "Li"].fix(0.05)
        m.fs.soda_ash_centrifuge.split_fraction[0, "overflow", "Cl"].fix(0.05)
        m.fs.soda_ash_centrifuge.split_fraction[0, "overflow", "SO4"].fix(0.05)
        m.fs.soda_ash_centrifuge.split_fraction[0, "overflow", "B"].fix(0.05)
        m.fs.soda_ash_centrifuge.split_fraction[0, "overflow", "H"].fix(0.05)
        m.fs.soda_ash_centrifuge.split_fraction[0, "overflow", "HCO3"].fix(0.05)
        m.fs.soda_ash_centrifuge.split_fraction[0, "overflow", "CO3"].fix(0.05)
        m.fs.soda_ash_centrifuge.split_fraction[0, "overflow", "Mg"].fix(0.05)
        m.fs.soda_ash_centrifuge.split_fraction[0, "overflow", "Ca"].fix(0.05)
    
        
        # LIME DEWATERING UNIT (Separator for Mg(OH)2 and CaSO4 precipitates)
        # Fix component-specific split fractions for lime dewatering
        # Overflow (clarified liquid) gets most water and dissolved ions
        # Underflow (concentrated solids) retains Mg(OH)2 and CaSO4 precipitates
        # Index: [time, outlet, component] for componentFlow split basis
        
        # Water: 95% to overflow (clarified liquid), 5% to underflow (moisture in solids)
        m.fs.lime_dewatering.split_fraction[0, "overflow", "H2O"].fix(0.95)
        
        # Dissolved ions: 90% to overflow (stay in solution), 10% to underflow (entrapped in filter cake)
        m.fs.lime_dewatering.split_fraction[0, "overflow", "Na"].fix(0.05)
        m.fs.lime_dewatering.split_fraction[0, "overflow", "K"].fix(0.05)
        m.fs.lime_dewatering.split_fraction[0, "overflow", "Li"].fix(0.05)
        m.fs.lime_dewatering.split_fraction[0, "overflow", "Cl"].fix(0.05)
        m.fs.lime_dewatering.split_fraction[0, "overflow", "SO4"].fix(0.05)
        m.fs.lime_dewatering.split_fraction[0, "overflow", "B"].fix(0.05)
        m.fs.lime_dewatering.split_fraction[0, "overflow", "H"].fix(0.05)
        m.fs.lime_dewatering.split_fraction[0, "overflow", "HCO3"].fix(0.05)
        m.fs.lime_dewatering.split_fraction[0, "overflow", "CO3"].fix(0.05)
        m.fs.lime_dewatering.split_fraction[0, "overflow", "Mg"].fix(0.05)
        m.fs.lime_dewatering.split_fraction[0, "overflow", "Ca"].fix(0.05)
    
        
        # LIME CENTRIFUGE UNIT (Further dewatering of lime precipitates)
        # Fix component-specific split fractions for lime centrifuge
        # More aggressive water removal than belt filter press
        # Index: [time, outlet, component] for componentFlow split basis
        
        # Water: 85% to overflow (clarified liquid), 15% to underflow (moisture in solids)
        m.fs.lime_centrifuge.split_fraction[0, "overflow", "H2O"].fix(0.95)
        
        # All ions: 70% to overflow (stay in solution), 30% to underflow (entrapped in filter cake)
        m.fs.lime_centrifuge.split_fraction[0, "overflow", "Na"].fix(0.05)
        m.fs.lime_centrifuge.split_fraction[0, "overflow", "K"].fix(0.05)
        m.fs.lime_centrifuge.split_fraction[0, "overflow", "Li"].fix(0.05)
        m.fs.lime_centrifuge.split_fraction[0, "overflow", "Mg"].fix(0.05)
        m.fs.lime_centrifuge.split_fraction[0, "overflow", "Ca"].fix(0.05)
        m.fs.lime_centrifuge.split_fraction[0, "overflow", "Cl"].fix(0.05)
        m.fs.lime_centrifuge.split_fraction[0, "overflow", "SO4"].fix(0.05)
        m.fs.lime_centrifuge.split_fraction[0, "overflow", "B"].fix(0.05)
        m.fs.lime_centrifuge.split_fraction[0, "overflow", "H"].fix(0.05)
        m.fs.lime_centrifuge.split_fraction[0, "overflow", "HCO3"].fix(0.05)
        m.fs.lime_centrifuge.split_fraction[0, "overflow", "CO3"].fix(0.05)
    
        
        # LITHIUM DEWATERING UNIT (Separator acting as dewatering for Li2CO3 slurry)
        # Fix component-specific split fractions for lithium dewatering
        # Overflow (clarified liquid) gets most water and dissolved ions
        # Underflow (concentrated solids) retains Li2CO3 precipitate
        # Index: [time, outlet, component] for componentFlow split basis
        
        # Water: 95% to overflow (clarified liquid), 5% to underflow (moisture in solids)
        m.fs.li_dewatering.split_fraction[0, "overflow", "H2O"].fix(0.95)
        
        # Dissolved ions: 90% to overflow (stay in solution), 10% to underflow (entrapped in filter cake)
        m.fs.li_dewatering.split_fraction[0, "overflow", "Na"].fix(0.10)
        m.fs.li_dewatering.split_fraction[0, "overflow", "K"].fix(0.10)
        m.fs.li_dewatering.split_fraction[0, "overflow", "Mg"].fix(0.10)
        m.fs.li_dewatering.split_fraction[0, "overflow", "Ca"].fix(0.10)
        m.fs.li_dewatering.split_fraction[0, "overflow", "Cl"].fix(0.10)
        m.fs.li_dewatering.split_fraction[0, "overflow", "SO4"].fix(0.10)
        m.fs.li_dewatering.split_fraction[0, "overflow", "B"].fix(0.10)
        m.fs.li_dewatering.split_fraction[0, "overflow", "H"].fix(0.10)
        m.fs.li_dewatering.split_fraction[0, "overflow", "HCO3"].fix(0.10)
        m.fs.li_dewatering.split_fraction[0, "overflow", "CO3"].fix(0.10)
        m.fs.li_dewatering.split_fraction[0, "overflow", "Li"].fix(0.10)
    
    print("Unit model variables fixed successfully!")

def initialize_flowsheet(m, stage=3):
    """
    Initialize the flowsheet by setting up all unit models in sequence.
    
    Args:
        m: The flowsheet model to initialize
        stage: Stage of flowsheet to initialize
            1 - Feed, storage tank, and pump only
            2 - Stage 1 + stoichiometric reactors
            3 - Stage 2 + dewaterers (complete flowsheet)
        
    Returns:
        m: The initialized flowsheet model
    """
    print("\n" + "="*60)
    print(f"INITIALIZATION SEQUENCE - STAGE {stage}")
    print("="*60)
    
    # ============================================================================
    # STAGE 1: Feed, Storage Tank, and Pump
    # ============================================================================
    
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
    
    # ============================================================================
    # STAGE 2: Stoichiometric Reactors
    # ============================================================================
    
    if stage >= 2:
        # Propagate state to soda ash reactor
        print("\n4. Propagating state to soda ash reactor...")
        propagate_state(m.fs.pump_to_soda_ash)
        m.fs.soda_ash_reactor.initialize()
        m.fs.soda_ash_reactor.report()
        print("Soda ash reactor initialized successfully!")
        print(f"DOF after soda ash reactor: {degrees_of_freedom(m)}")
        
        # Propagate state to lime reactor
        print("\n5. Propagating state to lime reactor...")
        propagate_state(m.fs.soda_ash_to_lime)
        m.fs.lime_reactor.initialize()
        m.fs.lime_reactor.report()
        print("Lime reactor initialized successfully!")
        print(f"DOF after lime reactor: {degrees_of_freedom(m)}")
        
        # Propagate state to lithium carbonate reactor
        print("\n6. Propagating state to lithium carbonate reactor...")
        propagate_state(m.fs.lime_to_lithium)
        m.fs.lithium_carbonate_reactor.initialize()
        m.fs.lithium_carbonate_reactor.report()
        print("Lithium carbonate reactor initialized successfully!")
        print(f"DOF after lithium carbonate reactor: {degrees_of_freedom(m)}")
    
    # ============================================================================
    # STAGE 3: Dewaterers
    # ============================================================================
    
    if stage >= 3:
        # Propagate state to soda ash dewatering unit
        print("\n7. Propagating state to soda ash dewatering unit...")
        propagate_state(m.fs.soda_ash_to_dewatering)
        m.fs.soda_ash_dewatering.initialize()
        m.fs.soda_ash_dewatering.report()
        print("Soda ash dewatering unit initialized successfully!")
        print(f"DOF after soda ash dewatering: {degrees_of_freedom(m)}")
        
        # Propagate state to soda ash centrifuge dewatering unit
        print("\n8. Propagating state to soda ash centrifuge dewatering unit...")
        propagate_state(m.fs.soda_ash_dewatering_to_centrifuge)
        m.fs.soda_ash_centrifuge.initialize()
        m.fs.soda_ash_centrifuge.report()
        print("Soda ash centrifuge dewatering unit initialized successfully!")
        print(f"DOF after soda ash centrifuge: {degrees_of_freedom(m)}")
        
        # Propagate state to lime dewatering unit
        print("\n9. Propagating state to lime dewatering unit...")
        propagate_state(m.fs.lime_to_lime_dewater)
        m.fs.lime_dewatering.initialize()
        m.fs.lime_dewatering.report()
        print("Lime dewatering unit initialized successfully!")
        print(f"DOF after lime dewatering: {degrees_of_freedom(m)}")
        
        # Propagate state to lime centrifuge unit
        print("\n10. Propagating state to lime centrifuge unit...")
        propagate_state(m.fs.lime_dewatering_to_lime_centrifuge)
        m.fs.lime_centrifuge.initialize()
        m.fs.lime_centrifuge.report()
        print("Lime centrifuge unit initialized successfully!")
        print(f"DOF after lime centrifuge: {degrees_of_freedom(m)}")
        
        # Propagate state to lithium dewatering unit
        print("\n11. Propagating state to lithium dewatering unit...")
        propagate_state(m.fs.lithium_to_dewatering)
        m.fs.li_dewatering.initialize()
        m.fs.li_dewatering.report()
        print("Lithium dewatering unit initialized successfully!")
        print(f"DOF after lithium dewatering: {degrees_of_freedom(m)}")
    
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
    

    
    return m

def run_diagnostics(m, report_scaling=False, analyze_jacobian=False, 
                            check_jacobian_quality=False):
    """
    Run comprehensive scaling diagnostics on the flowsheet.
    
    Args:
        m: The flowsheet model
        report_scaling: Boolean flag to generate and print a detailed scaling factors report
        analyze_jacobian: Boolean flag to perform SVD analysis on the Jacobian to verify scaling
        check_jacobian_quality: Boolean flag to run DiagnosticsToolbox checks for extreme Jacobian values
    """
    
    # ============================================================================
    # REPORT SCALING FACTORS (if requested)
    # ============================================================================
    
    if report_scaling:
        print("\n" + "="*80)
        print("SCALING FACTORS REPORT")
        print("="*80)
        
        # Create a StringIO buffer to capture the report
        report_buffer = StringIO()
        
        # Report scaling factors for the entire flowsheet
        print("\n>>> FLOWSHEET LEVEL SCALING FACTORS <<<")
        report_scaling_factors(m.fs, ctype=pyo.Var, descend_into=True, stream=report_buffer)
        
        # Print the captured report
        report_content = report_buffer.getvalue()
        print(report_content)
        
        print("\n" + "="*80)
        print("END OF SCALING FACTORS REPORT")
        print("="*80 + "\n")
        input("Press enter to continue")
    
    # ============================================================================
    # SVD ANALYSIS OF JACOBIAN (if requested)
    # ============================================================================
    
    if analyze_jacobian:
        print("\n" + "="*80)
        print("SINGULAR VALUE DECOMPOSITION (SVD) ANALYSIS")
        print("="*80)
        print("\nAnalyzing the Jacobian matrix to verify scaling quality...")
        print("This helps identify ill-conditioned constraints and variables.\n")
        
        try:
            # Try sparse SVD first for efficiency
            print("Attempting sparse SVD analysis...")
            try:
                svd = SVDToolbox(
                    m.fs,
                    number_of_smallest_singular_values=10,
                    singular_value_tolerance=1e-4,
                    size_cutoff_in_singular_vector=0.1,
                    svd_callback=svd_sparse
                )
                svd.run_svd_analysis()
                print("✓ Sparse SVD completed successfully")
            except Exception as sparse_error:
                # Fallback to dense SVD if sparse fails
                print(f"⚠ Sparse SVD failed: {str(sparse_error)}")
                print("Falling back to dense SVD method...")
                
                svd = SVDToolbox(
                    m.fs,
                    number_of_smallest_singular_values=10,
                    singular_value_tolerance=1e-4,
                    size_cutoff_in_singular_vector=0.1,
                    svd_callback=svd_dense
                )
                svd.run_svd_analysis()
                print("✓ Dense SVD completed successfully")
            
            # Display the rank of equality constraints
            print("\n" + "-"*80)
            print("CONSTRAINT RANK ANALYSIS")
            print("-"*80)
            svd.display_rank_of_equality_constraints()
            
            # Display variables and constraints associated with smallest singular values
            print("\n" + "-"*80)
            print("VARIABLES AND CONSTRAINTS WITH SMALLEST SINGULAR VALUES")
            print("-"*80)
            print("Components with large values in singular vectors associated with")
            print("small singular values may indicate scaling issues.\n")
            svd.display_underdetermined_variables_and_constraints(singular_values=[1, 2, 3])
            
            # Print singular values summary
            print("\n" + "-"*80)
            print("SINGULAR VALUE SUMMARY")
            print("-"*80)
            print(f"Number of singular values computed: {len(svd.s)}")
            print(f"Smallest singular value: {svd.s[0]:.3e}")
            print(f"Largest singular value: {svd.s[-1]:.3e}")
            condition_number = svd.s[-1]/svd.s[0] if svd.s[0] > 0 else float('inf')
            print(f"Condition number (max/min): {condition_number:.3e}")
            
            # Print all singular values
            print(f"\nAll {len(svd.s)} smallest singular values:")
            for i, sv in enumerate(svd.s, 1):
                print(f"  σ_{i}: {sv:.3e}")
            
            # Interpretation guide
            print("\n" + "-"*80)
            print("INTERPRETATION AND RECOMMENDATIONS")
            print("-"*80)
            
            # Check for very small singular values
            small_sv_count = sum(1 for sv in svd.s if sv < 1e-6)
            if small_sv_count > 0:
                print(f"⚠ WARNING: {small_sv_count} singular value(s) < 1e-6 detected")
                print("   This may indicate:")
                print("   - Nearly linearly dependent constraints")
                print("   - Poor scaling of variables or constraints")
                print("   - Structural issues in the model")
                print("   → Review the variables/constraints listed above")
                print("   → Consider adjusting scaling factors for highlighted components")
            elif svd.s[0] < 1e-4:
                print(f"⚠ CAUTION: Smallest singular value is {svd.s[0]:.3e} (< 1e-4)")
                print("   The model may have minor scaling issues")
                print("   → Consider reviewing the scaling of highlighted components")
            else:
                print("✓ All singular values are above 1e-4 threshold")
                print("  The Jacobian appears reasonably well-scaled")
            
            # Check condition number
            print()
            if condition_number > 1e10:
                print(f"⚠ WARNING: Very high condition number ({condition_number:.2e} > 1e10)")
                print("   The model is severely ill-conditioned")
                print("   → Strongly recommend improving scaling")
                print("   → May experience solver convergence failures")
            elif condition_number > 1e8:
                print(f"⚠ WARNING: High condition number ({condition_number:.2e} > 1e8)")
                print("   The model is ill-conditioned and may be difficult to solve")
                print("   → Consider improving scaling to reduce condition number")
            elif condition_number > 1e6:
                print(f"⚠ CAUTION: Moderate condition number ({condition_number:.2e} > 1e6)")
                print("   Solver may experience some numerical difficulties")
                print("   → Consider minor scaling improvements")
            else:
                print(f"✓ Acceptable condition number ({condition_number:.2e})")
                print("  The Jacobian is well-conditioned for numerical solving")
            
            print("\n" + "="*80)
            print("END OF SVD ANALYSIS")
            print("="*80 + "\n")
            
        except ValueError as e:
            print(f"\n⚠ SVD Analysis could not be performed: {str(e)}")
            print("This typically occurs if the model has fewer than 2 equality constraints")
            print("or if the model structure doesn't support SVD analysis.")
            print("="*80 + "\n")
        except Exception as e:
            print(f"\n⚠ SVD Analysis failed with error: {str(e)}")
            print("This may occur due to Jacobian evaluation issues.")
            print("Consider running this analysis after model initialization.")
            print("="*80 + "\n")
        input("Press enter to continue")
    # ============================================================================
    # JACOBIAN QUALITY DIAGNOSTICS (if requested)
    # ============================================================================
    
    if check_jacobian_quality:
        print("\n" + "="*80)
        print("JACOBIAN QUALITY DIAGNOSTICS")
        print("="*80)
        print("\nRunning DiagnosticsToolbox to identify extreme Jacobian values...")
        print("This helps pinpoint specific scaling issues in variables and constraints.\n")
        
        try:
            # Initialize DiagnosticsToolbox
            dt = DiagnosticsToolbox(m.fs)
            
            # Check for extreme Jacobian entries
            print("\n" + "-"*80)
            print("EXTREME JACOBIAN ENTRIES")
            print("-"*80)
            print("Identifies individual Jacobian entries that are exceptionally large or small.")
            print("These often indicate poorly scaled variables or constraints.\n")
            dt.display_extreme_jacobian_entries()
            
            # Check for constraints with extreme Jacobian rows
            print("\n" + "-"*80)
            print("CONSTRAINTS WITH EXTREME JACOBIAN ROWS")
            print("-"*80)
            print("Constraints with extreme L2 norms in their Jacobian rows may be poorly scaled.\n")
            dt.display_constraints_with_extreme_jacobians()
            
            # Check for variables with extreme Jacobian columns
            print("\n" + "-"*80)
            print("VARIABLES WITH EXTREME JACOBIAN COLUMNS")
            print("-"*80)
            print("Variables with extreme L2 norms in their Jacobian columns may be poorly scaled.\n")
            dt.display_variables_with_extreme_jacobians()
            
            # Additional useful diagnostics
            print("\n" + "-"*80)
            print("VARIABLES NEAR BOUNDS")
            print("-"*80)
            print("Variables close to their bounds may cause solver issues.\n")
            dt.display_variables_near_bounds()
            
            # Check for variables with extreme values
            print("\n" + "-"*80)
            print("VARIABLES WITH EXTREME VALUES")
            print("-"*80)
            print("Variables with very large or small values may indicate scaling issues.\n")
            dt.display_variables_with_extreme_values()
            
            # Summary and recommendations
            print("\n" + "-"*80)
            print("DIAGNOSTICS SUMMARY")
            print("-"*80)
            print("Review the components listed above. Common fixes include:")
            print("  1. Adjusting scaling factors for highlighted variables")
            print("  2. Adjusting scaling factors for highlighted constraints")
            print("  3. Reformulating constraints with extreme coefficients")
            print("  4. Checking for unit consistency in the model")
            print("  5. Reviewing variable bounds and initial values")
            
            print("\n" + "="*80)
            print("END OF JACOBIAN QUALITY DIAGNOSTICS")
            print("="*80 + "\n")
            
        except Exception as e:
            print(f"\n⚠ Jacobian quality diagnostics failed with error: {str(e)}")
            print("This may occur if the model structure doesn't support these diagnostics")
            print("or if there are issues evaluating the Jacobian.")
            print("="*80 + "\n")
        input("Press enter to continue")
        
def build_flowsheet(stage=3):
    """
    Build the lithium carbonate plant flowsheet.
    
    Args:
        stage: Stage of flowsheet to build
            1 - Feed, storage tank, and pump only
            2 - Stage 1 + stoichiometric reactors
            3 - Stage 2 + dewaterers (complete flowsheet)
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
    # UNIT MODELS - STAGE 1: Feed, Storage Tank, and Pump
    # ============================================================================
    
    m.fs.brine_feed = Feed(property_package=m.fs.brine_props)
    
    # Create database for zero-order unit models
    m.db = Database()
    
    m.fs.brine_storage = StorageTank(
        property_package=m.fs.brine_props,
        database=m.db,
    )
    # m.fs.brine_pump_list = RangeSet(1,2 )
    m.fs.brine_pump = Pump(
        property_package=m.fs.brine_props,
    )
    
    # ============================================================================
    # UNIT MODELS - STAGE 2: Stoichiometric Reactors
    # ============================================================================
    
    if stage >= 2:
        # Define reagents for soda ash reactor (first softening stage)
        soda_ash_reagents = {
            "Na2CO3": {
                "mw": 105.99 * pyunits.g / pyunits.mol,
                "dissolution_stoichiometric": {"Na": 2, "CO3": 1},
                "density_reagent": 2.52 * pyunits.kg / pyunits.L,
            },
        }
        
        # Define precipitates for soda ash reactor
        soda_ash_precipitates = {
            "MgCO3": {
                "mw": 84.3139 * pyunits.g / pyunits.mol,
                "precipitation_stoichiometric": {"Mg": 1, "CO3": 1},
            },
        }
        
        m.fs.soda_ash_reactor = StoichiometricReactor(
            property_package=m.fs.brine_props,
            reagent=soda_ash_reagents,
            precipitate=soda_ash_precipitates,
        )
        
        # Define reagents for lime reactor (second softening stage)
        lime_reagents = {
            "CaO": {
                "mw": 56.0774 * pyunits.g / pyunits.mol,
                "dissolution_stoichiometric": {"Ca": 1},
                "density_reagent": 3.34 * pyunits.kg / pyunits.L,
            },
        }
        
        # Define precipitates for lime reactor
        lime_precipitates = {
            "Brucite": {
                "mw": 58.3197 * pyunits.g / pyunits.mol,
                "precipitation_stoichiometric": {"Mg": 1, "H2O": 2},
            },
            "Gypsum": {
                "mw": 136.14 * pyunits.g / pyunits.mol,
                "precipitation_stoichiometric": {"Ca": 1, "SO4": 1},
            },
        }
        
        m.fs.lime_reactor = StoichiometricReactor(
            property_package=m.fs.brine_props,
            reagent=lime_reagents,
            precipitate=lime_precipitates,
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
    
    # ============================================================================
    # UNIT MODELS - STAGE 3: Dewaterers
    # ============================================================================
    
    if stage >= 3:
        # Dewatering unit for soda ash precipitates (MgCO3)
        # Separates waste stream from soda ash reactor into concentrated solids and clarified liquid
        m.fs.soda_ash_dewatering = Separator(
            property_package=m.fs.brine_props,
            outlet_list=["overflow", "underflow"],
            split_basis=SplittingType.componentFlow  # Split each component independently
        )
        
        # Additional dewatering unit after soda ash dewatering (centrifuge type)
        # Further concentrates solids from soda ash dewatering underflow
        m.fs.soda_ash_centrifuge = Separator(
            property_package=m.fs.brine_props,
            outlet_list=["overflow", "underflow"],
            split_basis=SplittingType.componentFlow  # Split each component independently
        )
        
        # Dewatering unit for lime precipitates (Mg(OH)2 and CaSO4)
        # Separates waste stream from lime reactor into concentrated solids and clarified liquid
        m.fs.lime_dewatering = Separator(
            property_package=m.fs.brine_props,
            outlet_list=["overflow", "underflow"],
            split_basis=SplittingType.componentFlow  # Split each component independently
        )
        
        # Lime centrifuge unit for further dewatering of lime precipitates
        # Takes underflow from lime dewatering and further concentrates the solids
        m.fs.lime_centrifuge = Separator(
            property_package=m.fs.brine_props,
            outlet_list=["overflow", "underflow"],
            split_basis=SplittingType.componentFlow  # Split each component independently
        )
        
        # Dewatering unit to separate Li2CO3 slurry into concentrated solids and clarified liquid
        # Using IDAES Separator as a generic dewatering unit
        m.fs.li_dewatering = Separator(
            property_package=m.fs.brine_props,
            outlet_list=["overflow", "underflow"],
            split_basis=SplittingType.componentFlow  # Split each component independently
        )
    
    
    # ============================================================================
    # CONNECT UNIT MODELS
    # ============================================================================
    
    # Stage 1 connections
    m.fs.brine_feed_to_storage = Arc(source=m.fs.brine_feed.outlet, destination=m.fs.brine_storage.inlet)
    m.fs.storage_to_pump = Arc(source=m.fs.brine_storage.outlet, destination=m.fs.brine_pump.inlet)
    
    # Stage 2 connections
    if stage >= 2:
        m.fs.pump_to_soda_ash = Arc(source=m.fs.brine_pump.outlet, destination=m.fs.soda_ash_reactor.inlet)
        m.fs.soda_ash_to_lime = Arc(source=m.fs.soda_ash_reactor.outlet, destination=m.fs.lime_reactor.inlet)
        m.fs.lime_to_lithium = Arc(source=m.fs.lime_reactor.outlet, destination=m.fs.lithium_carbonate_reactor.inlet)
    
    # Stage 3 connections
    if stage >= 3:
        m.fs.soda_ash_to_dewatering = Arc(source=m.fs.soda_ash_reactor.waste, destination=m.fs.soda_ash_dewatering.inlet)
        m.fs.soda_ash_dewatering_to_centrifuge = Arc(source=m.fs.soda_ash_dewatering.underflow, destination=m.fs.soda_ash_centrifuge.inlet)
        m.fs.lime_to_lime_dewater = Arc(source=m.fs.lime_reactor.waste, destination=m.fs.lime_dewatering.inlet)
        m.fs.lime_dewatering_to_lime_centrifuge = Arc(source=m.fs.lime_dewatering.underflow, destination=m.fs.lime_centrifuge.inlet)
        m.fs.lithium_to_dewatering = Arc(source=m.fs.lithium_carbonate_reactor.waste, destination=m.fs.li_dewatering.inlet)
    # Note: Mg(OH)2 and CaSO4 precipitate slurry from lime reactor waste stream goes to lime dewatering
    # Note: Dewatered lime precipitates go to lime centrifuge for further concentration
    # Note: Final concentrated lime precipitates are available at m.fs.lime_centrifuge.underflow
    # Note: Clarified process water is available at m.fs.lime_dewatering.overflow and m.fs.lime_centrifuge.overflow
    # Note: Li2CO3 precipitate slurry from reactor waste stream goes to lithium dewatering
    # Note: Dewatered Li2CO3 product is available at m.fs.li_dewatering.underflow
    # Note: Clarified process water is available at m.fs.li_dewatering.overflow
    # Note: Treated brine (with Li removed) is available at m.fs.lithium_carbonate_reactor.outlet
    
    TransformationFactory("network.expand_arcs").apply_to(m)
    
    # ============================================================================
    # SET CONDITIONS
    # ============================================================================
    
    modify_unit_models(m, stage=stage)
    set_brine_feed_conditions(m)
    modify_flowsheet(m, stage=stage)
    fix_unit_model_variables(m, stage=stage)
    initialize_flowsheet(m, stage=stage)
    set_scaling_factors(m, stage=stage)

    run_diagnostics(m, report_scaling=False, analyze_jacobian=False, check_jacobian_quality=False)

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

def main():
    """
    Main function to build and run the flowsheet.
    """
    print("Building lithium carbonate plant flowsheet...")
    
    # Build the flowsheet (includes initialization, scaling, and diagnostics)
    m = build_flowsheet()
    
    print("\nFlowsheet built successfully!")
    print(f"Number of variables: {len(list(m.fs.component_data_objects(pyo.Var)))}")
    print(f"Number of constraints: {len(list(m.fs.component_data_objects(pyo.Constraint)))}")
    
    return m

if __name__ == "__main__":
    m = main()
