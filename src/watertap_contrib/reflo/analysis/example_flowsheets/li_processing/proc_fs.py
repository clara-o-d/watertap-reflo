import pyomo.environ as pyo
from pyomo.environ import ConcreteModel, units as pyunits, value
from idaes.core import FlowsheetBlock
from pyomo.network import Arc
from pyomo.environ import TransformationFactory
from watertap.property_models.multicomp_aq_sol_prop_pack import MCASParameterBlock, DensityCalculation as MCASDensityCalculation
from idaes.models.unit_models import Feed, Product, Mixer
from idaes.models.unit_models.mixer import MixingType
from watertap.unit_models.pressure_changer import Pump
from watertap_contrib.reflo.unit_models import EvaporationPond, ChemicalSoftening
from watertap.unit_models.stoichiometric_reactor import StoichiometricReactor
from watertap.unit_models.clarifier import Clarifier
from watertap.unit_models.dewatering import DewateringUnit
from watertap.core.util.initialization import assert_degrees_of_freedom
from pyomo.environ import assert_optimal_termination
from watertap.unit_models.zero_order import StorageTankZO
from watertap.unit_models.zero_order import ClarifierZO
from idaes.models.properties.modular_properties.base.generic_reaction import GenericReactionParameterBlock
from idaes.core.base.components import Cation, Anion, Solvent
from idaes.models.properties.modular_properties.pure.ConstantProperties import Constant
from idaes.models.properties.modular_properties.state_definitions import FTPx
from idaes.models.properties.modular_properties.eos.ideal import Ideal
from idaes.core import AqueousPhase
from idaes.models.properties.modular_properties.base.generic_property import StateIndex
import idaes.core.util.scaling as iscale
from watertap.unit_models.boron_removal import BoronRemoval


def main():
    m = build()
    set_operating_conditions(m)
    assert_degrees_of_freedom(m, 0)
    iscale.calculate_scaling_factors(m)
    initialize_system(m)

    results = solve_flowsheet(m)
    assert_optimal_termination(results)
    print_results(m)

    add_costing(m)
    process_costing(m)
    
    results = solve_flowsheet(m)
    assert_optimal_termination(results)
    print_results(m)

