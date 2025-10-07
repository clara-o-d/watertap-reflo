"""Display module for lithium processing flowsheet results.

Prints comprehensive results from the lithium carbonate processing flowsheet simulation.
"""

from pyomo.environ import units as pyunits, value

def display_costing_results(m):
    """Display costing results from the lithium processing flowsheet.
    
    Args:
        m: Pyomo model with solved flowsheet and costing
    """
    if not hasattr(m.fs, 'costing'):
        print("\nNo costing information available. Run add_costing() first.")
        return
    
    print("\n" + "="*60)
    print("LITHIUM CARBONATE PROCESSING PLANT COSTING RESULTS")
    print("="*60)
    
    # Global costing parameters
    print(f"\nGLOBAL COSTING PARAMETERS:")
    print(f"  Plant lifetime: {value(m.fs.costing.plant_lifetime):.0f} years")
    print(f"  WACC: {value(m.fs.costing.wacc):.1%}")
    print(f"  Electricity cost: ${value(m.fs.costing.electricity_cost):.3f}/kWh")
    print(f"  Utilization factor: {value(m.fs.costing.utilization_factor):.1%}")
    print(f"  Base currency: {m.fs.costing.base_currency}")
    
    # Unit model capital costs
    print(f"\nUNIT MODEL CAPITAL COSTS:")
    
    if hasattr(m.fs.brine_storage, 'costing'):
        print(f"  Storage Tank Capital Cost: ${value(m.fs.brine_storage.costing.capital_cost):,.0f}")
    
    if hasattr(m.fs.brine_pump, 'costing'):
        print(f"  Pump Capital Cost: ${value(m.fs.brine_pump.costing.capital_cost):,.0f}")
    
    if hasattr(m.fs.softening_reactor, 'costing'):
        print(f"  Softening Reactor Capital Cost: ${value(m.fs.softening_reactor.costing.capital_cost):,.0f}")
    
    if hasattr(m.fs.lithium_carbonate_reactor, 'costing'):
        print(f"  Lithium Carbonate Reactor Capital Cost: ${value(m.fs.lithium_carbonate_reactor.costing.capital_cost):,.0f}")
    
    # Total capital cost
    total_capital_cost = 0
    if hasattr(m.fs.brine_storage, 'costing'):
        total_capital_cost += value(m.fs.brine_storage.costing.capital_cost)
    if hasattr(m.fs.brine_pump, 'costing'):
        total_capital_cost += value(m.fs.brine_pump.costing.capital_cost)
    if hasattr(m.fs.softening_reactor, 'costing'):
        total_capital_cost += value(m.fs.softening_reactor.costing.capital_cost)
    if hasattr(m.fs.lithium_carbonate_reactor, 'costing'):
        total_capital_cost += value(m.fs.lithium_carbonate_reactor.costing.capital_cost)
    
    print(f"\n  TOTAL CAPITAL COST: ${total_capital_cost:,.0f}")
    
    # Operating costs
    print(f"\nOPERATING COSTS:")
    
    # Electricity costs
    if hasattr(m.fs, 'brine_pump') and hasattr(m.fs.brine_pump.control_volume, 'work'):
        pump_power = value(m.fs.brine_pump.control_volume.work[0])  # W
        pump_power_kw = pump_power / 1000  # kW
        annual_electricity_cost = pump_power_kw * value(m.fs.costing.electricity_cost) * 8760 * value(m.fs.costing.utilization_factor)
        print(f"  Annual electricity cost: ${annual_electricity_cost:,.0f}")
    
    # Reagent costs
    if hasattr(m.fs, 'softening_reactor'):
        try:
            na2co3_flow = value(m.fs.softening_reactor.flow_mass_reagent["Na2CO3"])  # kg/s
            annual_na2co3_cost = na2co3_flow * 31536000 * value(m.fs.soda_ash_cost)  # kg/year * $/kg
            print(f"  Annual Na2CO3 cost (softening): ${annual_na2co3_cost:,.0f}")
        except (AttributeError, TypeError, KeyError):
            pass
        
        try:
            cao_flow = value(m.fs.softening_reactor.flow_mass_reagent["CaO"])  # kg/s
            annual_cao_cost = cao_flow * 31536000 * value(m.fs.lime_cost)  # kg/year * $/kg
            print(f"  Annual CaO cost (softening): ${annual_cao_cost:,.0f}")
        except (AttributeError, TypeError, KeyError):
            pass
    
    if hasattr(m.fs, 'lithium_carbonate_reactor'):
        try:
            na2co3_flow = value(m.fs.lithium_carbonate_reactor.flow_mass_reagent["Na2CO3"])  # kg/s
            annual_na2co3_cost = na2co3_flow * 31536000 * value(m.fs.soda_ash_cost)  # kg/year * $/kg
            print(f"  Annual Na2CO3 cost (Li2CO3): ${annual_na2co3_cost:,.0f}")
        except (AttributeError, TypeError, KeyError):
            pass
    
    # Annual operating cost (excluding capital recovery)
    total_opex = 0
    if hasattr(m.fs, 'brine_pump') and hasattr(m.fs.brine_pump.control_volume, 'work'):
        total_opex += annual_electricity_cost
    
    # Add reagent costs if available
    try:
        if hasattr(m.fs, 'softening_reactor'):
            na2co3_flow = value(m.fs.softening_reactor.flow_mass_reagent["Na2CO3"])
            total_opex += na2co3_flow * 31536000 * value(m.fs.soda_ash_cost)
            cao_flow = value(m.fs.softening_reactor.flow_mass_reagent["CaO"])
            total_opex += cao_flow * 31536000 * value(m.fs.lime_cost)
        
        if hasattr(m.fs, 'lithium_carbonate_reactor'):
            na2co3_flow = value(m.fs.lithium_carbonate_reactor.flow_mass_reagent["Na2CO3"])
            total_opex += na2co3_flow * 31536000 * value(m.fs.soda_ash_cost)
    except (AttributeError, TypeError, KeyError):
        pass
    
    print(f"\n  TOTAL ANNUAL OPERATING COST: ${total_opex:,.0f}")
    
    # Capital recovery cost
    capital_recovery_factor = value(m.fs.costing.wacc) * (1 + value(m.fs.costing.wacc))**value(m.fs.costing.plant_lifetime) / ((1 + value(m.fs.costing.wacc))**value(m.fs.costing.plant_lifetime) - 1)
    annual_capital_cost = total_capital_cost * capital_recovery_factor
    print(f"  Annual capital cost: ${annual_capital_cost:,.0f}")
    
    # Total annual cost
    total_annual_cost = total_opex + annual_capital_cost
    print(f"  TOTAL ANNUAL COST: ${total_annual_cost:,.0f}")
    
    # Cost per unit production
    if hasattr(m.fs, 'lithium_carbonate_reactor'):
        try:
            li2co3_production = value(m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3'])  # kg/s
            annual_li2co3_production = li2co3_production * 31536000  # kg/year
            cost_per_kg_li2co3 = total_annual_cost / annual_li2co3_production
            print(f"\n  COST PER KG Li2CO3: ${cost_per_kg_li2co3:.2f}/kg")
            print(f"  Annual Li2CO3 production: {annual_li2co3_production:,.0f} kg/year")
        except (AttributeError, TypeError, KeyError):
            pass
    
    # Display LCOLi and energy metrics if available
    if hasattr(m.fs.costing, 'LCOLi'):
        try:
            lcoli_vol = value(m.fs.costing.LCOLi)  # $/m³ Li
            lcoli_mass = value(m.fs.costing.LCOLi_mass)  # $/kg Li
            lcoli2co3_mass = value(m.fs.costing.LCOLi2CO3_mass)  # $/kg Li2CO3
            print(f"\n  LCOLi (per m³ Li): ${lcoli_vol:,.0f}/m³")
            print(f"  LCOLi (per kg Li): ${lcoli_mass:,.2f}/kg")
            print(f"  LCOLi2CO3 (per kg Li2CO3): ${lcoli2co3_mass:,.2f}/kg")
        except (AttributeError, TypeError, KeyError):
            pass
    
    if hasattr(m.fs.costing, 'specific_energy_consumption'):
        try:
            spec_energy_vol = value(m.fs.costing.specific_energy_consumption)  # kWh/m³ Li
            spec_energy_mass = value(m.fs.costing.specific_energy_consumption_mass)  # kWh/kg Li
            spec_energy_li2co3 = value(m.fs.costing.specific_energy_consumption_Li2CO3_mass)  # kWh/kg Li2CO3
            print(f"\n  Specific Energy (per m³ Li): {spec_energy_vol:.2f} kWh/m³")
            print(f"  Specific Energy (per kg Li): {spec_energy_mass:.2f} kWh/kg")
            print(f"  Specific Energy (per kg Li2CO3): {spec_energy_li2co3:.2f} kWh/kg")
        except (AttributeError, TypeError, KeyError):
            pass
    
    print(f"\n" + "="*60)
    print("END OF COSTING RESULTS")
    print("="*60)

def display_results(m, show_costing=False):
    """Display comprehensive results from the lithium processing flowsheet.
    
    Args:
        m: Pyomo model with solved flowsheet
    """
    print("\n" + "="*60)
    print("LITHIUM CARBONATE PROCESSING PLANT RESULTS")
    print("="*60)
    
    # Feed conditions
    print(f"\nBRINE FEED CONDITIONS:")
    print(f"  Temperature: {value(m.fs.brine_feed.properties[0].temperature):.1f} K")
    print(f"  Pressure: {value(m.fs.brine_feed.properties[0].pressure):.0f} Pa")
    print(f"  Total flow rate: {value(m.fs.brine_feed.properties[0].flow_vol):.2f} L/s")
    
    # Component flow rates
    print(f"\nCOMPONENT FLOW RATES (mol/s):")
    for comp in ["Li", "Na", "K", "Mg", "Ca", "Cl", "SO4", "B", "H2O"]:
        if comp in m.fs.brine_props.solute_set:
            flow = value(m.fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", comp])
            print(f"  {comp}: {flow:.4f}")
    
    # Storage tank results
    if hasattr(m.fs, 'brine_storage'):
        print(f"\nBRINE STORAGE TANK:")
        try:
            if hasattr(m.fs.brine_storage, 'storage_time'):
                print(f"  Storage time: {value(m.fs.brine_storage.storage_time[0]):.1f} hours")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            if hasattr(m.fs.brine_storage, 'surge_capacity'):
                print(f"  Surge capacity: {value(m.fs.brine_storage.surge_capacity[0]):.1f} hours")
        except (AttributeError, TypeError, KeyError):
            pass
    
    # Pump results
    if hasattr(m.fs, 'brine_pump'):
        print(f"\nBRINE PUMP:")
        try:
            print(f"  Pressure increase: {value(m.fs.brine_pump.deltaP[0]):.0f} Pa")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            print(f"  Pump efficiency: {value(m.fs.brine_pump.efficiency_pump[0]):.1%}")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            if hasattr(m.fs.brine_pump.control_volume, 'work'):
                print(f"  Power consumption: {value(m.fs.brine_pump.control_volume.work[0]):.2f} W")
        except (AttributeError, TypeError, KeyError):
            pass
    
    # Softening reactor results
    if hasattr(m.fs, 'softening_reactor'):
        print(f"\nMAGNESIUM/CALCIUM REMOVAL REACTOR:")
        try:
            print(f"  Na2CO3 dose: {value(m.fs.softening_reactor.reagent_dose['Na2CO3']):.4f} kg/L")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            print(f"  CaO dose: {value(m.fs.softening_reactor.reagent_dose['CaO']):.4f} kg/L")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            print(f"  Calcite formation: {value(m.fs.softening_reactor.flow_mass_precipitate['Calcite']):.4f} kg/s")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            print(f"  Brucite formation: {value(m.fs.softening_reactor.flow_mass_precipitate['Brucite']):.4f} kg/s")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            print(f"  Waste solids fraction: {value(m.fs.softening_reactor.waste_mass_frac_precipitate):.1%}")
        except (AttributeError, TypeError, KeyError):
            pass
    
    # Lithium carbonate reactor results
    if hasattr(m.fs, 'lithium_carbonate_reactor'):
        print(f"\nLITHIUM CARBONATE PRECIPITATION REACTOR:")
        try:
            print(f"  Na2CO3 dose: {value(m.fs.lithium_carbonate_reactor.reagent_dose['Na2CO3']):.4f} kg/L")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            print(f"  Li2CO3 formation: {value(m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3']):.4f} kg/s")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            print(f"  Waste solids fraction: {value(m.fs.lithium_carbonate_reactor.waste_mass_frac_precipitate):.1%}")
        except (AttributeError, TypeError, KeyError):
            pass
        
        # Calculate annual production
        try:
            annual_li2co3 = value(pyunits.convert(
                m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3'], 
                to_units=pyunits.kg/pyunits.year
            ))
            print(f"  Annual Li2CO3 production: {annual_li2co3:,.0f} kg/year")
        except (AttributeError, TypeError, KeyError):
            pass
    
    # Boron extraction results (if present)
    if hasattr(m.fs, 'boron_extraction'):
        print(f"\nBORON EXTRACTION:")
        print(f"  Number of stages: {m.fs.boron_extraction.config.number_of_finite_elements}")
        if hasattr(m.fs.boron_extraction, 'aqueous_inlet'):
            print(f"  Aqueous inlet flow: {value(m.fs.boron_extraction.aqueous_inlet.flow_vol[0]):.2f} L/s")
        if hasattr(m.fs.boron_extraction, 'organic_inlet'):
            print(f"  Organic inlet flow: {value(m.fs.boron_extraction.organic_inlet.flow_vol[0]):.2f} L/s")
    
    # Process efficiency metrics
    print(f"\nPROCESS EFFICIENCY METRICS:")
    
    # Lithium recovery calculation
    if hasattr(m.fs, 'lithium_carbonate_reactor'):
        li_in = value(m.fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", "Li"])
        li2co3_out = value(m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3'])
        li_mw = 6.94e-3  # kg/mol
        li2co3_mw = 73.89e-3  # kg/mol
        li_in_mass = li_in * li_mw  # kg/s
        li_out_mass = li2co3_out * (2 * li_mw / li2co3_mw)  # kg/s
        li_recovery = (li_out_mass / li_in_mass) * 100 if li_in_mass > 0 else 0
        print(f"  Lithium recovery: {li_recovery:.1f}%")
    
    # Chemical consumption
    if hasattr(m.fs, 'softening_reactor') and hasattr(m.fs, 'lithium_carbonate_reactor'):
        total_na2co3 = value(m.fs.softening_reactor.reagent_dose['Na2CO3']) + value(m.fs.lithium_carbonate_reactor.reagent_dose['Na2CO3'])
        print(f"  Total Na2CO3 consumption: {total_na2co3:.4f} kg/L brine")
        print(f"  CaO consumption: {value(m.fs.softening_reactor.reagent_dose['CaO']):.4f} kg/L brine")
    
    # Energy consumption
    total_power = 0
    if hasattr(m.fs, 'brine_pump') and hasattr(m.fs.brine_pump.control_volume, 'work'):
        total_power += value(m.fs.brine_pump.control_volume.work[0])
    if hasattr(m.fs, 'boron_pump') and hasattr(m.fs.boron_pump.control_volume, 'work'):
        total_power += value(m.fs.boron_pump.control_volume.work[0])
    
    if total_power > 0:
        print(f"  Total power consumption: {total_power:.2f} W")
        print(f"  Specific energy consumption: {total_power/value(m.fs.brine_feed.properties[0].flow_vol):.2f} W/(L/s)")
    
    # Product quality
    print(f"\nPRODUCT QUALITY:")
    if hasattr(m.fs, 'lithium_carbonate_reactor'):
        li2co3_purity = 100.0  # Assuming pure Li2CO3 precipitate
        print(f"  Li2CO3 purity: {li2co3_purity:.1f}%")
        print(f"  Li2CO3 production rate: {value(m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3']):.4f} kg/s")
    
    # Process summary
    print(f"\nPROCESS SUMMARY:")
    print(f"  Feed flow rate: {value(m.fs.brine_feed.properties[0].flow_vol):.2f} L/s")
    print(f"  Feed Li concentration: {value(m.fs.brine_feed.properties[0].flow_mol_phase_comp['Liq', 'Li']):.4f} mol/s")
    if hasattr(m.fs, 'lithium_carbonate_reactor'):
        print(f"  Li2CO3 production: {value(m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3']):.4f} kg/s")
        print(f"  Annual Li2CO3 production: {annual_li2co3:,.0f} kg/year")
    
    print(f"\n" + "="*60)
    print("END OF RESULTS")
    print("="*60)
    
    # Display costing results if requested
    if show_costing:
        display_costing_results(m)
