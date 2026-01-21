#################################################################################
# Lithium Carbonate Plant Flowsheet
# Salar de Carmen (Antofagasta) Process
#
# This module implements a staged flowsheet build approach for developing and
# debugging the lithium carbonate processing plant. The flowsheet can be built
# in 5 progressive stages:
#
# Stage 1: Feed, storage tank, and pump only
#          - Establishes basic brine feed conditions and pumping
#
# Stage 2: Stage 1 + soda ash reactor
#          - Adds first softening stage (MgCO3 and CaCO3 precipitation)
#          - Uses Na2CO3 as reagent
#
# Stage 3: Stage 2 + lime reactor  
#          - Adds second softening stage (Brucite, Gypsum, and CaCO3 precipitation)
#          - Uses Ca(OH)2 as reagent
#
# Stage 4: Stage 3 + lithium carbonate reactor
#          - Adds lithium precipitation stage (Li2CO3 precipitation)
#          - Uses Na2CO3 as reagent
#
# Stage 5: Stage 4 + dewatering units (complete flowsheet)
#          - Adds all dewatering/solid-liquid separation units
#          - Includes vacuum filter, centrifuges, and press filters
#
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
from pyomo.core.base.param import Param

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
from watertap_contrib.reflo.analysis.example_flowsheets.li_processing.pc_scaling_factors import set_scaling_factors

def modify_unit_models(m):
    """Modify variables and constraints for unit models."""      
    if hasattr(m.fs, 'soda_ash_vacuum_filter'):
        m.fs.soda_ash_vacuum_filter.electricity_consumption = pyo.Var(
            m.fs.time,
            initialize=0.1,
            units=pyunits.kW,
            bounds=(0, None),
            doc="Electricity consumption of soda ash vacuum filter unit"
        )
        
        m.fs.soda_ash_vacuum_filter.energy_electric_flow_vol_inlet = pyo.Param(
            m.fs.time,
            initialize=0.006,
            units=pyunits.kWh / pyunits.m**3,
            mutable=True,
            doc="Specific electricity intensity for belt filter press"
        )
        
        @m.fs.soda_ash_vacuum_filter.Constraint(m.fs.time, doc="Electricity consumption equation")
        def soda_ash_eq_electricity_consumption(blk, t):
            return blk.electricity_consumption[t] == pyunits.convert(
                blk.energy_electric_flow_vol_inlet[t] * blk.mixed_state[t].flow_vol,
                to_units=pyunits.kW,
            )
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
        m.fs.lime_press_filter.electricity_consumption = pyo.Var(
            m.fs.time,
            initialize=0.1,
            units=pyunits.kW,
            bounds=(0, None),
            doc="Electricity consumption of softening dewatering unit"
        )
        
        m.fs.lime_press_filter.energy_electric_flow_vol_inlet = pyo.Param(
            m.fs.time,
            initialize=0.006,
            units=pyunits.kWh / pyunits.m**3,
            mutable=True,
            doc="Specific electricity intensity for belt filter press"
        )
        
        @m.fs.lime_press_filter.Constraint(m.fs.time, doc="Electricity consumption equation")
        def lime_press_filter_eq_electricity_consumption(blk, t):
            return blk.electricity_consumption[t] == pyunits.convert(
                blk.energy_electric_flow_vol_inlet[t] * blk.mixed_state[t].flow_vol,
                to_units=pyunits.kW,
            )
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
    """Set brine feed conditions based on Salar de Carmen (Antofagasta) composition."""
    T_ref = 298.15 * pyunits.K
    P_ref = 101325 * pyunits.Pa
    
    m.fs.brine_feed.properties[0].temperature.fix(T_ref)
    m.fs.brine_feed.properties[0].pressure.fix(P_ref)
    
    total_flow_mass = 13.568 * pyunits.kg / pyunits.s
    density = 1252 * pyunits.g / pyunits.L
    total_flow_vol = total_flow_mass / density
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
        "OH": 17.008 * pyunits.g/pyunits.mol,
        "HCO3": 61.0168 * pyunits.g/pyunits.mol,
        "CO3": 60.0092 * pyunits.g/pyunits.mol,
    }
    
    # Concentrations in ppm (mg/kg) - Salar de Carmen composition
    ppm = {
        "Na": 570,
        "K": 160,
        "Mg": 19200,
        "Li": 60000,
        "Ca": 530,
        "Cl": 351000,
        "SO4": 220,
        "B": 6270,
        "HCO3": 164000, #230*1/(1-0.986),
        "CO3": 50,
    }
    
    # Convert ppm to molar flow rates
    for comp in ppm:
        mass_fraction = ppm[comp] / 1e6
        comp_mass_flow = mass_fraction * total_flow_mass
        comp_molar_flow = comp_mass_flow * 1000 / MW[comp]
        m.fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", comp].fix(pyo.value(comp_molar_flow))

    # H+ from pH (assuming pH = 6.5)
    H_conc_mol_L = 3.16e-7 * pyunits.mol / pyunits.L
    H_flow_mol_s = H_conc_mol_L * total_flow_vol
    m.fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", "H"].fix(pyo.value(H_flow_mol_s))
    
    # OH- from pH (assuming pH = 6.5, pOH = 7.5)
    OH_conc_mol_L = 3.16e-8 * pyunits.mol / pyunits.L
    OH_flow_mol_s = OH_conc_mol_L * total_flow_vol
    m.fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", "OH"].fix(pyo.value(OH_flow_mol_s))
    
    # Water: calculate as difference from total (to ensure mass balance)
    total_solute_mass_fraction = sum(ppm[c] / 1e6 for c in ppm) + (H_conc_mol_L * MW["H"] / density) + (OH_conc_mol_L * MW["OH"] / density)
    water_mass_fraction = 1.0 - total_solute_mass_fraction  # dimensionless
    water_mass_flow = water_mass_fraction * total_flow_mass  # kg/s
    water_molar_flow = water_mass_flow / MW["H2O"]  # mol/s
    m.fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", "H2O"].fix(pyo.value(water_molar_flow))

