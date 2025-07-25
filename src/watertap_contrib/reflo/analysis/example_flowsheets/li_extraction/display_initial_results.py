from pyomo.environ import value

def display_initial_results(m, weather_name="Unknown"):
    print("\n" + "="*50)
    print(f"EVAPORATION POND RESULTS ({weather_name} Weather Data)")
    print("="*50)
    print(f"Total evaporative area required: {value(m.fs.pond.total_evaporative_area_required):.1f} m²")
    print(f"Number of evaporation ponds: {value(m.fs.pond.number_evaporation_ponds):.0f}")
    print(f"Fraction of water evaporated: {value(m.fs.fraction_evaporated):.3f}")
    print(f"Water outflow: {value(m.fs.water_outflow):.2f} kg/s")
    print(f"Li+ outflow concentration: {value(m.fs.li_concentration_outflow):.2f} kg/m³ ({value(m.fs.li_concentration_outflow * 100 / value(m.fs.rho)):.2f}%)") 