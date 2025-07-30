from pyomo.environ import value
import pyomo.environ as pyo


def display_results(m):
    print("=" * 60)
    print("LITHIUM PROCESSING FLOWSHEET RESULTS")
    print("=" * 60)
    
    # Feed stream information
    print("\n--- FEED STREAM ---")
    feed = m.fs.feed.properties[0]
    print(f"Feed flow rate: {value(feed.flow_vol_phase['Liq']):.3f} m³/s")
    print(f"Feed temperature: {value(feed.temperature):.1f} K")
    print(f"Feed pressure: {value(feed.pressure):.1f} Pa")
    
    # Component concentrations in feed
    print("\nFeed composition (mol/L):")
    # Get the component list from the property package
    component_list = feed.component_list
    for comp in component_list:
        if value(feed.flow_mol_phase_comp['Liq', comp]) > 1e-6:
            conc = value(feed.flow_mol_phase_comp['Liq', comp] / feed.flow_vol_phase['Liq'])
            print(f"  {comp}: {conc:.6f}")

    # Product streams
    print("\n--- PRODUCT STREAMS ---")
    
    # Li2CO3 product
    if hasattr(m.fs, 'li2co3_product'):
        li2co3_product = m.fs.li2co3_product.properties[0]
        print(f"Li2CO3 product flow: {value(li2co3_product.flow_vol_phase['Liq']):.3f} m³/s")
        print("Li2CO3 product composition (mol/L):")
        for comp in component_list:
            if value(li2co3_product.flow_mol_phase_comp['Liq', comp]) > 1e-6:
                conc = value(li2co3_product.flow_mol_phase_comp['Liq', comp] / li2co3_product.flow_vol_phase['Liq'])
                print(f"  {comp}: {conc:.6f}")

    # Waste streams
    if hasattr(m.fs, 'li2co3_softening_waste'):
        softening_waste = m.fs.li2co3_softening_waste.properties[0]
        print(f"\nSoftening waste flow: {value(softening_waste.flow_vol_phase['Liq']):.3f} m³/s")
        
    if hasattr(m.fs, 'li2co3_separation_waste'):
        separation_waste = m.fs.li2co3_separation_waste.properties[0]
        print(f"Separation waste flow: {value(separation_waste.flow_vol_phase['Liq']):.3f} m³/s")
        print("Separation waste composition (mol/L):")
        for comp in component_list:
            if value(separation_waste.flow_mol_phase_comp['Liq', comp]) > 1e-6:
                conc = value(separation_waste.flow_mol_phase_comp['Liq', comp] / separation_waste.flow_vol_phase['Liq'])
                print(f"  {comp}: {conc:.6f}")

    # Process performance
    print("\n--- PROCESS PERFORMANCE ---")
    
    # Calculate and display lithium recovery
    try:
        from watertap_contrib.reflo.analysis.example_flowsheets.li_processing.utils import calculate_lithium_recovery, calculate_water_balance
        calculate_lithium_recovery(m)
        calculate_water_balance(m)
    except Exception as e:
        print(f"Could not calculate performance metrics: {e}")
    
    # Calculate annual Li2CO3 production
    if hasattr(m.fs, 'li2co3_product'):
        try:
            # Calculate Li2CO3 production from lithium flow
            M_Li = 6.94e-3  # kg/mol
            M_Li2CO3 = 73.89e-3  # kg/mol
            li_mass_flow = value(li2co3_product.flow_mass_phase_comp["Liq", "li+"])  # kg/s
            li2co3_mass_flow = li_mass_flow * (M_Li2CO3 / (2 * M_Li))  # kg/s
            annual_li2co3_production = li2co3_mass_flow * 3600 * 24 * 365 / 1000  # tonnes/year
            print(f"Annual Li2CO3 production: {annual_li2co3_production:.1f} tonnes/year")
        except Exception as e:
            print(f"Could not calculate annual Li2CO3 production: {e}")

    # Unit performance & costing
    print("\n--- UNIT PERFORMANCE & COSTING ---")
    
    # Check if any costing is available
    has_costing = False
    
    # Check treatment costing
    if hasattr(m.fs, 'treatment_costing'):
        has_costing = True
        print("\n** Treatment Costing (Standard WaterTAP Units) **")
        try:
            tc = m.fs.treatment_costing
            print(f"Capital cost: ${value(tc.total_capital_cost):,.0f}")
            print(f"Operating cost: ${value(tc.total_operating_cost):,.0f}/year")
            
            # Show unit-specific costs
            if hasattr(m.fs, 'boron_removal') and hasattr(m.fs.boron_removal, 'costing'):
                br_cost = m.fs.boron_removal.costing
                if hasattr(br_cost, 'capital_cost'):
                    print(f"  - Boron Removal capital: ${value(br_cost.capital_cost):,.0f}")
                if hasattr(br_cost, 'fixed_operating_cost'):
                    print(f"  - Boron Removal operating: ${value(br_cost.fixed_operating_cost):,.0f}/year")
                    
        except Exception as e:
            print(f"Error displaying treatment costing: {e}")
    
    # Check REFLO costing
    if hasattr(m.fs, 'reflo_costing'):
        has_costing = True
        print("\n** REFLO Costing (Custom Units) **")
        try:
            rc = m.fs.reflo_costing
            print(f"Capital cost: ${value(rc.total_capital_cost):,.0f}")
            print(f"Operating cost: ${value(rc.total_operating_cost):,.0f}/year")
            
            # Show LCOW if available
            if hasattr(rc, 'LCOW'):
                print(f"LCOW: ${value(rc.LCOW):.4f}/m³")
                
            # Show unit-specific costs
            if hasattr(m.fs, 'softening') and hasattr(m.fs.softening, 'costing'):
                soft_cost = m.fs.softening.costing
                if hasattr(soft_cost, 'capital_cost'):
                    print(f"  - Chemical Softening capital: ${value(soft_cost.capital_cost):,.0f}")
                if hasattr(soft_cost, 'fixed_operating_cost'):
                    print(f"  - Chemical Softening operating: ${value(soft_cost.fixed_operating_cost):,.0f}/year")
                    
        except Exception as e:
            print(f"Error displaying REFLO costing: {e}")
    
    # Show aggregated costs if available
    if hasattr(m.fs, 'total_capital_cost') and hasattr(m.fs, 'total_operating_cost'):
        print("\n** Total Aggregated Costs **")
        try:
            print(f"Total capital cost: ${value(m.fs.total_capital_cost):,.0f}")
            print(f"Total operating cost: ${value(m.fs.total_operating_cost):,.0f}/year")
        except Exception as e:
            print(f"Error displaying aggregated costs: {e}")
    
    if not has_costing:
        print("✗ Costing is not enabled")

    print("=" * 60) 