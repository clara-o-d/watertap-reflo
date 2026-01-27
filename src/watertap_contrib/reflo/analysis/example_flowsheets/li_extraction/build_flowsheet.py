"""Lithium extraction flowsheet construction module.

Builds and configures a lithium extraction flowsheet using evaporation ponds.
"""

from pyomo.core import ConcreteModel, TransformationFactory
from idaes.core import FlowsheetBlock
from pyomo.network import Arc
from idaes.core.util.initialization import propagate_state
from watertap_contrib.reflo.property_models import AirWaterEq, DensityCalculation
from idaes.models.unit_models import Feed
from watertap_contrib.reflo.unit_models.evaporation_pond import EvaporationPond
from watertap.core.util.initialization import assert_degrees_of_freedom
import idaes.core.util.scaling as iscale
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.modify_process import modify_process
from idaes.core.util.model_statistics import degrees_of_freedom

def define_pond_parameters(m):
    """Set evaporation pond parameters."""
    m.fs.pond.evaporation_rate_salinity_adjustment_factor.set_value(0.75)
    m.fs.pond.evaporation_rate_enhancement_adjustment_factor.fix(1.0)
    m.fs.pond.number_evaporation_ponds.fix(300)
    m.fs.pond.evaporation_pond_depth.set_value(15)

def add_scaling(m):
    """Apply scaling factors to improve numerical stability."""
    # Air property package scaling - set scaling factors for different components and phases
    m.fs.prop_air.set_default_scaling("flow_mass_phase_comp", 1e-3, index=("Liq", "H2O"))
    m.fs.prop_air.set_default_scaling("flow_mass_phase_comp", 1e-2, index=("Liq", "TDS"))
    m.fs.prop_air.set_default_scaling("flow_mass_phase_comp", 1e0, index=("Liq", "Li+"))
    m.fs.prop_air.set_default_scaling("flow_mass_phase_comp", 1e0, index=("Vap", "H2O"))
    m.fs.prop_air.set_default_scaling("flow_mass_phase_comp", 1e0, index=("Vap", "Air"))
    m.fs.prop_air.set_default_scaling("temperature", 1e-2)
    m.fs.prop_air.set_default_scaling("pressure", 1e-5)
    m.fs.prop_air.set_default_scaling("mass_frac_phase_comp", 1e1, index=("Liq", "H2O"))
    m.fs.prop_air.set_default_scaling("mass_frac_phase_comp", 1e1, index=("Liq", "TDS"))
    m.fs.prop_air.set_default_scaling("mass_frac_phase_comp", 1e2, index=("Liq", "Li+"))
    m.fs.prop_air.set_default_scaling("mass_frac_phase_comp", 1e0, index=("Vap", "H2O"))
    m.fs.prop_air.set_default_scaling("mass_frac_phase_comp", 1e0, index=("Vap", "Air"))
    
    # Unit model scaling - apply scaling to control volume work terms
    for unit in [m.fs.feed, m.fs.pond]:
        if hasattr(unit, 'control_volume'):
            iscale.set_scaling_factor(unit.control_volume.work, 1e-6)
    
    # Weather-dependent scaling - scale radiation and pressure terms for each day
    if hasattr(m.fs.pond, 'net_radiation'):
        for d in m.fs.pond.days_of_year:
            iscale.set_scaling_factor(m.fs.pond.net_radiation[d], 1e-1)

    # Pond area and capacity scaling - scale large area and capacity variables
    if hasattr(m.fs.pond, 'total_evaporative_area_required'):
        iscale.set_scaling_factor(m.fs.pond.total_evaporative_area_required, 1e-7)
    
    # if hasattr(m.fs.pond, 'evaporative_area_per_pond'):
    #     iscale.set_scaling_factor(m.fs.pond.evaporative_area_per_pond, 1e-4)

    # if hasattr(m.fs.pond, 'evaporation_pond_area'):
    #     iscale.set_scaling_factor(m.fs.pond.evaporation_pond_area, 1e-5)

    if hasattr(m.fs.pond, 'number_evaporation_ponds'):
        iscale.set_scaling_factor(m.fs.pond.number_evaporation_ponds, 1e-2)

    if hasattr(m.fs.pond, 'solids_precipitation_rate'):
        iscale.set_scaling_factor(m.fs.pond.solids_precipitation_rate, 1e1)

    # Concentration scaling - scale mass concentration terms for numerical stability
    if hasattr(m.fs.pond.properties_in[0.0], 'conc_mass_phase_comp'):
        iscale.set_scaling_factor(m.fs.pond.properties_in[0.0].conc_mass_phase_comp['Liq', 'TDS'], 1e-2)
        iscale.set_scaling_factor(m.fs.pond.properties_in[0.0].conc_mass_phase_comp['Liq', 'Li+'], 1e0)
        iscale.set_scaling_factor(m.fs.pond.properties_in[0.0].conc_mass_phase_comp['Liq', 'H2O'], 1e-2)

    # Weather pressure scaling - scale pressure terms for each day of the year
    if hasattr(m.fs.pond.weather[0], 'pressure'):
        for d in m.fs.pond.days_of_year:
            iscale.set_scaling_factor(m.fs.pond.weather[d].pressure, 1e-3)

    if hasattr(m.fs.pond.weather[0], 'pressure_vap_sat'):
        for d in m.fs.pond.days_of_year:
            iscale.set_scaling_factor(m.fs.pond.weather[d].pressure_vap_sat['H2O'], 1e-3)

    # Calculate all scaling factors
    iscale.calculate_scaling_factors(m)
    