def build():
    # Property package
    m = ConcreteModel()
    m.fs = FlowsheetBlock(dynamic=False)
    m.fs.properties = MCASParameterBlock(
        solute_list=["li+", "boron", "borate", "Ca_2+", "Mg_2+", "Na+", "Cl-", "CO3-2", "HCO3-", "tss", "tds", "Alkalinity_2-", "Li2CO3"],
        mw_data={
            "li+": 6.94e-3,
            "boron": 10.81e-3,
            "borate": 61.83e-3,  # MW for B(OH)4-
            "Ca_2+": 40.08e-3,
            "Mg_2+": 24.31e-3,
            "Na+": 22.99e-3,
            "Cl-": 35.45e-3,
            "CO3-2": 60.01e-3,
            "HCO3-": 61.02e-3,
            "tss": 1.0,
            "tds": 31.4e-3,
            "Alkalinity_2-": 61.02e-3,  # Placeholder MW
            "Li2CO3": 73.89e-3,
        },
        density_calculation=MCASDensityCalculation.constant,
    )
    # Main process units
    m.fs.feed = Feed(property_package=m.fs.properties)
    m.fs.storage = StorageTankZO(property_package=m.fs.properties)
    # Boron removal unit (replace Mixer + Clarifier)
    chem_dict = {
        'boron_name': 'boron',
        'borate_name': 'borate',
        'caustic_additive': {
            'additive_name': 'NaOH',
            'cation_name': 'Na+',
            'mw_additive': (39.997, pyunits.g/pyunits.mol),
            'moles_cation_per_additive': 1,
        }
    }
    m.fs.boron_removal = BoronRemoval(property_package=m.fs.properties, chemical_mapping_data=chem_dict)
    m.fs.softening = ChemicalSoftening(property_package=m.fs.properties)
    # StoichiometricReactor for Li2CO3 precipitation
    precipitants = {
        "Li2CO3": {
            "mw": 73.89 * pyunits.g / pyunits.mol,
            "precipitation_stoichiometric": {"li+": 2, "CO3-2": 1},
        }
    }
    m.fs.carbonation = StoichiometricReactor(property_package=m.fs.properties, precipitants=precipitants)
    m.fs.carbonation_sep = ClarifierZO(property_package=m.fs.properties)
    m.fs.drying = DewateringUnit(property_package=m.fs.properties)
    m.fs.li2co3_product = Product(property_package=m.fs.properties)
    m.fs.solid_waste = Product(property_package=m.fs.properties)
    m.fs.liquid_waste = Product(property_package=m.fs.properties)
    # Connectivity
    m.fs.feed_to_storage = Arc(source=m.fs.feed.outlet, destination=m.fs.storage.inlet)
    m.fs.storage_to_boron = Arc(source=m.fs.storage.outlet, destination=m.fs.boron_removal.inlet)
    m.fs.boron_to_softening = Arc(source=m.fs.boron_removal.outlet, destination=m.fs.softening.inlet)
    m.fs.softening_to_carbonation = Arc(source=m.fs.softening.outlet, destination=m.fs.carbonation.inlet)
    m.fs.carbonation_to_sep = Arc(source=m.fs.carbonation.outlet, destination=m.fs.carbonation_sep.inlet)
    m.fs.sep_to_drying = Arc(source=m.fs.carbonation_sep.li2co3_slurry, destination=m.fs.drying.inlet)
    m.fs.drying_to_product = Arc(source=m.fs.drying.overflow, destination=m.fs.li2co3_product.inlet)
    m.fs.drying_to_solidwaste = Arc(source=m.fs.drying.underflow, destination=m.fs.solid_waste.inlet)
    m.fs.carbonation_sep_to_liquidwaste = Arc(source=m.fs.carbonation_sep.mother_liquor, destination=m.fs.liquid_waste.inlet)
    # LiOH section
    m.fs.lioh_reactor = StoichiometricReactor(property_package=m.fs.properties)
    m.fs.lioh_clarifier = ClarifierZO(property_package=m.fs.properties)
    m.fs.lioh_filter = DewateringUnit(property_package=m.fs.properties)
    m.fs.lioh_evap = StorageTankZO(property_package=m.fs.properties)  # Use storage for buffer/hold, not evaporation
    m.fs.lioh_centrifuge = DewateringUnit(property_package=m.fs.properties)
    m.fs.lioh_dryer = DewateringUnit(property_package=m.fs.properties)
    m.fs.lioh_product = Product(property_package=m.fs.properties)
    m.fs.lioh_offspec = Product(property_package=m.fs.properties)
    m.fs.lioh_solidwaste = Product(property_package=m.fs.properties)
    m.fs.lioh_liquidwaste = Product(property_package=m.fs.properties)
    # LiOH section connectivity
    m.fs.li2co3_to_lioh = Arc(source=m.fs.li2co3_product.outlet, destination=m.fs.lioh_reactor.inlet)
    m.fs.lioh_reactor_to_clarifier = Arc(source=m.fs.lioh_reactor.outlet, destination=m.fs.lioh_clarifier.inlet)
    m.fs.lioh_clarifier_to_filter = Arc(source=m.fs.lioh_clarifier.caco3_slurry, destination=m.fs.lioh_filter.inlet)
    m.fs.lioh_clarifier_to_evap = Arc(source=m.fs.lioh_clarifier.li_oh_sol, destination=m.fs.lioh_evap.inlet)
    m.fs.lioh_evap_to_centrifuge = Arc(source=m.fs.lioh_evap.outlet, destination=m.fs.lioh_centrifuge.inlet)
    m.fs.lioh_centrifuge_to_dryer = Arc(source=m.fs.lioh_centrifuge.overflow, destination=m.fs.lioh_dryer.inlet)
    m.fs.lioh_dryer_to_product = Arc(source=m.fs.lioh_dryer.overflow, destination=m.fs.lioh_product.inlet)
    m.fs.lioh_dryer_to_offspec = Arc(source=m.fs.lioh_dryer.underflow, destination=m.fs.lioh_offspec.inlet)
    m.fs.lioh_filter_to_solidwaste = Arc(source=m.fs.lioh_filter.underflow, destination=m.fs.lioh_solidwaste.inlet)
    m.fs.lioh_evap_to_liquidwaste = Arc(source=m.fs.lioh_evap.outlet, destination=m.fs.lioh_liquidwaste.inlet)
    TransformationFactory("network.expand_arcs").apply_to(m)
    return m

