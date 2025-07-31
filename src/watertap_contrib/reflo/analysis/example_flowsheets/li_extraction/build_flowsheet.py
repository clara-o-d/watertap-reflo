from pyomo.core import ConcreteModel, TransformationFactory
from idaes.core import FlowsheetBlock
from pyomo.network import Arc
from idaes.core.util.initialization import propagate_state
from watertap_contrib.reflo.property_models import AirWaterEq, DensityCalculation
from idaes.models.unit_models import Feed
from watertap_contrib.reflo.unit_models.evaporation_pond import EvaporationPond
from watertap.core.util.initialization import assert_degrees_of_freedom
import idaes.core.util.scaling as iscale
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.define_additional_constraints import define_additional_constraints
from idaes.core.util.model_statistics import degrees_of_freedom
from pyomo.environ import units as pyunits
from pyomo.environ import value
from pyomo.environ import Constraint

def build_flowsheet():
    m = ConcreteModel()
    m.fs = FlowsheetBlock(dynamic=False)

    # AirWaterEq property package uses uppercase 'TDS' for compatibility with EvaporationPond
    props = {
        "non_volatile_solute_list": ["TDS", "Li+"],
        "mw_data": {"TDS": 31.4038218e-3, "Li+": 6.94e-3},
        "density_calculation": DensityCalculation.calculated,
    }
    m.fs.prop_air = AirWaterEq(**props)
    m.fs.feed = Feed(property_package=m.fs.prop_air)

    weather_data_column_dict = {
        "pressure": "Pressure",
        "temperature": "Temperature",
        "shortwave_radiation": "GHI",
        "relative_humidity": "Relative Humidity",
    }

    m.fs.pond = EvaporationPond(
        property_package=m.fs.prop_air,
        weather_data_path="watertap_contrib/reflo/analysis/example_flowsheets/li_extraction/weather/station34_processed_weather.csv",
        weather_data_column_dict=weather_data_column_dict,
        dike_height=8,  # 4, 8, or 12
        add_enhancement=True,
    )

    m.fs.feed_to_pond = Arc(source=m.fs.feed.outlet, destination=m.fs.pond.inlet)
    TransformationFactory("network.expand_arcs").apply_to(m)

    # Set feed conditions
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "TDS"].fix(477)
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "Li+"].fix(2.0)
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "H2O"].fix(1290)
    m.fs.feed.properties[0].temperature.fix(300)  # K
    m.fs.feed.properties[0].pressure.fix(101325)  # Pa
    m.fs.feed.properties[0].flow_mass_phase_comp["Vap", "Air"].fix(1)
    m.fs.feed.properties[0].flow_mass_phase_comp["Vap", "H2O"].fix(0)
    print(f"DOF after setting feed: {degrees_of_freedom(m)}")

    define_additional_constraints(m)
    print(f"DOF after define_additional_constraints: {degrees_of_freedom(m)}")
    
    # Air property package scaling
    m.fs.prop_air.set_default_scaling("flow_mass_phase_comp", 1e-3, index=("Liq", "H2O"))
    m.fs.prop_air.set_default_scaling("flow_mass_phase_comp", 1e-1, index=("Liq", "TDS"))
    m.fs.prop_air.set_default_scaling("flow_mass_phase_comp", 1e-1, index=("Liq", "Li+"))
    m.fs.prop_air.set_default_scaling("flow_mass_phase_comp", 1e-3, index=("Vap", "H2O"))
    m.fs.prop_air.set_default_scaling("flow_mass_phase_comp", 1e-3, index=("Vap", "Air"))
    m.fs.prop_air.set_default_scaling("temperature", 1e-2)
    m.fs.prop_air.set_default_scaling("pressure", 1e-5)
    m.fs.prop_air.set_default_scaling("mass_frac_phase_comp", 1e0)
    
    # Unit model scaling
    for unit in [m.fs.feed, m.fs.pond]:
        if hasattr(unit, 'control_volume'):
            iscale.set_scaling_factor(unit.control_volume.work, 1e-6)
    
    iscale.calculate_scaling_factors(m)

    m.fs.feed.initialize()
    m.fs.feed.report()

    propagate_state(m.fs.feed_to_pond)
    m.fs.pond.initialize()
    m.fs.pond.report()
    print(f"DOF after build_flowsheet: {degrees_of_freedom(m)}")
    assert_degrees_of_freedom(m, 0)

    return m 