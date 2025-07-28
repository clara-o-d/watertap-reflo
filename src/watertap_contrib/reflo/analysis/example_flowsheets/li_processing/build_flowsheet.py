import pyomo.environ as pyo
from pyomo.core import ConcreteModel, TransformationFactory
from idaes.core import FlowsheetBlock
from pyomo.network import Arc
from idaes.core.util.initialization import propagate_state
from watertap.property_models.multicomp_aq_sol_prop_pack import MCASParameterBlock, DensityCalculation as MCASDensityCalculation
from idaes.models.unit_models import Feed, Product
from watertap.unit_models.pressure_changer import Pump
from watertap_contrib.reflo.unit_models import ChemicalSoftening
# DewateringUnit removed - using StorageTankZO for simplicity
from watertap.unit_models.zero_order import StorageTankZO, ClarifierZO
from watertap.unit_models.boron_removal import BoronRemoval
from watertap.core.util.initialization import assert_degrees_of_freedom
import idaes.core.util.scaling as iscale
from watertap_contrib.reflo.analysis.example_flowsheets.li_processing.define_additional_constraints import define_additional_constraints
from watertap_contrib.reflo.analysis.example_flowsheets.li_processing.reaction_packages import (
    get_enhanced_property_config
)
from idaes.core.util.model_statistics import degrees_of_freedom
from pyomo.environ import units as pyunits