def set_operating_conditions(m):
    # Feed conditions (placeholders)
    m.fs.feed.properties[0].pressure.fix(101325 * pyunits.Pa)
    m.fs.feed.properties[0].temperature.fix(298 * pyunits.K)
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "H2O"].fix(10 * pyunits.kg / pyunits.s)
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "li+"].fix(0.1 * pyunits.kg / pyunits.s)
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "boron"].fix(0.01 * pyunits.kg / pyunits.s)
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "Ca_2+"].fix(0.02 * pyunits.kg / pyunits.s)
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "Mg_2+"].fix(0.02 * pyunits.kg / pyunits.s)
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "Na+"].fix(0.2 * pyunits.kg / pyunits.s)
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "Cl-"].fix(0.3 * pyunits.kg / pyunits.s)
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "CO3-2"].fix(0.01 * pyunits.kg / pyunits.s)
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "HCO3-"].fix(0.01 * pyunits.kg / pyunits.s)
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "tss"].fix(0.0 * pyunits.kg / pyunits.s)
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "tds"].fix(0.5 * pyunits.kg / pyunits.s)
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "Alkalinity_2-"].fix(0.01 * pyunits.kg / pyunits.s)

def initialize_system(m):
    # Initialize all major units
    for unit in [
        m.fs.storage, m.fs.boron_removal, m.fs.softening, m.fs.carbonation,
        m.fs.carbonation_sep, m.fs.drying, m.fs.li2co3_product,
        m.fs.solid_waste, m.fs.liquid_waste, m.fs.lioh_reactor, m.fs.lioh_clarifier,
        m.fs.lioh_filter, m.fs.lioh_evap, m.fs.lioh_centrifuge, m.fs.lioh_dryer,
        m.fs.lioh_product, m.fs.lioh_offspec, m.fs.lioh_solidwaste, m.fs.lioh_liquidwaste
    ]:
        if hasattr(unit, "initialize"):
            try:
                unit.initialize()
            except Exception:
                pass

def solve_flowsheet(m, solver=None):
    # Solve the flowsheet
    if solver is None:
        from watertap.core.solvers import get_solver
        solver = get_solver()
    results = solver.solve(m, tee=True)
    return results

def add_costing(m):
    # Attach costing blocks to all major units
    from idaes.core import UnitModelCostingBlock
    from watertap_contrib.reflo.costing.watertap_reflo_costing_package import REFLOCosting
    m.fs.costing = REFLOCosting()
    for unit in [
        m.fs.storage, m.fs.boron_removal, m.fs.softening, m.fs.carbonation,
        m.fs.carbonation_sep, m.fs.drying, m.fs.lioh_reactor, m.fs.lioh_clarifier,
        m.fs.lioh_filter, m.fs.lioh_evap, m.fs.lioh_centrifuge, m.fs.lioh_dryer
    ]:
        if hasattr(unit, "costing"):
            continue
        try:
            unit.costing = UnitModelCostingBlock(flowsheet_costing_block=m.fs.costing)
        except Exception:
            pass
    m.fs.costing.plant_lifetime.fix(20)
    m.fs.costing.wacc.fix(0.07)
    m.fs.costing.electricity_cost.fix(0.16)
    m.fs.costing.electrical_carbon_intensity.fix(0.229)
    m.fs.costing.utilization_factor.fix(0.98)
    m.fs.costing.maintenance_labor_chemical_factor.fix(0.01)