def modify_flowsheet(m):
    # Molecular weights for stoichiometric calculations
    mgco3_mw = 84.3139e-3 * pyunits.kg / pyunits.mol
    caco3_mw = 100.09e-3 * pyunits.kg / pyunits.mol
    na2co3_mw = 105.99e-3 * pyunits.kg / pyunits.mol
    caoh2_mw = 74.093e-3 * pyunits.kg / pyunits.mol
    brucite_mw = 58.3197e-3 * pyunits.kg / pyunits.mol
    gypsum_mw = 136.14e-3 * pyunits.kg / pyunits.mol
    li2co3_mw = 73.89e-3 * pyunits.kg / pyunits.mol
    
    if hasattr(m.fs, 'soda_ash_reactor'):
        m.fs.soda_ash_reactor.reaction_rate_constant_mg = pyo.Var(
            initialize=2e-3,
            bounds=(1e-6, 1.0),
            units=pyunits.s**-1,
            doc="First-order reaction rate constant for magnesium precipitation in soda ash reactor"
        )
        m.fs.soda_ash_reactor.reaction_rate_constant_mg_param = pyo.Param(
            initialize=2e-3,
            mutable=True,
            units=pyunits.s**-1,
            doc="Parameter for first-order magnesium precipitation reaction rate constant"
        )
        m.fs.soda_ash_reactor.reaction_rate_constant_mg.fix(m.fs.soda_ash_reactor.reaction_rate_constant_mg_param)
        
        m.fs.soda_ash_reactor.reactor_volume = pyo.Var(
            initialize=100,
            bounds=(1, 10000),
            units=pyunits.m**3,
            doc="Volume of soda ash reactor"
        )
    
    if hasattr(m.fs, 'lime_reactor'):
        m.fs.lime_reactor.reaction_rate_constant_mg = pyo.Var(
            initialize=3e-2,
            bounds=(1e-6, 1.0),
            units=pyunits.s**-1,
            doc="First-order reaction rate constant for magnesium precipitation in lime reactor"
        )
        m.fs.lime_reactor.reaction_rate_constant_mg_param = pyo.Param(
            initialize=3e-2,
            mutable=True,
            units=pyunits.s**-1,
            doc="Parameter for first-order magnesium precipitation reaction rate constant"
        )
        m.fs.lime_reactor.reaction_rate_constant_mg.fix(m.fs.lime_reactor.reaction_rate_constant_mg_param)
        
        m.fs.lime_reactor.reactor_volume = pyo.Var(
            initialize=100,
            bounds=(1, 10000),
            units=pyunits.m**3,
            doc="Volume of lime reactor"
        )
    
    if hasattr(m.fs, 'lithium_carbonate_reactor'):
        m.fs.lithium_carbonate_reactor.reaction_rate_constant_li = pyo.Var(
            initialize=2e-3,
            bounds=(1e-6, 1.0),
            units=pyunits.s**-1,
            doc="First-order reaction rate constant for lithium precipitation in lithium carbonate reactor"
        )
        m.fs.lithium_carbonate_reactor.reaction_rate_constant_li_param = pyo.Param(
            initialize=2e-3,
            mutable=True,
            units=pyunits.s**-1,
            doc="Parameter for first-order lithium precipitation reaction rate constant"
        )
        m.fs.lithium_carbonate_reactor.reaction_rate_constant_li.fix(m.fs.lithium_carbonate_reactor.reaction_rate_constant_li_param)
        
        m.fs.lithium_carbonate_reactor.reactor_volume = pyo.Var(
            initialize=500,
            bounds=(1, 10000),
            units=pyunits.m**3,
            doc="Volume of lithium carbonate reactor"
        )

    # Annual reagent inputs (based on industrial-scale operation)
    m.fs.annual_soda_ash_input = pyo.Var(
        initialize=144402000,
        bounds=(0, None),
        units=pyunits.kg / pyunits.year,
        doc="Annual soda ash input (144,402 tonnes/year)"
    )
    m.fs.annual_soda_ash_input_param = pyo.Param(
        initialize=144402000,
        mutable=True,
        units=pyunits.kg / pyunits.year,
        doc="Parameter for annual soda ash input"
    )
    m.fs.annual_soda_ash_input.fix(m.fs.annual_soda_ash_input_param)

    m.fs.soda_ash_input_split_fraction = pyo.Var(
        initialize=0.6895,
        bounds=(0, 1),
        units=pyunits.dimensionless,
        doc="Fraction of soda ash input to soda ash reactor"
    )
    m.fs.soda_ash_input_split_fraction_param = pyo.Param(
        initialize=0.6895,
        mutable=True,
        units=pyunits.dimensionless,
        doc="Parameter for fraction of soda ash input to soda ash reactor"
    )
    m.fs.soda_ash_input_split_fraction.fix(m.fs.soda_ash_input_split_fraction_param)
    
    m.fs.annual_lime_input = pyo.Var(
        initialize=3356800,
        bounds=(0, None),
        units=pyunits.kg / pyunits.year,
        doc="Annual lime input (3,356.8 tonnes/year)"
    )
    m.fs.annual_lime_input_param = pyo.Param(
        initialize=3356800,
        mutable=True,
        units=pyunits.kg / pyunits.year,
        doc="Parameter for annual lime input"
    )
    m.fs.annual_lime_input.fix(m.fs.annual_lime_input_param)

    # m.fs.annual_water_input = pyo.Var(
    #     initialize=997.047*797259,
    #     bounds=(0, None),
    #     units=pyunits.kg / pyunits.year,
    #     doc="Annual water input"
    # )
    # m.fs.annual_water_input.fix(424008000)

    m.fs.soda_ash_solution_molality = pyo.Var(
        initialize=30,
        bounds=(0, None),
        units=pyunits.mol / pyunits.kg,
        doc="Molality of soda ash solution"
    )
    m.fs.soda_ash_solution_molality_param = pyo.Param(
        initialize=4,
        mutable=True,
        units=pyunits.mol / pyunits.kg,
        doc="Parameter for soda ash solution molality"
    )
    m.fs.soda_ash_solution_molality.fix(m.fs.soda_ash_solution_molality_param)
    
    m.fs.lime_solution_molality = pyo.Var(
        initialize=1.5,
        bounds=(0, None),
        units=pyunits.mol / pyunits.kg,
        doc="Molality of lime solution"
    )
    m.fs.lime_solution_molality_param = pyo.Param(
        initialize=1.5,
        mutable=True,
        units=pyunits.mol / pyunits.kg,
        doc="Parameter for lime solution molality"
    )
    m.fs.lime_solution_molality.fix(m.fs.lime_solution_molality_param)

    # Stoichiometric fractions for reactor molar balances
    m.fs.magnesium_removal_fraction_soda_ash_reactor = pyo.Var(
        initialize=0.45,
        bounds=(0, None),
        units=pyunits.dimensionless,
        doc="Molar magnesium removal fraction from soda ash reactor"
    )
    m.fs.magnesium_removal_fraction_soda_ash_reactor_param = pyo.Param(
        initialize=0.45,
        mutable=True,
        units=pyunits.dimensionless,
        doc="Parameter for magnesium removal fraction from soda ash reactor"
    )
    m.fs.magnesium_removal_fraction_soda_ash_reactor.fix(m.fs.magnesium_removal_fraction_soda_ash_reactor_param)
    
    m.fs.magnesium_removal_fraction_lime_reactor = pyo.Var(
        initialize=0.9,
        bounds=(0, None),
        units=pyunits.dimensionless,
        doc="Molar magnesium removal fraction from lime reactor"
    )
    m.fs.magnesium_removal_fraction_lime_reactor_param = pyo.Param(
        initialize=0.9,
        mutable=True,
        units=pyunits.dimensionless,
        doc="Parameter for magnesium removal fraction from lime reactor"
    )
    m.fs.magnesium_removal_fraction_lime_reactor.fix(m.fs.magnesium_removal_fraction_lime_reactor_param)
    
    m.fs.calcium_removal_fraction_soda_ash_reactor = pyo.Var(
        initialize=0.2,
        bounds=(0, None),
        units=pyunits.dimensionless,
        doc="Molar calcium removal fraction from soda ash reactor"
    )
    m.fs.calcium_removal_fraction_soda_ash_reactor_param = pyo.Param(
        initialize=0.2,
        mutable=True,
        units=pyunits.dimensionless,
        doc="Parameter for calcium removal fraction from soda ash reactor"
    )
    m.fs.calcium_removal_fraction_soda_ash_reactor.fix(m.fs.calcium_removal_fraction_soda_ash_reactor_param)
    
    m.fs.calcium_removal_fraction_lime_reactor = pyo.Var(
        initialize=0.5,
        bounds=(0, None),
        units=pyunits.dimensionless,
        doc="Molar calcium removal fraction from lime reactor"
    )
    m.fs.calcium_removal_fraction_lime_reactor_param = pyo.Param(
        initialize=0.5,
        mutable=True,
        units=pyunits.dimensionless,
        doc="Parameter for calcium removal fraction from lime reactor"
    )
    m.fs.calcium_removal_fraction_lime_reactor.fix(m.fs.calcium_removal_fraction_lime_reactor_param)

    m.fs.sulfate_removal_fraction_lime_reactor = pyo.Var(
        initialize=0.9,
        bounds=(0, None),
        units=pyunits.dimensionless,
        doc="Molar sulfate removal fraction from lime reactor"
    )
    m.fs.sulfate_removal_fraction_lime_reactor_param = pyo.Param(
        initialize=0.9,
        mutable=True,
        units=pyunits.dimensionless,
        doc="Parameter for sulfate removal fraction from lime reactor"
    )
    m.fs.sulfate_removal_fraction_lime_reactor.fix(m.fs.sulfate_removal_fraction_lime_reactor_param)

    m.fs.lithium_removal_fraction_lithium_reactor = pyo.Var(
        initialize=0.4,
        bounds=(0, None),
        units=pyunits.dimensionless,
        doc="Molar lithium removal fraction from lithium reactor"
    )
    m.fs.lithium_removal_fraction_lithium_reactor_param = pyo.Param(
        initialize=0.4,
        mutable=True,
        units=pyunits.dimensionless,
        doc="Parameter for lithium removal fraction from lithium reactor"
    )
    m.fs.lithium_removal_fraction_lithium_reactor.fix(m.fs.lithium_removal_fraction_lithium_reactor_param)

    if hasattr(m.fs, 'soda_ash_reactor') and hasattr(m.fs.soda_ash_reactor, 'reactor_volume'):
        @m.fs.soda_ash_reactor.Constraint(doc="Soda ash reactor volume sizing based on Mg removal (first-order kinetics)")
        def reactor_volume_constraint(blk):
            inlet_mass_flow = mgco3_mw * blk.precipitation_reactor.properties_in[0].flow_mol_phase_comp["Liq", "Mg"]
            inlet_concentration = blk.precipitation_reactor.properties_in[0].flow_mol_phase_comp["Liq", "Mg"] / blk.precipitation_reactor.properties_in[0].flow_vol
            X = m.fs.magnesium_removal_fraction_soda_ash_reactor
            return blk.reactor_volume * blk.reaction_rate_constant_mg * inlet_concentration * (1 - X) * mgco3_mw == inlet_mass_flow * X
    
    if hasattr(m.fs, 'lime_reactor') and hasattr(m.fs.lime_reactor, 'reactor_volume'):
        @m.fs.lime_reactor.Constraint(doc="Lime reactor volume sizing based on Mg removal (first-order kinetics)")
        def reactor_volume_constraint(blk):
            inlet_mass_flow = brucite_mw * blk.precipitation_reactor.properties_in[0].flow_mol_phase_comp["Liq", "Mg"]
            inlet_concentration = blk.precipitation_reactor.properties_in[0].flow_mol_phase_comp["Liq", "Mg"] / blk.precipitation_reactor.properties_in[0].flow_vol
            X = m.fs.magnesium_removal_fraction_lime_reactor
            return blk.reactor_volume * blk.reaction_rate_constant_mg * inlet_concentration * (1 - X) * brucite_mw == inlet_mass_flow * X
    
    if hasattr(m.fs, 'lithium_carbonate_reactor') and hasattr(m.fs.lithium_carbonate_reactor, 'reactor_volume'):
        @m.fs.lithium_carbonate_reactor.Constraint(doc="Lithium reactor volume sizing based on Li removal (first-order kinetics)")
        def reactor_volume_constraint(blk):
            inlet_mass_flow = li2co3_mw / 2 * blk.precipitation_reactor.properties_in[0].flow_mol_phase_comp["Liq", "Li"]
            inlet_concentration = blk.precipitation_reactor.properties_in[0].flow_mol_phase_comp["Liq", "Li"] / blk.precipitation_reactor.properties_in[0].flow_vol
            X = m.fs.lithium_removal_fraction_lithium_reactor
            return blk.reactor_volume * blk.reaction_rate_constant_li * inlet_concentration * (1 - X) * li2co3_mw / 2 == inlet_mass_flow * X

    if hasattr(m.fs, 'soda_ash_reactor'):
        @m.fs.Constraint(doc="Soda ash reactor input constraint")
        def soda_ash_input_soda_ash_reactor_constraint(fs):
            return fs.soda_ash_reactor.flow_mass_reagent["Na2CO3"] == pyunits.convert(fs.annual_soda_ash_input * fs.soda_ash_input_split_fraction, to_units=pyunits.kg / pyunits.second)

        @m.fs.Constraint(doc="Magnesium removal fraction from soda ash reactor")
        def magnesium_removal_fraction_soda_ash_reactor_constraint(fs):
            return fs.soda_ash_reactor.flow_mass_precipitate["MgCO3"] == mgco3_mw * fs.magnesium_removal_fraction_soda_ash_reactor * fs.soda_ash_reactor.precipitation_reactor.properties_in[0].flow_mol_phase_comp["Liq", "Mg"]
        
        @m.fs.Constraint(doc="Calcium removal fraction from soda ash reactor")
        def calcium_removal_fraction_soda_ash_reactor_constraint(fs):
            return fs.soda_ash_reactor.flow_mass_precipitate["CaCO3"] == caco3_mw * fs.calcium_removal_fraction_soda_ash_reactor * fs.soda_ash_reactor.precipitation_reactor.properties_in[0].flow_mol_phase_comp["Liq", "Ca"]
        
        @m.fs.Constraint(doc="Water reagent to soda ash reagent ratio 1")
        def soda_ash_solution_molality_constraint_1(fs):
            return fs.soda_ash_solution_molality * fs.soda_ash_reactor.flow_mass_reagent["H2O"] * na2co3_mw == fs.soda_ash_reactor.flow_mass_reagent["Na2CO3"]

    if hasattr(m.fs, 'lime_reactor'):
        @m.fs.Constraint(doc="Lime annual input constraint")
        def lime_annual_input_constraint(fs):
            return fs.lime_reactor.flow_mass_reagent["Ca(OH)2"] == pyunits.convert(
                fs.annual_lime_input,
                to_units=pyunits.kg / pyunits.second
            )

        @m.fs.Constraint(doc="Magnesium removal fraction from lime reactor")
        def magnesium_removal_fraction_lime_reactor_constraint(fs):
            return fs.lime_reactor.flow_mass_precipitate["Brucite"] == brucite_mw * fs.magnesium_removal_fraction_lime_reactor * fs.lime_reactor.precipitation_reactor.properties_in[0].flow_mol_phase_comp["Liq", "Mg"]
        
        @m.fs.Constraint(doc="Calcium removal fraction from lime reactor")
        def calcium_removal_fraction_lime_reactor_constraint(fs):
            return (fs.lime_reactor.flow_mass_precipitate["CaCO3"] / caco3_mw + 
                    fs.lime_reactor.flow_mass_precipitate["Gypsum"] / gypsum_mw) == (
                    fs.calcium_removal_fraction_lime_reactor * 
                    fs.lime_reactor.precipitation_reactor.properties_in[0].flow_mol_phase_comp["Liq", "Ca"])
        
        @m.fs.Constraint(doc="Sulfate removal fraction from lime reactor")
        def sulfate_removal_fraction_lime_reactor_constraint(fs):
            return fs.lime_reactor.flow_mass_precipitate["Gypsum"] == gypsum_mw * fs.sulfate_removal_fraction_lime_reactor * fs.lime_reactor.precipitation_reactor.properties_in[0].flow_mol_phase_comp["Liq", "SO4"]
        
        @m.fs.Constraint(doc="Water reagent to lime reagent ratio")
        def lime_solution_molality_constraint(fs):
            return fs.lime_solution_molality * fs.lime_reactor.flow_mass_reagent["H2O"] * caoh2_mw == fs.lime_reactor.flow_mass_reagent["Ca(OH)2"]

    if hasattr(m.fs, 'lithium_carbonate_reactor'):
        @m.fs.Constraint(doc="Lithium reactor input constraint")
        def soda_ash_input_lithium_reactor_constraint(fs):
            return fs.lithium_carbonate_reactor.flow_mass_reagent["Na2CO3"] == pyunits.convert(fs.annual_soda_ash_input * (1 - fs.soda_ash_input_split_fraction), to_units=pyunits.kg / pyunits.second)

        @m.fs.Constraint(doc="Lithium removal fraction from lithium reactor")
        def lithium_removal_fraction_lithium_reactor_constraint(fs):
            return fs.lithium_carbonate_reactor.flow_mass_precipitate["Li2CO3"] * 2 == li2co3_mw * fs.lithium_removal_fraction_lithium_reactor * fs.lithium_carbonate_reactor.precipitation_reactor.properties_in[0].flow_mol_phase_comp["Liq", "Li"]
        
        @m.fs.Constraint(doc="Water reagent to soda ash reagent ratio 2")
        def soda_ash_solution_molality_constraint_2(fs):
            return fs.soda_ash_solution_molality * fs.lithium_carbonate_reactor.flow_mass_reagent["H2O"] * na2co3_mw == fs.lithium_carbonate_reactor.flow_mass_reagent["Na2CO3"]
        
    if hasattr(m.fs, 'soda_ash_vacuum_filter'):
        m.fs.soda_ash_vacuum_filter_ion_split_fraction = pyo.Param(
            initialize=0.05,
            mutable=True,
            units=pyunits.dimensionless,
            doc="Ion split fraction to overflow for soda ash vacuum filter unit"
        )
        
        m.fs.soda_ash_centrifuge_ion_split_fraction = pyo.Param(
            initialize=0.05,
            mutable=True,
            units=pyunits.dimensionless,
            doc="Ion split fraction to overflow for soda ash centrifuge unit"
        )
        
        m.fs.lime_press_filter_ion_split_fraction = pyo.Param(
            initialize=0.05,
            mutable=True,
            units=pyunits.dimensionless,
            doc="Ion split fraction to overflow for lime press filter unit"
        )
        
        m.fs.lime_centrifuge_ion_split_fraction = pyo.Param(
            initialize=0.05,
            mutable=True,
            units=pyunits.dimensionless,
            doc="Ion split fraction to overflow for lime centrifuge unit"
            )

        m.fs.lithium_dewatering_ion_split_fraction = pyo.Param(
            initialize=0.05,
            mutable=True,
            units=pyunits.dimensionless,
            doc="Ion split fraction to overflow for lithium dewatering unit"
        )

