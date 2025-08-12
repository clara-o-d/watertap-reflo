"""Display module for initial flowsheet results.

Prints comprehensive results from the lithium extraction flowsheet simulation.
"""

from pyomo.environ import value

def display_initial_results(m, weather_name="Station 34"):
    """Display comprehensive results from the lithium extraction flowsheet.
    
    Args:
        m: Pyomo model with solved flowsheet
        weather_name: Name of weather station used
    """
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
    
    # Process parameters
    print(f"\nPROCESS PARAMETERS:")
    print(f"  Solution density: {value(m.fs.rho):.0f} kg/m³")
    print(f"  Pond overdesign factor: {value(m.fs.pond_overdesign_factor):.2f}")
    print(f"  Target Li+ concentration: {value(m.fs.target_li_concentration):.1f} g/kg")
    
    # Evaporation and flow results
    print(f"\nEVAPORATION AND FLOW RESULTS:")
    print(f"  Fraction of water evaporated: {value(m.fs.fraction_evaporated):.3f}")
    print(f"  Fraction of water outflow: {value(m.fs.fraction_outflow):.3f}")
    print(f"  Water evaporated: {value(m.fs.water_evaporated):.2f} kg/s")
    print(f"  Water outflow: {value(m.fs.water_outflow):.2f} kg/s")
    print(f"  TDS outflow: {value(m.fs.tds_outflow):.2f} kg/s")
    print(f"  Li+ outflow: {value(m.fs.li_outflow):.2f} kg/s")
    print(f"  Actual Li+ concentration: {value(m.fs.li_outflow / (m.fs.concentrated_brine_outflow) * 1000):.2f} g/kg")
    print(f"  TDS concentration in outflow: {value(m.fs.tds_concentration_outflow):.2f} kg/m³")
    print(f"  Concentrated brine outflow: {value(m.fs.concentrated_brine_outflow):.2f} kg/s")
    
    # Infrastructure parameters
    print(f"\nINFRASTRUCTURE PARAMETERS:")
    print(f"  Number of wells: {value(m.fs.number_of_wells):.0f}")
    print(f"  Piping length: {value(m.fs.piping_length):.1f} km")
    print(f"  Pumping efficiency: {value(m.fs.pumping_efficiency):.1%}")
    print(f"  Static head: {value(m.fs.static_head):.1f} m")
    print(f"  Friction head: {value(m.fs.friction_head):.1f} m/km")
    print(f"  Calculated pumping head: {value(m.fs.pumping_head):.1f} m")
    
    # Shipping parameters
    print(f"\nSHIPPING PARAMETERS:")
    print(f"  Number of trucks: {value(m.fs.number_of_trucks):.0f}")
    print(f"  Shipping distance: {value(m.fs.shipping_distance):.1f} km")
    
    # Precipitate parameters
    print(f"\nPRECIPITATE PARAMETERS:")
    print(f"  Annual solid precipitate coefficient a: {value(m.fs.pond.annual_solid_precipitate_a):.1f} kg/m³")
    print(f"  Annual solid precipitate coefficient b: {value(m.fs.pond.annual_solid_precipitate_b):.1f} kg/m³")