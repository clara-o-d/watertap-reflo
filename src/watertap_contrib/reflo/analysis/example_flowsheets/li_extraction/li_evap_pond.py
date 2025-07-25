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


def build_flowsheet():

    m = ConcreteModel()
    m.fs = FlowsheetBlock(dynamic=False)

    # AirWaterEq property package uses uppercase 'TDS' for compatibility with EvaporationPond
    props = {
        "non_volatile_solute_list": ["TDS", "li+"],
        "mw_data": {"TDS": 31.4038218e-3, "li+": 6.94e-3},
        "density_calculation": DensityCalculation.calculated,
    }
    m.fs.prop_air = AirWaterEq(**props)
    m.fs.prop_mcas = MCASParameterBlock(
        solute_list=["TDS", "li+"],
        mw_data={"TDS": 31.4038218e-3, "li+": 6.94e-3},
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
        weather_data_path="evaporation_pond_test_data.csv",
        weather_data_column_dict=weather_data_column_dict,
        dike_height=8,  # 4, 8, or 12
        add_enhancement=True,
    )

    m.fs.pump_to_pond_tb = Translator(
        inlet_property_package=m.fs.prop_mcas,
        outlet_property_package=m.fs.prop_air,
    )
    @m.fs.pump_to_pond_tb.Constraint(['H2O', 'TDS', 'li+'])
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

    @m.fs.pump_to_pond_tb.Constraint(['Liq', 'Vap'])
    def eq_temp_equilibrium(b, p):
        return b.properties_in[0].temperature == b.properties_out[0].temperature[p]


    m.fs.feed_to_pump = Arc(source=m.fs.feed.outlet, destination=m.fs.pump.inlet)
    m.fs.pump_to_tb = Arc(source=m.fs.pump.outlet, destination=m.fs.pump_to_pond_tb.inlet)
    m.fs.tb_to_pond = Arc(source=m.fs.pump_to_pond_tb.outlet, destination=m.fs.pond.inlet)
    TransformationFactory("network.expand_arcs").apply_to(m)

    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "TDS"] = 1
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "li+"] = 0.1
    m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "H2O"] = 50
    m.fs.feed.properties[0].temperature = 300  # K
    m.fs.feed.properties[0].pressure = 101325  # Pa

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
    return m


if __name__ == "__main__":
    m1 = build_flowsheet()