def build_flowsheet():
    """Build and configure the lithium extraction flowsheet.
    
    Returns:
        ConcreteModel: Configured flowsheet model
    """
    m = ConcreteModel()
    m.fs = FlowsheetBlock(dynamic=False)

    # Define property package with TDS and Li+ as non-volatile solutes
    props = {
        "non_volatile_solute_list": ["TDS", "Li+"],
        "mw_data": {"TDS": 31.4038218e-3, "Li+": 6.94e-3},
        "density_calculation": DensityCalculation.calculated,
    }
    m.fs.prop_air = AirWaterEq(**props)
    m.fs.feed = Feed(property_package=m.fs.prop_air)

    # Map weather data columns to expected names for EvaporationPond model
    weather_data_column_dict = {
        "pressure": "Pressure",
        "temperature": "Temperature",
        "shortwave_radiation": "GHI",
        "relative_humidity": "Relative Humidity",
    }

    # Create evaporation pond with weather data and enhancement
    m.fs.pond = EvaporationPond(
        property_package=m.fs.prop_air,
        weather_data_path="watertap_contrib/reflo/analysis/example_flowsheets/li_extraction/weather/station34_processed_weather.csv",
        weather_data_column_dict=weather_data_column_dict,
        dike_height=8,  # 4, 8, or 12
        add_enhancement=True,
    )

    # Connect feed to pond and expand network arcs
    m.fs.feed_to_pond = Arc(source=m.fs.feed.outlet, destination=m.fs.pond.inlet)
    TransformationFactory("network.expand_arcs").apply_to(m)

    # Set feed conditions - brine composition and operating parameters
    flow_vol = 1.280 # m^3/s
    tds_conc = 250 # kg/m^3
    li_conc = 1.3 # kg/m^3
    water_conc = 873 # kg/m^3

    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "TDS"].fix(tds_conc*flow_vol)
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "Li+"].fix(li_conc*flow_vol)
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "H2O"].fix(water_conc*flow_vol)
    m.fs.feed.properties[0].temperature.fix(300)  # K
    m.fs.feed.properties[0].pressure.fix(101325)  # Pa
    m.fs.feed.properties[0].flow_mass_phase_comp["Vap", "Air"].fix(1)
    m.fs.feed.properties[0].flow_mass_phase_comp["Vap", "H2O"].fix(0)
    print(f"DOF after setting feed: {degrees_of_freedom(m)}")

    # Apply process modifications and set pond parameters
    modify_process(m)
    define_pond_parameters(m)
    print(f"DOF after define_pond_parameters: {degrees_of_freedom(m)}")
    
    # Apply scaling for numerical stability
    add_scaling(m)

    # Initialize and report feed unit
    m.fs.feed.initialize()
    m.fs.feed.report()

    # Propagate state to pond and initialize
    propagate_state(m.fs.feed_to_pond)
    # m.fs.pond.initialize()
    # m.fs.pond.report()
    print(f"DOF after build_flowsheet: {degrees_of_freedom(m)}")
    assert_degrees_of_freedom(m, 0)

    return m 