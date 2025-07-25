from pyomo.core import ConcreteModel, TransformationFactory
from idaes.core import FlowsheetBlock
from pyomo.network import Arc
from idaes.core.util.initialization import propagate_state
from watertap_contrib.reflo.property_models import AirWaterEq, DensityCalculation
from idaes.models.unit_models import Feed
from watertap.property_models.multicomp_aq_sol_prop_pack import MCASParameterBlock, DensityCalculation as MCASDensityCalculation, MaterialFlowBasis
from idaes.models.unit_models.translator import Translator
from watertap.unit_models.pressure_changer import Pump
from watertap_contrib.reflo.unit_models.evaporation_pond import EvaporationPond
from watertap.core.util.initialization import assert_degrees_of_freedom
import idaes.core.util.scaling as iscale
from watertap_contrib.reflo.analysis.example_flowsheets.li_extraction.define_additional_constraints import define_additional_constraints
from idaes.core.util.model_statistics import degrees_of_freedom

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
    m.fs.prop_mcas = MCASParameterBlock(
        solute_list=["TDS", "Li+"],
        mw_data={"TDS": 31.4038218e-3, "Li+": 6.94e-3},
        density_calculation=MCASDensityCalculation.constant,
        material_flow_basis=MaterialFlowBasis.mass,
    )
    m.fs.feed = Feed(property_package=m.fs.prop_mcas)
    m.fs.pump = Pump(property_package=m.fs.prop_mcas)

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

    m.fs.pump_to_pond_tb = Translator(
        inlet_property_package=m.fs.prop_mcas,
        outlet_property_package=m.fs.prop_air,
    )
    @m.fs.pump_to_pond_tb.Constraint(['H2O', 'TDS', 'Li+'])
    def eq_mass_flow_balance(b, j):
        return b.properties_in[0].flow_mass_phase_comp["Liq", j] == b.properties_out[0].flow_mass_phase_comp["Liq", j]

    @m.fs.pump_to_pond_tb.Constraint(['H2O', 'Air'])
    def eq_fix_vap_flow_rate(b, j):
        if j == "H2O":
            return b.properties_out[0].flow_mass_phase_comp["Vap", j] == 0
        elif j == "Air":
            return b.properties_out[0].flow_mass_phase_comp["Vap", j] == 1
        else:
            raise AttributeError('Unknown component was passed to AirWaterEq property package: {}'.format(j))

    @m.fs.pump_to_pond_tb.Constraint()
    def eq_pressure_equality(b):
        return b.properties_in[0].pressure == b.properties_out[0].pressure

    m.fs.feed_to_pump = Arc(source=m.fs.feed.outlet, destination=m.fs.pump.inlet)
    m.fs.pump_to_tb = Arc(source=m.fs.pump.outlet, destination=m.fs.pump_to_pond_tb.inlet)
    m.fs.tb_to_pond = Arc(source=m.fs.pump_to_pond_tb.outlet, destination=m.fs.pond.inlet)
    TransformationFactory("network.expand_arcs").apply_to(m)

    @m.fs.pump_to_pond_tb.Constraint(['Liq', 'Vap'])
    def eq_temp_equilibrium(b, p):
        return b.properties_in[0].temperature == b.properties_out[0].temperature[p]

    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "TDS"].fix(477)
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "Li+"].fix(2.0)
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "H2O"].fix(1290)
    m.fs.feed.properties[0].temperature.fix(300)  # K
    m.fs.feed.properties[0].pressure.fix(101325)  # Pa
    print(f"DOF after setting feed: {degrees_of_freedom(m)}")

    define_additional_constraints(m)
    print(f"DOF after define_additional_constraints: {degrees_of_freedom(m)}")
    
    # MCAS property package scaling
    m.fs.prop_mcas.set_default_scaling("flow_mass_phase_comp", 1e-3, index=("Liq", "H2O"))
    m.fs.prop_mcas.set_default_scaling("flow_mass_phase_comp", 1e-1, index=("Liq", "TDS"))
    m.fs.prop_mcas.set_default_scaling("flow_mass_phase_comp", 1e-1, index=("Liq", "Li+"))
    m.fs.prop_mcas.set_default_scaling("temperature", 1e-2)
    m.fs.prop_mcas.set_default_scaling("pressure", 1e-5)
    m.fs.prop_mcas.set_default_scaling("mass_frac_phase_comp", 1e0)
    
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
    for unit in [m.fs.feed, m.fs.pump, m.fs.pump_to_pond_tb, m.fs.pond]:
        if hasattr(unit, 'control_volume'):
            iscale.set_scaling_factor(unit.control_volume.work, 1e-6)
    
    iscale.calculate_scaling_factors(m)

    # Set initial values for translator to improve convergence
    m.fs.pump_to_pond_tb.properties_out[0].temperature["Liq"].set_value(300)
    m.fs.pump_to_pond_tb.properties_out[0].temperature["Vap"].set_value(300)
    m.fs.pump_to_pond_tb.properties_out[0].pressure.set_value(1.1 * 101325)
    
    # Set initial values for vapor flows
    m.fs.pump_to_pond_tb.properties_out[0].flow_mass_phase_comp["Vap", "H2O"].set_value(0)
    m.fs.pump_to_pond_tb.properties_out[0].flow_mass_phase_comp["Vap", "Air"].set_value(0)

    m.fs.feed.initialize()
    m.fs.feed.report()

    propagate_state(m.fs.feed_to_pump)
    m.fs.pump.efficiency_pump.fix(0.8) # 80% efficiency
    m.fs.pump.outlet.pressure[0].fix(1.1 * 101325)  # 10% higher than feed pressure
    m.fs.pump.initialize()
    m.fs.pump.report()
    propagate_state(m.fs.pump_to_tb)
    m.fs.pump_to_pond_tb.initialize()
    propagate_state(m.fs.tb_to_pond)
    m.fs.pump_to_pond_tb.report()
    m.fs.pond.initialize()
    m.fs.pond.report()
    print(f"DOF after build_flowsheet: {degrees_of_freedom(m)}")
    #assert_degrees_of_freedom(m, 0)

    return m 