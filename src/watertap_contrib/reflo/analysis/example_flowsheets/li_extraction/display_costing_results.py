from pyomo.environ import value

def display_costing_results(m, detailed=False):
    print("\n" + "="*50)
    print("COSTING RESULTS")
    print("="*50)
    try:
        if hasattr(m.fs.pond.costing, 'capital_cost'):
            print(f"Pond capital cost: ${value(m.fs.pond.costing.capital_cost):,.0f}")
        if hasattr(m.fs, 'total_well_capital_cost'):
            print(f"Well capital cost: ${value(m.fs.total_well_capital_cost):,.0f}")
        if hasattr(m.fs, 'total_piping_pump_capital_cost'):
            print(f"Piping and pump capital cost: ${value(m.fs.total_piping_pump_capital_cost):,.0f}")
        if hasattr(m.fs, 'total_facilities_electrical_capital_cost'):
            print(f"Facilities/electrical capital cost: ${value(m.fs.total_facilities_electrical_capital_cost):,.0f}")
        if hasattr(m.fs.costing, 'total_capital_cost'):
            print(f"Total capital cost: ${value(m.fs.costing.total_capital_cost):,.0f}")
        if hasattr(m.fs.costing, 'LCOLi'):
            lcoli_vol = value(m.fs.costing.LCOLi)
            lcoli_mass = value(m.fs.costing.LCOLi_mass)
            print(f"Levelized Cost of Lithium (LCOLi): ${lcoli_vol:.2f} per m³ Li, ${lcoli_mass:.2f} per mt Li")
        
        # Well information
        if hasattr(m.fs, 'number_of_wells') and hasattr(m.fs, 'well_capital_cost'):
            print(f"\nWell Information:")
            print(f"  Number of wells: {value(m.fs.number_of_wells):.0f}")
            print(f"  Cost per well: ${value(m.fs.well_capital_cost):,.0f}")
            print(f"  Total well capital cost: ${value(m.fs.total_well_capital_cost):,.0f}")
            
        # Piping and pump information
        if hasattr(m.fs, 'piping_length') and hasattr(m.fs, 'piping_unit_cost'):
            print(f"\nPiping and Pump Information:")
            print(f"  Piping length: {value(m.fs.piping_length):.1f} km")
            print(f"  Piping unit cost: ${value(m.fs.piping_unit_cost):,.0f} per km")
            print(f"  Total piping and pump capital cost: ${value(m.fs.total_piping_pump_capital_cost):,.0f}")
            
        # Facilities and electrical information
        if hasattr(m.fs, 'facilities_electrical_unit_cost'):
            print(f"\nFacilities and Electrical Information:")
            print(f"  Number of wells: {value(m.fs.number_of_wells):.0f}")
            print(f"  Facilities/electrical cost per well: ${value(m.fs.facilities_electrical_unit_cost):,.0f}")
            print(f"  Total facilities/electrical capital cost: ${value(m.fs.total_facilities_electrical_capital_cost):,.0f}")
            
        # Pumping information
        if hasattr(m.fs, 'pumping_flow') and hasattr(m.fs, 'pumping_head'):
            print(f"\nPumping Information:")
            print(f"  Pumping flow: {value(m.fs.pumping_flow):,.0f} m³/year")
            print(f"  Static head: {value(m.fs.static_head):.1f} m")
            print(f"  Friction head: {value(m.fs.friction_head):.1f} m/km")
            print(f"  Calculated pumping head: {value(m.fs.pumping_head):.1f} m")
            print(f"  Pumping efficiency: {value(m.fs.pumping_efficiency):.1%}")
            print(f"  Pumping unit cost: ${value(m.fs.pumping_unit_cost):.4f} per m³")
            
        # Shipping cost information
        if hasattr(m.fs, 'shipping_distance'):
            print(f"\nShipping Information:")
            print(f"  Shipping distance: {value(m.fs.shipping_distance):.1f} km")
            print(f"  Shipping unit cost: ${value(m.fs.shipping_unit_cost):.2e} per kg/km")
            print(f"  Annual concentrated brine outflow: {value(m.fs.annual_concentrated_brine_outflow):,.0f} kg/year")
            print(f"  Shipping cost per kg: ${value(m.fs.shipping_cost):.4f}")
            
            # Calculate total annual shipping cost
            total_shipping_cost = value(m.fs.shipping_cost) * value(m.fs.annual_concentrated_brine_outflow)
            print(f"  Total annual shipping cost: ${total_shipping_cost:,.0f}/year")
            
        # Display aggregate flow costs if available
        if hasattr(m.fs.costing, 'used_flows') and hasattr(m.fs.costing, 'aggregate_flow_costs'):
            print(f"\nFlow Costs:")
            for flow in m.fs.costing.used_flows:
                try:
                    cost = value(m.fs.costing.aggregate_flow_costs[flow])
                    print(f"  {flow.capitalize()} cost: ${cost:,.0f}/year")
                except Exception:
                    pass
                    
        if detailed:
            print("\n" + "="*50)
            print("DETAILED COST BREAKDOWN")
            print("="*50)
            
            # Capital Cost Breakdown
            print("\nCAPITAL COST BREAKDOWN:")
            print("-" * 30)
            
            # Flowsheet-level capital costs
            if hasattr(m.fs.costing, 'total_capital_cost'):
                total_capex = value(m.fs.costing.total_capital_cost)
                print(f"Total Capital Cost:              ${total_capex:,.0f}")
            if hasattr(m.fs.costing, 'aggregate_capital_cost'):
                agg_capex = value(m.fs.costing.aggregate_capital_cost)
                print(f"Aggregate Capital Cost:          ${agg_capex:,.0f}")
            if hasattr(m.fs.costing, 'aggregate_direct_capital_cost'):
                direct_capex = value(m.fs.costing.aggregate_direct_capital_cost)
                print(f"Aggregate Direct Capital Cost:   ${direct_capex:,.0f}")
            
            # Pond capital costs
            if hasattr(m.fs.pond.costing, 'capital_cost'):
                pond_capex = value(m.fs.pond.costing.capital_cost)
                print(f"  Pond Capital Cost:             ${pond_capex:,.0f}")
                
                # Pond components (based on actual evaporation pond costing)
                if hasattr(m.fs.pond.costing, 'land_capital_cost'):
                    land_cost = value(m.fs.pond.costing.land_capital_cost)
                    print(f"    - Land Cost:                 ${land_cost:,.0f}")
                if hasattr(m.fs.pond.costing, 'land_clearing_capital_cost'):
                    clearing_cost = value(m.fs.pond.costing.land_clearing_capital_cost)
                    print(f"    - Land Clearing Cost:        ${clearing_cost:,.0f}")
                if hasattr(m.fs.pond.costing, 'dike_capital_cost'):
                    dike_cost = value(m.fs.pond.costing.dike_capital_cost)
                    print(f"    - Dike Cost:                 ${dike_cost:,.0f}")
                if hasattr(m.fs.pond.costing, 'liner_capital_cost'):
                    liner_cost = value(m.fs.pond.costing.liner_capital_cost)
                    print(f"    - Liner Cost:                ${liner_cost:,.0f}")
                if hasattr(m.fs.pond.costing, 'fence_capital_cost'):
                    fence_cost = value(m.fs.pond.costing.fence_capital_cost)
                    print(f"    - Fence Cost:                ${fence_cost:,.0f}")
                if hasattr(m.fs.pond.costing, 'road_capital_cost'):
                    road_cost = value(m.fs.pond.costing.road_capital_cost)
                    print(f"    - Road Cost:                 ${road_cost:,.0f}")
                    
            # Extraction capital costs
            if hasattr(m.fs, 'total_well_capital_cost'):
                well_capex = value(m.fs.total_well_capital_cost)
                print(f"  Well Capital Cost:             ${well_capex:,.0f}")
                if hasattr(m.fs, 'number_of_wells') and hasattr(m.fs, 'well_capital_cost'):
                    num_wells = value(m.fs.number_of_wells)
                    cost_per_well = value(m.fs.well_capital_cost)
                    print(f"    ({num_wells:.0f} wells × ${cost_per_well:,.0f}/well)")
                    
            if hasattr(m.fs, 'total_piping_pump_capital_cost'):
                piping_pump_capex = value(m.fs.total_piping_pump_capital_cost)
                print(f"  Piping and Pump Capital Cost:  ${piping_pump_capex:,.0f}")
                if hasattr(m.fs, 'piping_length') and hasattr(m.fs, 'piping_unit_cost'):
                    pipe_length = value(m.fs.piping_length)
                    cost_per_km = value(m.fs.piping_unit_cost)
                    print(f"    ({pipe_length:.1f} km × ${cost_per_km:,.0f}/km)")
                    
            if hasattr(m.fs, 'total_facilities_electrical_capital_cost'):
                facilities_electrical_capex = value(m.fs.total_facilities_electrical_capital_cost)
                print(f"  Facilities/Electrical Capital: ${facilities_electrical_capex:,.0f}")
                if hasattr(m.fs, 'number_of_wells') and hasattr(m.fs, 'facilities_electrical_unit_cost'):
                    num_wells = value(m.fs.number_of_wells)
                    cost_per_well = value(m.fs.facilities_electrical_unit_cost)
                    print(f"    ({num_wells:.0f} wells × ${cost_per_well:,.0f}/well)")
                    
            if hasattr(m.fs.pond.costing, 'direct_capital_cost'):
                direct_cost = value(m.fs.pond.costing.direct_capital_cost)
                print(f"  Direct Capital Cost:           ${direct_cost:,.0f}")
                    
            # Operating Cost Breakdown
            print("\nOPERATING COST BREAKDOWN:")
            print("-" * 30)
            
            # Total operating cost
            if hasattr(m.fs.costing, 'total_operating_cost'):
                total_opex = value(m.fs.costing.total_operating_cost)
                print(f"Total Operating Cost:            ${total_opex:,.0f}/year")
                
            # Aggregate operating costs
            if hasattr(m.fs.costing, 'aggregate_fixed_operating_cost'):
                agg_fixed = value(m.fs.costing.aggregate_fixed_operating_cost)
                print(f"  Aggregate Fixed Operating Cost: ${agg_fixed:,.0f}/year")
            if hasattr(m.fs.costing, 'aggregate_variable_operating_cost'):
                agg_var = value(m.fs.costing.aggregate_variable_operating_cost)
                print(f"  Aggregate Variable Operating Cost: ${agg_var:,.0f}/year")
                
            # Fixed operating costs breakdown
            if hasattr(m.fs.costing, 'total_fixed_operating_cost'):
                total_fixed = value(m.fs.costing.total_fixed_operating_cost)
                print(f"  Total Fixed Operating Cost:     ${total_fixed:,.0f}/year")
            if hasattr(m.fs.costing, 'maintenance_labor_chemical_operating_cost'):
                mlc_cost = value(m.fs.costing.maintenance_labor_chemical_operating_cost)
                print(f"    - Maintenance/Labor/Chemical: ${mlc_cost:,.0f}/year")
                
            # Variable operating costs
            if hasattr(m.fs.costing, 'total_variable_operating_cost'):
                total_var = value(m.fs.costing.total_variable_operating_cost)
                print(f"  Total Variable Operating Cost:  ${total_var:,.0f}/year")
                
            # Pond operating costs
            if hasattr(m.fs.pond.costing, 'fixed_operating_cost'):
                pond_fixed = value(m.fs.pond.costing.fixed_operating_cost)
                print(f"  Pond Fixed Operating Cost:      ${pond_fixed:,.0f}/year")
                
                # Pond operating components
                if hasattr(m.fs.pond.costing, 'recovered_solids_handling_operating_cost'):
                    solids_cost = value(m.fs.pond.costing.recovered_solids_handling_operating_cost)
                    print(f"    - Recovered Solids Handling:  ${solids_cost:,.0f}/year")
                if hasattr(m.fs.pond.costing, 'liner_replacement_operating_cost'):
                    liner_repl = value(m.fs.pond.costing.liner_replacement_operating_cost)
                    print(f"    - Liner Replacement:         ${liner_repl:,.0f}/year")
                    
            # Check for utility flows and their costs
            if hasattr(m.fs.costing, 'used_flows'):
                print("  Flow Costs:")
                for flow in m.fs.costing.used_flows:
                    if hasattr(m.fs.costing, 'aggregate_flow_costs'):
                        flow_cost = value(m.fs.costing.aggregate_flow_costs[flow])
                        print(f"    - {flow.capitalize()} Flow Cost:    ${flow_cost:,.0f}/year")
                        
            print("="*50)
            
    except Exception as e:
        print(f"Error displaying costing results: {e}")
    print("="*50) 