def fix_unit_model_variables(m):
    m.fs.brine_storage.load_parameters_from_database()
    
    m.fs.brine_pump.deltaP[0].fix(3e5 * units.Pa)
    m.fs.brine_pump.efficiency_pump[0].fix(0.75)
    
    if hasattr(m.fs, 'soda_ash_reactor'):
        m.fs.soda_ash_reactor.waste_mass_frac_precipitate.fix(0.5)
    
    if hasattr(m.fs, 'lime_reactor'):
        m.fs.lime_reactor.waste_mass_frac_precipitate.fix(0.5)
    
    if hasattr(m.fs, 'lithium_carbonate_reactor'):
        m.fs.lithium_carbonate_reactor.waste_mass_frac_precipitate.fix(0.5)
    
    if hasattr(m.fs, 'soda_ash_vacuum_filter'):
        # Dewatering unit split fractions: overflow gets clarified liquid, underflow gets concentrated solids
        ion_list = ["Na", "K", "Li", "Cl", "SO4", "B", "H", "OH", "HCO3", "CO3", "Mg", "Ca"]

        m.fs.soda_ash_vacuum_filter.split_fraction[0, "overflow", "H2O"].fix(0.95)
        for ion in ion_list:
            m.fs.soda_ash_vacuum_filter.split_fraction[0, "overflow", ion].fix(
                m.fs.soda_ash_vacuum_filter_ion_split_fraction.value
            )
        
        m.fs.soda_ash_centrifuge.split_fraction[0, "overflow", "H2O"].fix(0.95)
        for ion in ion_list:
            m.fs.soda_ash_centrifuge.split_fraction[0, "overflow", ion].fix(
                m.fs.soda_ash_centrifuge_ion_split_fraction.value
            )
        
        m.fs.lime_press_filter.split_fraction[0, "overflow", "H2O"].fix(0.95)
        for ion in ion_list:
            m.fs.lime_press_filter.split_fraction[0, "overflow", ion].fix(
                m.fs.lime_press_filter_ion_split_fraction.value
            )
        
        m.fs.lime_centrifuge.split_fraction[0, "overflow", "H2O"].fix(0.95)
        for ion in ion_list:
            m.fs.lime_centrifuge.split_fraction[0, "overflow", ion].fix(
                m.fs.lime_centrifuge_ion_split_fraction.value
            )
        
        m.fs.li_dewatering.split_fraction[0, "overflow", "H2O"].fix(0.95)
        for ion in ion_list:
            m.fs.li_dewatering.split_fraction[0, "overflow", ion].fix(
                m.fs.lithium_dewatering_ion_split_fraction.value
            )

