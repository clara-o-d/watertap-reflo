"""Display module for initial flowsheet results.

Prints comprehensive results from the lithium extraction flowsheet simulation.
"""

from pyomo.environ import units as pyunits, value

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
    print(f"  Water activity: {value(m.fs.pond.water_activity):.4f}")
    print(f"  Area correction factor: {value(m.fs.pond.area_correction_factor):.4f}")
    print(f"  Average mass flux of water vapor: {value(m.fs.pond.mass_flux_water_vapor_average):.2e} kg/(m²·s)")
    
    # Process parameters
    print(f"\nPROCESS PARAMETERS:")
    print(f"  Solution density: {value(m.fs.rho):.0f} kg/m³")
    print(f"  Pond overdesign factor: {value(m.fs.pond_overdesign_factor):.2f}")
    
    # Flow process parameters
    print(f"\nFLOW PROCESS PARAMETERS:")
    print(f"  Final Li+ concentration: {value(m.fs.final_li_conc):.3f} kg/kg")
    print(f"  Lithium recovery fraction: {value(m.fs.li_recovery):.2f}")
    print(f"  Final TDS concentration: {value(m.fs.final_tds_conc):.3f} kg/kg")
    
    # Evaporation and flow results
    print(f"\nEVAPORATION AND FLOW RESULTS:")
    print(f"  Fraction of water evaporated: {value(m.fs.fraction_evaporated):.3f}")
    water_evaporated = value(m.fs.feed.properties[0].flow_mass_phase_comp['Liq', 'H2O'] * m.fs.fraction_evaporated)
    print(f"  Water evaporated: {water_evaporated:.2f} kg/s")
    print(f"  Water outflow: {value(m.fs.water_outflow):.2f} kg/s")
    print(f"  TDS outflow: {value(m.fs.tds_outflow):.2f} kg/s")
    print(f"  Li+ outflow: {value(m.fs.li_outflow):.2f} kg/s")
    print(f"  Actual Li+ concentration: {value(m.fs.li_outflow / (m.fs.concentrated_brine_outflow) * 1000):.2f} g/kg")
    print(f"  Concentrated brine outflow: {value(m.fs.concentrated_brine_outflow):.2f} kg/s")
    print(f"  Mass flow of precipitate: {value(m.fs.pond.mass_flow_precipitate):,.0f} kg/year")
    
    # Brine extraction infrastructure parameters
    print(f"\nBRINE EXTRACTION INFRASTRUCTURE:")
    print(f"  Number of wells: {value(m.fs.number_of_wells):.0f}")
    print(f"  Piping length: {value(m.fs.piping_length):.1f} km")
    print(f"  Pumping efficiency: {value(m.fs.pumping_efficiency):.1%}")
    print(f"  Static head: {value(m.fs.static_head):.1f} m")
    print(f"  Friction head: {value(m.fs.friction_head):.1f} m/km")
    print(f"  Calculated pumping head: {value(m.fs.pumping_head):.1f} m")
    
    # Shipping infrastructure parameters
    print(f"\nSHIPPING INFRASTRUCTURE:")
    print(f"  Number of trucks: {value(m.fs.number_of_trucks):.0f}")
    print(f"  Shipping distance: {value(m.fs.shipping_distance):.1f} km")
    
    # Lithium outflow parameters
    print(f"\nLITHIUM OUTFLOW SUMMARY:")
    print(f"  Li+ outflow: {value(m.fs.li_outflow):.4f} kg/s")
    print(f"  Annual Li+ outflow: {value(pyunits.convert(m.fs.li_outflow, to_units=pyunits.kg/pyunits.year)):,.0f} kg/year")
    print(f"  Lithium recovery efficiency: {value(m.fs.li_recovery):.1%}")
    
    # Government agreements parameters
    if hasattr(m.fs, 'government_agreements_unit_cost'):
        print(f"\nGOVERNMENT AGREEMENTS PARAMETERS:")
        print(f"  Government agreements unit cost: ${value(m.fs.government_agreements_unit_cost):.4f} per kg Li")
        if hasattr(m.fs, 'annual_lithium_outflow'):
            print(f"  Annual lithium outflow for agreements: {value(m.fs.annual_lithium_outflow):,.0f} kg/year")