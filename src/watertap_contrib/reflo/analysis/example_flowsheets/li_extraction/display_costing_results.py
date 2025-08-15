"""Display module for costing results.

Prints comprehensive costing analysis results from the lithium extraction flowsheet.
"""

from pyomo.environ import value

def display_costing_results(m, detailed=False):
    """Display comprehensive costing results from the lithium extraction flowsheet.
    
    Args:
        m: Pyomo model with solved flowsheet and costing
        detailed: Whether to show detailed breakdown
    """
    print("\n" + "="*50)
    print("COSTING RESULTS")
    print("="*50)
    try:
        # Basic costing results
        print(f"\nBASIC COSTING RESULTS:")
        if hasattr(m.fs.pond.costing, 'capital_cost'):
            print(f"  Pond capital cost: ${value(m.fs.pond.costing.capital_cost):,.0f}")
        if hasattr(m.fs.pond.costing, 'total_capital_cost'):
            print(f"  Total capital cost: ${value(m.fs.pond.costing.total_capital_cost):,.0f}")
        if hasattr(m.fs, 'total_well_capital_cost'):
            print(f"  Well capital cost: ${value(m.fs.total_well_capital_cost):,.0f}")
        if hasattr(m.fs, 'total_piping_pump_capital_cost'):
            print(f"  Piping and pump capital cost: ${value(m.fs.total_piping_pump_capital_cost):,.0f}")
        if hasattr(m.fs, 'total_facilities_electrical_capital_cost'):
            print(f"  Facilities/electrical capital cost: ${value(m.fs.total_facilities_electrical_capital_cost):,.0f}")
        if hasattr(m.fs, 'total_truck_capital_cost'):
            print(f"  Truck capital cost: ${value(m.fs.total_truck_capital_cost):,.0f}")
        
        # LCOLi results
        if hasattr(m.fs.costing, 'LCOLi'):
            lcoli_vol = value(m.fs.costing.LCOLi)
            print(f"  Levelized Cost of Lithium (LCOLi): ${lcoli_vol:.2f} per m³ Li")
        if hasattr(m.fs.costing, 'LCOLi_mass'):
            lcoli_mass = value(m.fs.costing.LCOLi_mass)
            print(f"  Levelized Cost of Lithium (LCOLi): ${lcoli_mass:.2f} per mt Li")
        
        # Energy consumption
        if hasattr(m.fs.costing, 'specific_energy_consumption'):
            spec_energy = value(m.fs.costing.specific_energy_consumption)
            print(f"  Specific Energy Consumption: {spec_energy:.3f} kWh/m³")
            
            if hasattr(m.fs.costing, 'aggregate_flow_electricity'):
                total_electricity = value(m.fs.costing.aggregate_flow_electricity)
                print(f"  Total Electricity Consumption: {total_electricity:.1f} kW")
            
            if hasattr(m.fs.costing, 'specific_electrical_carbon_intensity'):
                spec_carbon = value(m.fs.costing.specific_electrical_carbon_intensity)
                print(f"  Specific Electrical Carbon Intensity: {spec_carbon:.3f} kg CO₂eq/m³")
        
        # Wellfield information
        if hasattr(m.fs, 'number_of_wells') and hasattr(m.fs, 'well_capital_cost'):
            print(f"\nWELLFIELD INFORMATION:")
            print(f"  Number of wells: {value(m.fs.number_of_wells):.0f}")
            print(f"  Cost per well: ${value(m.fs.well_capital_cost):,.0f}")
            print(f"  Total well capital cost: ${value(m.fs.total_well_capital_cost):,.0f}")
            
        # Piping and pump information
        if hasattr(m.fs, 'piping_length') and hasattr(m.fs, 'piping_unit_cost'):
            print(f"\nPIPING AND PUMP INFORMATION:")
            print(f"  Piping length: {value(m.fs.piping_length):.1f} km")
            print(f"  Piping unit cost: ${value(m.fs.piping_unit_cost):,.0f} per km")
            print(f"  Total piping and pump capital cost: ${value(m.fs.total_piping_pump_capital_cost):,.0f}")
            
        # Facilities and electrical information
        if hasattr(m.fs, 'facilities_electrical_unit_cost'):
            print(f"\nFACILITIES AND ELECTRICAL INFORMATION:")
            print(f"  Number of wells: {value(m.fs.number_of_wells):.0f}")
            print(f"  Facilities/electrical cost per well: ${value(m.fs.facilities_electrical_unit_cost):,.0f}")
            print(f"  Total facilities/electrical capital cost: ${value(m.fs.total_facilities_electrical_capital_cost):,.0f}")
            
        # Pumping information
        if hasattr(m.fs, 'pumping_flow') and hasattr(m.fs, 'pumping_head'):
            print(f"\nPUMPING INFORMATION:")
            print(f"  Pumping flow: {value(m.fs.pumping_flow):,.0f} m³/year")
            print(f"  Static head: {value(m.fs.static_head):.1f} m")
            print(f"  Friction head: {value(m.fs.friction_head):.1f} m/km")
            print(f"  Calculated pumping head: {value(m.fs.pumping_head):.1f} m")
            print(f"  Pumping efficiency: {value(m.fs.pumping_efficiency):.1%}")
            print(f"  Pumping power: {value(m.fs.pumping_power):,.0f} kW")
            
        # Shipping cost information
        if hasattr(m.fs, 'shipping_distance'):
            print(f"\nSHIPPING INFORMATION:")
            print(f"  Shipping distance: {value(m.fs.shipping_distance):.1f} km")
            print(f"  Shipping unit cost: ${value(m.fs.shipping_unit_cost):.2e} per kg/km")
            print(f"  Annual concentrated brine outflow: {value(m.fs.annual_concentrated_brine_outflow):,.0f} kg/year")
            print(f"  Shipping cost per kg: ${value(m.fs.shipping_cost):.4f}")
            
            # Calculate total annual shipping cost
            total_shipping_cost = value(m.fs.shipping_cost) * value(m.fs.annual_concentrated_brine_outflow)
            print(f"  Total annual shipping cost: ${total_shipping_cost:,.0f}/year")
            
        # Government agreements cost information
        if hasattr(m.fs, 'government_agreements_unit_cost'):
            print(f"\nGOVERNMENT AGREEMENTS INFORMATION:")
            print(f"  Government agreements unit cost: ${value(m.fs.government_agreements_unit_cost):.4f} per kg Li")
            if hasattr(m.fs, 'annual_lithium_outflow'):
                print(f"  Annual lithium outflow: {value(m.fs.annual_lithium_outflow):,.0f} kg/year")
                print(f"  Government agreements cost per kg: ${value(m.fs.government_agreements_cost):.4f}")
                
                # Calculate total annual government agreements cost
                total_gov_agreements_cost = value(m.fs.government_agreements_cost) * value(m.fs.annual_lithium_outflow)
                print(f"  Total annual government agreements cost: ${total_gov_agreements_cost:,.0f}/year")
            
        # Truck information
        if hasattr(m.fs, 'number_of_trucks') and hasattr(m.fs, 'truck_capital_cost'):
            print(f"\nTRUCK INFORMATION:")
            print(f"  Number of trucks: {value(m.fs.number_of_trucks):.0f}")
            print(f"  Cost per truck: ${value(m.fs.truck_capital_cost):,.0f}")
            print(f"  Total truck capital cost: ${value(m.fs.total_truck_capital_cost):,.0f}")
            
        # Display aggregate flow costs if available
        if hasattr(m.fs.costing, 'used_flows') and hasattr(m.fs.costing, 'aggregate_flow_costs'):
            print(f"\nFLOW COSTS:")
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
            
            # Total capital cost
            if hasattr(m.fs.pond.costing, 'total_capital_cost'):
                total_capex = value(m.fs.pond.costing.total_capital_cost)
                print(f"Total Capital Cost:              ${total_capex:,.0f}")
            
            # Pond capital costs
            if hasattr(m.fs.pond.costing, 'capital_cost'):
                pond_capex = value(m.fs.pond.costing.capital_cost)
                print(f"  Pond Capital Cost:             ${pond_capex:,.0f}")
                
                # Pond components
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
                    
            if hasattr(m.fs, 'total_truck_capital_cost'):
                truck_capex = value(m.fs.total_truck_capital_cost)
                print(f"  Truck Capital Cost:            ${truck_capex:,.0f}")
                if hasattr(m.fs, 'number_of_trucks') and hasattr(m.fs, 'truck_capital_cost'):
                    num_trucks = value(m.fs.number_of_trucks)
                    cost_per_truck = value(m.fs.truck_capital_cost)
                    print(f"    ({num_trucks:.0f} trucks × ${cost_per_truck:,.0f}/truck × 1.36 indirect cost multiplier)")
                    
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
                        
                        # Show detailed breakdown for specific flow types
                        if flow == "government_agreements" and hasattr(m.fs, 'annual_lithium_outflow'):
                            li_outflow = value(m.fs.annual_lithium_outflow)
                            unit_cost = value(m.fs.government_agreements_cost)
                            print(f"      (Government agreements: {li_outflow:,.0f} kg/year × ${unit_cost:.4f}/kg)")
                        elif flow == "shipping" and hasattr(m.fs, 'annual_concentrated_brine_outflow'):
                            brine_outflow = value(m.fs.annual_concentrated_brine_outflow)
                            shipping_cost_per_kg = value(m.fs.shipping_cost)
                            print(f"      (Shipping: {brine_outflow:,.0f} kg/year × ${shipping_cost_per_kg:.4f}/kg)")
                        elif flow == "electricity" and hasattr(m.fs, 'pumping_power'):
                            power = value(m.fs.pumping_power)
                            print(f"      (Pumping power: {power:.1f} kW)")
            
            # Energy Consumption Breakdown
            print("\nENERGY CONSUMPTION BREAKDOWN:")
            print("-" * 30)
            
            if hasattr(m.fs.costing, 'specific_energy_consumption'):
                total_spec_energy = value(m.fs.costing.specific_energy_consumption)
                print(f"Total Specific Energy Consumption: {total_spec_energy:.3f} kWh/m³")
                
                # Show aggregate electricity consumption
                if hasattr(m.fs.costing, 'aggregate_flow_electricity'):
                    total_electricity = value(m.fs.costing.aggregate_flow_electricity)
                    print(f"Total Electricity Consumption:    {total_electricity:.1f} kW")
                
                # Show specific electrical carbon intensity if available
                if hasattr(m.fs.costing, 'specific_electrical_carbon_intensity'):
                    spec_carbon = value(m.fs.costing.specific_electrical_carbon_intensity)
                    print(f"Specific Electrical Carbon Intensity: {spec_carbon:.3f} kg CO₂eq/m³")
                    
                    # Show carbon intensity component breakdown if available
                    if hasattr(m.fs.costing, 'specific_electrical_carbon_intensity_component'):
                        print("  Carbon Intensity Component Breakdown:")
                        for component, carbon_intensity in m.fs.costing.specific_electrical_carbon_intensity_component.items():
                            try:
                                comp_value = value(carbon_intensity)
                                if comp_value > 0:
                                    percentage = (comp_value / spec_carbon) * 100
                                    print(f"    {component}: {comp_value:.3f} kg CO₂eq/m³ ({percentage:.1f}%)")
                            except Exception:
                                pass
                
                # Show component breakdown
                if hasattr(m.fs.costing, 'specific_energy_consumption_component'):
                    print("  Component Breakdown:")
                    for component, consumption in m.fs.costing.specific_energy_consumption_component.items():
                        try:
                            comp_value = value(consumption)
                            if comp_value > 0:
                                percentage = (comp_value / total_spec_energy) * 100
                                print(f"    {component}: {comp_value:.3f} kWh/m³ ({percentage:.1f}%)")
                        except Exception:
                            pass
                
                # Show annual water production for context
                if hasattr(m.fs.costing, 'annual_water_production'):
                    annual_production = value(m.fs.costing.annual_water_production)
                    print(f"Annual Water Production:         {annual_production:,.0f} m³/year")
                    
                    # Calculate total annual energy consumption
                    if hasattr(m.fs.costing, 'aggregate_flow_electricity'):
                        annual_energy = total_electricity * 8760  # hours per year
                        print(f"Total Annual Energy Consumption: {annual_energy:,.0f} kWh/year")
                        
                        # Calculate total annual carbon emissions
                        if hasattr(m.fs.costing, 'specific_electrical_carbon_intensity'):
                            annual_carbon = spec_carbon * annual_production
                            print(f"Total Annual Carbon Emissions:  {annual_carbon:,.0f} kg CO₂eq/year")
            
            # Annual Flow Costs Summary
            print("\nANNUAL FLOW COSTS SUMMARY:")
            print("-" * 30)
            total_annual_flow_costs = 0
            if hasattr(m.fs.costing, 'used_flows') and hasattr(m.fs.costing, 'aggregate_flow_costs'):
                for flow in m.fs.costing.used_flows:
                    try:
                        flow_cost = value(m.fs.costing.aggregate_flow_costs[flow])
                        total_annual_flow_costs += flow_cost
                        print(f"  {flow.capitalize()}: ${flow_cost:,.0f}/year")
                    except Exception:
                        pass
                print(f"  Total Annual Flow Costs: ${total_annual_flow_costs:,.0f}/year")
            
            print("="*50)
            
    except Exception as e:
        print(f"Error displaying costing results: {e}")
    print("="*50) 