def initialize_flowsheet(m):
    """Initialize flowsheet units in sequence, propagating state between units."""
    print("\n" + "="*60)
    print("INITIALIZATION SEQUENCE")
    print("="*60)
    
    print("\n1. Initializing brine feed...")
    m.fs.brine_feed.initialize()
    m.fs.brine_feed.report()
    check_unfixed_variables(m.fs.brine_feed.properties[0], "brine_feed.properties[0]")
    
    print("\n2. Propagating state to storage tank...")
    propagate_state(m.fs.brine_feed_to_storage)
    m.fs.brine_storage.initialize()
    m.fs.brine_storage.report()
    print(f"DOF after brine storage: {degrees_of_freedom(m)}")

    print("\n3. Propagating state to pump...")
    propagate_state(m.fs.storage_to_pump)
    m.fs.brine_pump.initialize()
    m.fs.brine_pump.report()
    print(f"DOF after brine pump: {degrees_of_freedom(m)}")
    
    if hasattr(m.fs, 'soda_ash_reactor'):
        print("\n4. Propagating state to soda ash reactor...")
        propagate_state(m.fs.pump_to_soda_ash)
        m.fs.soda_ash_reactor.initialize()
        m.fs.soda_ash_reactor.report()
        print(f"DOF after soda ash reactor: {degrees_of_freedom(m)}")
    
    if hasattr(m.fs, 'lime_reactor'):
        print("\n5. Propagating state to lime reactor...")
        propagate_state(m.fs.soda_ash_to_lime)
        m.fs.lime_reactor.initialize()
        m.fs.lime_reactor.report()
        print(f"DOF after lime reactor: {degrees_of_freedom(m)}")
    
    if hasattr(m.fs, 'lithium_carbonate_reactor'):
        print("\n6. Propagating state to lithium carbonate reactor...")
        propagate_state(m.fs.lime_to_lithium)
        m.fs.lithium_carbonate_reactor.initialize()
        m.fs.lithium_carbonate_reactor.report()
        print(f"DOF after lithium carbonate reactor: {degrees_of_freedom(m)}")
    
    if hasattr(m.fs, 'soda_ash_vacuum_filter'):
        print("\n7. Propagating state to soda ash vacuum filter unit...")
        propagate_state(m.fs.soda_ash_to_vacuum_filter)
        m.fs.soda_ash_vacuum_filter.initialize()
        m.fs.soda_ash_vacuum_filter.report()
        print(f"DOF after soda ash vacuum filter: {degrees_of_freedom(m)}")
        
        print("\n8. Propagating state to soda ash centrifuge dewatering unit...")
        propagate_state(m.fs.soda_ash_vacuum_filter_to_centrifuge)
        m.fs.soda_ash_centrifuge.initialize()
        m.fs.soda_ash_centrifuge.report()
        print(f"DOF after soda ash centrifuge: {degrees_of_freedom(m)}")
        
        print("\n9. Propagating state to lime press filter unit...")
        propagate_state(m.fs.lime_to_lime_press_filter)
        m.fs.lime_press_filter.initialize()
        m.fs.lime_press_filter.report()
        print(f"DOF after lime press filter: {degrees_of_freedom(m)}")
        
        print("\n10. Propagating state to lime centrifuge unit...")
        propagate_state(m.fs.lime_press_filter_to_lime_centrifuge)
        m.fs.lime_centrifuge.initialize()
        m.fs.lime_centrifuge.report()
        print(f"DOF after lime centrifuge: {degrees_of_freedom(m)}")
        
        print("\n11. Propagating state to lithium dewatering unit...")
        propagate_state(m.fs.lithium_to_dewatering)
        m.fs.li_dewatering.initialize()
        m.fs.li_dewatering.report()
        print(f"DOF after lithium dewatering: {degrees_of_freedom(m)}")
    
    print("\n" + "="*60)
    print("INITIALIZATION COMPLETE")
    print("="*60)
    
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
    """Run scaling diagnostics including SVD analysis and Jacobian quality checks."""
    if report_scaling:
        print("\n" + "="*80)
        print("SCALING FACTORS REPORT")
        print("="*80)
        
        report_buffer = StringIO()
        print("\n>>> FLOWSHEET LEVEL SCALING FACTORS <<<")
        report_scaling_factors(m.fs, ctype=pyo.Var, descend_into=True, stream=report_buffer)
        report_content = report_buffer.getvalue()
        print(report_content)
        
        print("\n" + "="*80)
        print("END OF SCALING FACTORS REPORT")
        print("="*80 + "\n")
    
    if analyze_jacobian:
        print("\n" + "="*80)
        print("SINGULAR VALUE DECOMPOSITION (SVD) ANALYSIS")
        print("="*80)
        print("\nAnalyzing the Jacobian matrix to verify scaling quality...\n")
        
        try:
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
            
            print("\n" + "-"*80)
            print("CONSTRAINT RANK ANALYSIS")
            print("-"*80)
            svd.display_rank_of_equality_constraints()
            
            print("\n" + "-"*80)
            print("VARIABLES AND CONSTRAINTS WITH SMALLEST SINGULAR VALUES")
            print("-"*80)
            svd.display_underdetermined_variables_and_constraints(singular_values=[1, 2, 3])
            
            print("\n" + "-"*80)
            print("SINGULAR VALUE SUMMARY")
            print("-"*80)
            print(f"Number of singular values computed: {len(svd.s)}")
            print(f"Smallest singular value: {svd.s[0]:.3e}")
            print(f"Largest singular value: {svd.s[-1]:.3e}")
            condition_number = svd.s[-1]/svd.s[0] if svd.s[0] > 0 else float('inf')
            print(f"Condition number (max/min): {condition_number:.3e}")
            
            print(f"\nAll {len(svd.s)} smallest singular values:")
            for i, sv in enumerate(svd.s, 1):
                print(f"  σ_{i}: {sv:.3e}")
            
            print("\n" + "-"*80)
            print("INTERPRETATION AND RECOMMENDATIONS")
            print("-"*80)
            
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
    
    if check_jacobian_quality:
        print("\n" + "="*80)
        print("JACOBIAN QUALITY DIAGNOSTICS")
        print("="*80)
        print("\nRunning DiagnosticsToolbox to identify extreme Jacobian values...\n")
        
        try:
            dt = DiagnosticsToolbox(m.fs)
            
            print("\n" + "-"*80)
            print("EXTREME JACOBIAN ENTRIES")
            print("-"*80)
            dt.display_extreme_jacobian_entries()
            
            print("\n" + "-"*80)
            print("CONSTRAINTS WITH EXTREME JACOBIAN ROWS")
            print("-"*80)
            dt.display_constraints_with_extreme_jacobians()
            
            print("\n" + "-"*80)
            print("VARIABLES WITH EXTREME JACOBIAN COLUMNS")
            print("-"*80)
            dt.display_variables_with_extreme_jacobians()
            
            print("\n" + "-"*80)
            print("VARIABLES NEAR BOUNDS")
            print("-"*80)
            dt.display_variables_near_bounds()
            
            print("\n" + "-"*80)
            print("VARIABLES WITH EXTREME VALUES")
            print("-"*80)
            dt.display_variables_with_extreme_values()
            
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
        