def process_costing(m):
    # Molar masses and mass flows
    M_Li = 6.94e-3
    M_Li2CO3 = 73.89e-3
    M_LiOH_H2O = 41.96e-3
    li_mass_flow = m.fs.li2co3_product.properties[0].flow_mass_phase_comp["Liq", "li+"]
    li2co3_mass_flow = li_mass_flow * (M_Li2CO3 / (2 * M_Li))
    lioh_mass_flow = li_mass_flow * (M_LiOH_H2O / M_Li)
    # Volumetric LCOLi (for reference)
    m.fs.density_concentrated_brine = pyo.Param(
        initialize=1323,  # placeholder value, kg/m^3
        mutable=True,
        units=pyunits.kg / pyunits.m**3,
        doc="Density of concentrated brine for Li+ volume calculation"
    )
    vol_flow_li = li_mass_flow / m.fs.density_concentrated_brine  # m³/s
    if hasattr(m.fs.costing, "add_LCOW"):
        m.fs.costing.add_LCOW(vol_flow_li, name="LCOLi")
    # Mass-based LCOLi for Li2CO3
    m.fs.costing.LCOLi2CO3 = pyo.Var(
        initialize=1000,
        units=m.fs.costing.base_currency / pyunits.t,
        bounds=(0, None),
        doc="Levelized cost of lithium carbonate by mass ($/t)"
    )
    m.fs.costing.LCOLi2CO3_constraint = pyo.Constraint(
        expr=m.fs.costing.LCOLi2CO3 == m.fs.costing.LCOLi / li2co3_mass_flow * pyunits.convert(1 * pyunits.s, to_units=pyunits.year) / 1000
    )
    # Mass-based LCOLi for LiOH·H2O
    m.fs.costing.LCOLiOH_H2O = pyo.Var(
        initialize=1000,
        units=m.fs.costing.base_currency / pyunits.t,
        bounds=(0, None),
        doc="Levelized cost of lithium hydroxide monohydrate by mass ($/t)"
    )
    m.fs.costing.LCOLiOH_H2O_constraint = pyo.Constraint(
        expr=m.fs.costing.LCOLiOH_H2O == m.fs.costing.LCOLi / lioh_mass_flow * pyunits.convert(1 * pyunits.s, to_units=pyunits.year) / 1000
    )

def print_results(m):
    # Print main product and waste flows
    print("\n=== PQC Lithium Flowsheet Results ===")
    print(f"Li2CO3 product flow: {value(m.fs.li2co3_product.properties[0].flow_mass_phase_comp['Liq', 'li+']):.3f} kg/s")
    print(f"Solid waste flow: {value(m.fs.solid_waste.properties[0].flow_mass_phase_comp['Liq', 'tss']):.3f} kg/s")
    print(f"Liquid waste flow: {value(m.fs.liquid_waste.properties[0].flow_mass_phase_comp['Liq', 'tds']):.3f} kg/s")
    print("(Add more detailed reporting as needed)")
    # Print costing summary
    if hasattr(m.fs, "costing"):
        print("\n--- Costing ---")
        if hasattr(m.fs.costing, "aggregate_capital_cost"):
            print(f"Aggregate capital cost: {value(m.fs.costing.aggregate_capital_cost):.2f}")
        if hasattr(m.fs.costing, "aggregate_fixed_operating_cost"):
            print(f"Aggregate fixed OPEX: {value(m.fs.costing.aggregate_fixed_operating_cost):.2f}/year")
        if hasattr(m.fs.costing, "LCOLi2CO3"):
            print(f"Levelized cost of Li2CO3: {value(m.fs.costing.LCOLi2CO3):.2f} $/t")
        if hasattr(m.fs.costing, "LCOLiOH_H2O"):
            print(f"Levelized cost of LiOH·H2O: {value(m.fs.costing.LCOLiOH_H2O):.2f} $/t")
        if hasattr(m.fs.costing, "LCOLi"):
            print(f"Levelized cost of Li (volumetric): {value(m.fs.costing.LCOLi):.2f} $/m³")

if __name__ == "__main__":
    main()