def build_flowsheet():
    m = ConcreteModel()
    m.fs = FlowsheetBlock(dynamic=False)

    # Get enhanced property configuration with additional components for reactions
    enhanced_props = get_enhanced_property_config()
    
    m.fs.properties = MCASParameterBlock(
        solute_list=enhanced_props["solute_list"],
        mw_data=enhanced_props["mw_data"],
        density_calculation=MCASDensityCalculation.constant,
    )
    
    # Feed and storage
    m.fs.feed = Feed(property_package=m.fs.properties)
    m.fs.storage = StorageTankZO(property_package=m.fs.properties)

    # Boron removal section
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
    
    # Chemical softening
    m.fs.softening = ChemicalSoftening(property_package=m.fs.properties)
    
    # Li2CO3 precipitation section with constraint-based stoichiometry
    m.fs.carbonation = StorageTankZO(property_package=m.fs.properties)  # Reactor with constraints
    m.fs.carbonation_sep = ClarifierZO(property_package=m.fs.properties)
    m.fs.drying = StorageTankZO(property_package=m.fs.properties)
    
    # Li2CO3 products and waste streams
    m.fs.li2co3_product = Product(property_package=m.fs.properties)
    m.fs.solid_waste = Product(property_package=m.fs.properties)
    m.fs.liquid_waste = Product(property_package=m.fs.properties)
    
    # LiOH section with constraint-based stoichiometry
    m.fs.lioh_reactor = StorageTankZO(property_package=m.fs.properties)  # Reactor with constraints
    m.fs.lioh_clarifier = ClarifierZO(property_package=m.fs.properties)
    m.fs.lioh_filter = StorageTankZO(property_package=m.fs.properties)
    m.fs.lioh_evap = StorageTankZO(property_package=m.fs.properties)
    m.fs.lioh_centrifuge = StorageTankZO(property_package=m.fs.properties)
    m.fs.lioh_dryer = StorageTankZO(property_package=m.fs.properties)
    
    # LiOH products and waste streams
    m.fs.lioh_product = Product(property_package=m.fs.properties)
    m.fs.lioh_offspec = Product(property_package=m.fs.properties)
    m.fs.lioh_solidwaste = Product(property_package=m.fs.properties)
    m.fs.lioh_liquidwaste = Product(property_package=m.fs.properties)

    
    # Main Li2CO3 processing train
    m.fs.feed_to_storage = Arc(source=m.fs.feed.outlet, destination=m.fs.storage.inlet)
    m.fs.storage_to_boron = Arc(source=m.fs.storage.outlet, destination=m.fs.boron_removal.inlet)
    m.fs.boron_to_softening = Arc(source=m.fs.boron_removal.outlet, destination=m.fs.softening.inlet)
    m.fs.softening_to_carbonation = Arc(source=m.fs.softening.outlet, destination=m.fs.carbonation.inlet)
    m.fs.carbonation_to_sep = Arc(source=m.fs.carbonation.outlet, destination=m.fs.carbonation_sep.inlet)
    m.fs.sep_to_drying = Arc(source=m.fs.carbonation_sep.treated, destination=m.fs.drying.inlet)
    m.fs.drying_to_product = Arc(source=m.fs.drying.outlet, destination=m.fs.li2co3_product.inlet)
    m.fs.sep_to_waste = Arc(source=m.fs.carbonation_sep.byproduct, destination=m.fs.liquid_waste.inlet)
    
    # LiOH processing train
    m.fs.carbonation_to_lioh = Arc(source=m.fs.carbonation.outlet, destination=m.fs.lioh_reactor.inlet)
    m.fs.lioh_reactor_to_clarifier = Arc(source=m.fs.lioh_reactor.outlet, destination=m.fs.lioh_clarifier.inlet)
    m.fs.lioh_clarifier_to_filter = Arc(source=m.fs.lioh_clarifier.treated, destination=m.fs.lioh_filter.inlet)
    m.fs.lioh_clarifier_to_evap = Arc(source=m.fs.lioh_clarifier.byproduct, destination=m.fs.lioh_evap.inlet)
    m.fs.lioh_evap_to_centrifuge = Arc(source=m.fs.lioh_evap.outlet, destination=m.fs.lioh_centrifuge.inlet)
    m.fs.lioh_centrifuge_to_dryer = Arc(source=m.fs.lioh_centrifuge.outlet, destination=m.fs.lioh_dryer.inlet)
    m.fs.lioh_dryer_to_product = Arc(source=m.fs.lioh_dryer.outlet, destination=m.fs.lioh_product.inlet)
    
    TransformationFactory("network.expand_arcs").apply_to(m)

    define_additional_constraints(m)

    m.fs.feed.properties[0].pressure.fix(101325 * pyunits.Pa)
    m.fs.feed.properties[0].temperature.fix(298 * pyunits.K)
    
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "H2O"].set_value(10.0)   # Solvent
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "li+"].set_value(0.1)    # Main valuable component
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "Na+"].set_value(0.2)    # For electroneutrality
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "Cl-"].set_value(0.3)    # Major anion
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "CO3-2"].set_value(0.01) # For Li2CO3 reaction
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "Ca_2+"].set_value(0.02) # For LiOH reaction
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "boron"].set_value(0.01) # For boron removal
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "tds"].set_value(0.5)    # Total dissolved solids
    
    print(f"DOF after setting feed: {degrees_of_freedom(m)}")

    define_additional_constraints(m)
    print(f"DOF after define_additional_constraints: {degrees_of_freedom(m)}")

    m.fs.properties.set_default_scaling("flow_mass_phase_comp", 1e-3, index=("Liq", "H2O"))
    m.fs.properties.set_default_scaling("flow_mass_phase_comp", 1e-1, index=("Liq", "li+"))
    m.fs.properties.set_default_scaling("flow_mass_phase_comp", 1e-1, index=("Liq", "boron"))
    m.fs.properties.set_default_scaling("flow_mass_phase_comp", 1e-1, index=("Liq", "borate"))
    m.fs.properties.set_default_scaling("flow_mass_phase_comp", 1e-1, index=("Liq", "Ca_2+"))
    m.fs.properties.set_default_scaling("flow_mass_phase_comp", 1e-1, index=("Liq", "Mg_2+"))
    m.fs.properties.set_default_scaling("flow_mass_phase_comp", 1e-1, index=("Liq", "Na+"))
    m.fs.properties.set_default_scaling("flow_mass_phase_comp", 1e-1, index=("Liq", "Cl-"))
    m.fs.properties.set_default_scaling("flow_mass_phase_comp", 1e-1, index=("Liq", "CO3-2"))
    m.fs.properties.set_default_scaling("flow_mass_phase_comp", 1e-1, index=("Liq", "HCO3-"))
    m.fs.properties.set_default_scaling("flow_mass_phase_comp", 1e-1, index=("Liq", "tss"))
    m.fs.properties.set_default_scaling("flow_mass_phase_comp", 1e-1, index=("Liq", "tds"))
    m.fs.properties.set_default_scaling("flow_mass_phase_comp", 1e-1, index=("Liq", "Alkalinity_2-"))
    m.fs.properties.set_default_scaling("flow_mass_phase_comp", 1e-1, index=("Liq", "Li2CO3"))
    m.fs.properties.set_default_scaling("flow_mass_phase_comp", 1e-1, index=("Liq", "OH-"))
    m.fs.properties.set_default_scaling("flow_mass_phase_comp", 1e-1, index=("Liq", "H+"))
    m.fs.properties.set_default_scaling("flow_mass_phase_comp", 1e-1, index=("Liq", "CaCO3"))
    m.fs.properties.set_default_scaling("temperature", 1e-2)
    m.fs.properties.set_default_scaling("pressure", 1e-5)
    m.fs.properties.set_default_scaling("mass_frac_phase_comp", 1e0)
    
    # Unit model scaling
    for unit in [m.fs.feed, m.fs.storage, m.fs.boron_removal, m.fs.softening, m.fs.carbonation,
                 m.fs.carbonation_sep, m.fs.drying, m.fs.lioh_reactor, m.fs.lioh_clarifier,
                 m.fs.lioh_filter, m.fs.lioh_evap, m.fs.lioh_centrifuge, m.fs.lioh_dryer]:
        if hasattr(unit, 'control_volume') and hasattr(unit.control_volume, 'work'):
            iscale.set_scaling_factor(unit.control_volume.work, 1e-6)

    iscale.calculate_scaling_factors(m)

    
    print("Initializing complete lithium processing flowsheet...")
    
    # Feed
    m.fs.feed.initialize()
    m.fs.feed.report()

    # Storage
    propagate_state(m.fs.feed_to_storage)
    m.fs.storage.initialize()
    m.fs.storage.report()

    # Boron removal
    propagate_state(m.fs.storage_to_boron)
    m.fs.boron_removal.initialize()
    m.fs.boron_removal.report()

    # Chemical softening
    propagate_state(m.fs.boron_to_softening)
    m.fs.softening.initialize()
    m.fs.softening.report()

    # Li2CO3 precipitation with constraint-based stoichiometry
    propagate_state(m.fs.softening_to_carbonation)
    m.fs.carbonation.initialize()
    m.fs.carbonation.report()

    # Li2CO3 separation
    propagate_state(m.fs.carbonation_to_sep)
    m.fs.carbonation_sep.initialize()
    m.fs.carbonation_sep.report()

    # Drying and Li2CO3 product
    propagate_state(m.fs.sep_to_drying)
    m.fs.drying.initialize()
    m.fs.drying.report()

    propagate_state(m.fs.drying_to_product)
    m.fs.li2co3_product.initialize()
    m.fs.li2co3_product.report()

    # Waste streams
    propagate_state(m.fs.sep_to_waste)
    m.fs.liquid_waste.initialize()
    m.fs.liquid_waste.report()

    # Initialize unconnected product units
    m.fs.solid_waste.initialize()
    m.fs.solid_waste.report()

    # LiOH section with constraint-based stoichiometry
    propagate_state(m.fs.carbonation_to_lioh)
    m.fs.lioh_reactor.initialize()
    m.fs.lioh_reactor.report()

    propagate_state(m.fs.lioh_reactor_to_clarifier)
    m.fs.lioh_clarifier.initialize()
    m.fs.lioh_clarifier.report()

    propagate_state(m.fs.lioh_clarifier_to_filter)
    m.fs.lioh_filter.initialize()
    m.fs.lioh_filter.report()

    propagate_state(m.fs.lioh_clarifier_to_evap)
    m.fs.lioh_evap.initialize()
    m.fs.lioh_evap.report()

    propagate_state(m.fs.lioh_evap_to_centrifuge)
    m.fs.lioh_centrifuge.initialize()
    m.fs.lioh_centrifuge.report()

    propagate_state(m.fs.lioh_centrifuge_to_dryer)
    m.fs.lioh_dryer.initialize()
    m.fs.lioh_dryer.report()

    # LiOH products and waste
    propagate_state(m.fs.lioh_dryer_to_product)
    m.fs.lioh_product.initialize()
    m.fs.lioh_product.report()

    # Initialize unconnected waste products
    m.fs.lioh_offspec.initialize()
    m.fs.lioh_solidwaste.initialize()
    m.fs.lioh_liquidwaste.initialize()
    m.fs.lioh_offspec.report()
    m.fs.lioh_solidwaste.report()
    m.fs.lioh_liquidwaste.report()

    
    print(f"DOF after build_flowsheet: {degrees_of_freedom(m)}")
    assert_degrees_of_freedom(m, 0)
    
    return m 