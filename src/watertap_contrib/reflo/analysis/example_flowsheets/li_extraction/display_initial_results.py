from pyomo.environ import value

def display_initial_results(m, weather_name="Station 34"):
    print("\n" + "="*50)
    print(f"EVAPORATION POND RESULTS ({weather_name} Weather Data)")
    print("="*50)
    
    # Feed conditions
    print(f"\nFEED CONDITIONS:")
    print(f"  Water flow rate: {value(m.fs.feed.properties[0].flow_mass_phase_comp['Liq', 'H2O']):.2f} kg/s")
    print(f"  TDS flow rate: {value(m.fs.feed.properties[0].flow_mass_phase_comp['Liq', 'TDS']):.2f} kg/s")
    print(f"  Li+ flow rate: {value(m.fs.feed.properties[0].flow_mass_phase_comp['Liq', 'Li+']):.2f} kg/s")
    print(f"  Liquid temperature: {value(m.fs.feed.properties[0].temperature['Liq']):.1f} K")
    print(f"  Vapor temperature: {value(m.fs.feed.properties[0].temperature['Vap']):.1f} K")
    print(f"  Pressure: {value(m.fs.feed.properties[0].pressure):.0f} Pa")
    
    # Evaporation pond results
    print(f"\nEVAPORATION POND RESULTS:")
    print(f"  Total evaporative area required: {value(m.fs.pond.total_evaporative_area_required):.1f} m²")
    print(f"  Number of evaporation ponds: {value(m.fs.pond.number_evaporation_ponds):.0f}")
    print(f"  Evaporative area per pond: {value(m.fs.pond.evaporative_area_per_pond):.1f} m²")
    print(f"  Evaporation pond area: {value(m.fs.pond.evaporation_pond_area):.1f} m²")
    print(f"  Solids precipitation rate: {value(m.fs.pond.solids_precipitation_rate):.4f} ft/yr")
    print(f"  Mass flow of precipitate: {value(m.fs.pond.mass_flow_precipitate):.0f} kg/yr")
    print(f"  Water activity: {value(m.fs.pond.water_activity):.4f}")
    print(f"  Area correction factor: {value(m.fs.pond.area_correction_factor):.4f}")
    print(f"  Average mass flux of water vapor: {value(m.fs.pond.mass_flux_water_vapor_average):.2e} kg/(m²·s)")
    
    # Partial evaporation results
    print(f"\nPARTIAL EVAPORATION RESULTS:")
    print(f"  Fraction of water evaporated: {value(m.fs.fraction_evaporated):.8f}")
    print(f"  Water evaporated: {value(m.fs.water_evaporated):.2f} kg/s")
    print(f"  Water outflow: {value(m.fs.water_outflow):.2f} kg/s")
    print(f"  TDS outflow: {value(m.fs.tds_outflow):.2f} kg/s")
    if hasattr(m.fs, 'li_outflow'):
        print(f"  Li+ outflow: {value(m.fs.li_outflow):.2f} kg/s")
    else:
        print(f"  Li+ outflow: {value(m.fs.target_li_concentration * (m.fs.water_outflow + m.fs.tds_outflow) / 1000):.2f} kg/s")
    print(f"  TDS concentration in outflow: {value(m.fs.tds_concentration_outflow):.2f} kg/m³")
    if hasattr(m.fs, 'li_concentration_outflow'):
        print(f"  Li+ concentration in outflow: {value(m.fs.li_concentration_outflow):.2f} kg/m³")
    print(f"  Li+ mass fraction in outflow: {value(m.fs.li_outflow / (m.fs.concentrated_brine_outflow) * 100):.2f}%")
    print(f"  Concentrated brine outflow: {value(m.fs.concentrated_brine_outflow):.2f} kg/s")
    
    # Target Li+ concentration
    print(f"\nTARGET CONCENTRATION:")
    print(f"  Target Li+ concentration: {value(m.fs.target_li_concentration):.3f} g/kg")
    print(f"  Achieved Li+ concentration: {value(m.fs.li_outflow / (m.fs.water_outflow + m.fs.tds_outflow) * 1000):.3f} g/kg") 