def build_flowsheet(stage=5):
    """Build lithium carbonate plant flowsheet.
    
    Args:
        stage: Stage of flowsheet to build
            1 - Feed, storage tank, and pump only
            2 - Stage 1 + soda ash reactor
            3 - Stage 2 + lime reactor
            4 - Stage 3 + lithium carbonate reactor
            5 - Stage 4 + dewaterers (complete flowsheet)
    """
    m = pyo.ConcreteModel()
    m.fs = FlowsheetBlock(dynamic=False)
    
    m.fs.brine_props = MCASParameterBlock(
        solute_list=["Na", "K", "Mg", "Li", "Ca", "Cl", "SO4", "B", "H", "OH", "HCO3", "CO3"],
        charge={"Na": 1, "K": 1, "Mg": 2, "Li": 1, "Ca": 2, "Cl": -1, "SO4": -2, "B": 0, "H": 1, "OH": -1, "HCO3": -1, "CO3": -2},
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
            "OH": 17.008e-3,
            "HCO3": 61.0168e-3,
            "CO3": 60.0092e-3,
        },
        material_flow_basis=MaterialFlowBasis.molar,
    )
    
    m.fs.brine_feed = Feed(property_package=m.fs.brine_props)
    m.db = Database()
    m.fs.brine_storage = StorageTank(
        property_package=m.fs.brine_props,
        database=m.db,
    )
    m.fs.brine_pump = Pump(
        property_package=m.fs.brine_props,
    )
    
    if stage >= 2:
        # Soda ash reactor: precipitates MgCO3 and CaCO3
        soda_ash_reagents = {
            "Na2CO3": {
                "mw": 105.99 * pyunits.g / pyunits.mol,
                "dissolution_stoichiometric": {"Na": 2, "HCO3": 1},
                "density_reagent": 2.52 * pyunits.kg / pyunits.L,
            },
            "H2O": {
                "mw": 18.015 * pyunits.g / pyunits.mol,
                "dissolution_stoichiometric": {"H2O": 1},
                "density_reagent": 1.0 * pyunits.kg / pyunits.L,
            },
        }
        
        soda_ash_precipitates = {
            "MgCO3": {
                "mw": 84.3139 * pyunits.g / pyunits.mol,
                "precipitation_stoichiometric": {"Mg": 1, "HCO3": 1},
            },
            "CaCO3": {
                "mw": 100.09 * pyunits.g / pyunits.mol,
                "precipitation_stoichiometric": {"Ca": 1, "HCO3": 1},
            },
        }
        
        m.fs.soda_ash_reactor = StoichiometricReactor(
            property_package=m.fs.brine_props,
            reagent=soda_ash_reagents,
            precipitate=soda_ash_precipitates,
        )
    
    if stage >= 3:
        # Lime reactor: precipitates Brucite (Mg(OH)2), Gypsum (CaSO4), and CaCO3
        lime_reagents = {
            "Ca(OH)2": {
                "mw": 74.093 * pyunits.g / pyunits.mol,
                "dissolution_stoichiometric": {"Ca": 1, "H2O": 2},
                "density_reagent": 2.24 * pyunits.kg / pyunits.L,
            },
            "H2O": {
                "mw": 18.015 * pyunits.g / pyunits.mol,
                "dissolution_stoichiometric": {"H2O": 1},
                "density_reagent": 1.0 * pyunits.kg / pyunits.L,
            },
        }
        
        lime_precipitates = {
            "Brucite": {
                "mw": 58.3197 * pyunits.g / pyunits.mol,
                "precipitation_stoichiometric": {"Mg": 1, "H2O": 2},
            },
            "Gypsum": {
                "mw": 136.14 * pyunits.g / pyunits.mol,
                "precipitation_stoichiometric": {"Ca": 1, "SO4": 1},
            },
            "CaCO3": {
                "mw": 100.09 * pyunits.g / pyunits.mol,
                "precipitation_stoichiometric": {"Ca": 1, "HCO3": 1},
            },
        }
        
        m.fs.lime_reactor = StoichiometricReactor(
            property_package=m.fs.brine_props,
            reagent=lime_reagents,
            precipitate=lime_precipitates,
        )
    
    if stage >= 4:
        # Lithium carbonate reactor: precipitates Li2CO3
        lithium_reagents = {
            "Na2CO3": {
                "mw": 105.99 * pyunits.g / pyunits.mol,
                "dissolution_stoichiometric": {"Na": 2, "HCO3": 1},
                "density_reagent": 1.2 * pyunits.kg / pyunits.L,
            },
            "H2O": {
                "mw": 18.015 * pyunits.g / pyunits.mol,
                "dissolution_stoichiometric": {"H2O": 1},
                "density_reagent": 1.0 * pyunits.kg / pyunits.L,
            },
        }
        
        lithium_precipitants = {
            "Li2CO3": {
                "mw": 73.89 * pyunits.g / pyunits.mol,
                "precipitation_stoichiometric": {"Li": 2, "HCO3": 1},
                "density_precipitate": 2.11 * pyunits.kg / pyunits.L,
            },
        }
        
        m.fs.lithium_carbonate_reactor = StoichiometricReactor(
            property_package=m.fs.brine_props,
            reagent=lithium_reagents,
            precipitate=lithium_precipitants,
        )
    
    if stage >= 5:
        # Dewatering units: separate precipitates from clarified liquid
        m.fs.soda_ash_vacuum_filter = Separator(
            property_package=m.fs.brine_props,
            outlet_list=["overflow", "underflow"],
            split_basis=SplittingType.componentFlow
        )
        
        m.fs.soda_ash_centrifuge = Separator(
            property_package=m.fs.brine_props,
            outlet_list=["overflow", "underflow"],
            split_basis=SplittingType.componentFlow
        )
        
        m.fs.lime_press_filter = Separator(
            property_package=m.fs.brine_props,
            outlet_list=["overflow", "underflow"],
            split_basis=SplittingType.componentFlow
        )
        
        m.fs.lime_centrifuge = Separator(
            property_package=m.fs.brine_props,
            outlet_list=["overflow", "underflow"],
            split_basis=SplittingType.componentFlow
        )
        
        m.fs.li_dewatering = Separator(
            property_package=m.fs.brine_props,
            outlet_list=["overflow", "underflow"],
            split_basis=SplittingType.componentFlow
        )
    
    m.fs.brine_feed_to_storage = Arc(source=m.fs.brine_feed.outlet, destination=m.fs.brine_storage.inlet)
    m.fs.storage_to_pump = Arc(source=m.fs.brine_storage.outlet, destination=m.fs.brine_pump.inlet)
    
    if hasattr(m.fs, 'soda_ash_reactor'):
        m.fs.pump_to_soda_ash = Arc(source=m.fs.brine_pump.outlet, destination=m.fs.soda_ash_reactor.inlet)
    
    if hasattr(m.fs, 'soda_ash_reactor') and hasattr(m.fs, 'lime_reactor'):
        m.fs.soda_ash_to_lime = Arc(source=m.fs.soda_ash_reactor.outlet, destination=m.fs.lime_reactor.inlet)
    
    if hasattr(m.fs, 'lime_reactor') and hasattr(m.fs, 'lithium_carbonate_reactor'):
        m.fs.lime_to_lithium = Arc(source=m.fs.lime_reactor.outlet, destination=m.fs.lithium_carbonate_reactor.inlet)
    
    if hasattr(m.fs, 'soda_ash_vacuum_filter'):
        m.fs.soda_ash_to_vacuum_filter = Arc(source=m.fs.soda_ash_reactor.waste, destination=m.fs.soda_ash_vacuum_filter.inlet)
        m.fs.soda_ash_vacuum_filter_to_centrifuge = Arc(source=m.fs.soda_ash_vacuum_filter.underflow, destination=m.fs.soda_ash_centrifuge.inlet)
        m.fs.lime_to_lime_press_filter = Arc(source=m.fs.lime_reactor.waste, destination=m.fs.lime_press_filter.inlet)
        m.fs.lime_press_filter_to_lime_centrifuge = Arc(source=m.fs.lime_press_filter.underflow, destination=m.fs.lime_centrifuge.inlet)
        m.fs.lithium_to_dewatering = Arc(source=m.fs.lithium_carbonate_reactor.waste, destination=m.fs.li_dewatering.inlet)
    
    TransformationFactory("network.expand_arcs").apply_to(m)
    
    modify_unit_models(m)
    set_brine_feed_conditions(m)
    modify_flowsheet(m)
    fix_unit_model_variables(m)
    initialize_flowsheet(m)
    set_scaling_factors(m, stage=stage)

    run_diagnostics(m, report_scaling=True, analyze_jacobian=False, check_jacobian_quality=False)

    return m

def check_unfixed_variables(block, name="block"):
    """Check which variables are not fixed in a block (useful for debugging DOF issues)."""
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

def set_objective(m):
    """
    Set objective to maximize the flow of lithium (as waste) out of the lithium carbonate reactor.
    This unfixes the lithium removal fraction if it was fixed and sets the objective.
    """
    if hasattr(m.fs, 'lithium_carbonate_reactor'):
        li_waste_flow = m.fs.lithium_carbonate_reactor.waste_state[0].flow_mol_phase_comp["Liq", "Li"]
        m.fs.objective = pyo.Objective(expr=li_waste_flow, sense=pyo.maximize)
        print("\nObjective set: maximize lithium waste flow from lithium carbonate reactor")
    else:
        print("\nWarning: lithium_carbonate_reactor not found in flowsheet, cannot set objective")

def main():
    print("Building lithium carbonate plant flowsheet...")
    m = build_flowsheet()
    
    print("\nFlowsheet built successfully!")
    print(f"Number of variables: {len(list(m.fs.component_data_objects(pyo.Var)))}")
    print(f"Number of constraints: {len(list(m.fs.component_data_objects(pyo.Constraint)))}")
    
    set_objective(m)
    
    return m

if __name__ == "__main__":
    m = main()
