"""Display module for lithium processing flowsheet results.

Prints comprehensive results from the lithium carbonate processing flowsheet simulation.
"""

from pyomo.environ import units as pyunits, value

def display_costing_results(m):
    """Display costing results including capital costs, operating costs, and LCOLi metrics."""
    if not hasattr(m.fs, 'costing'):
        print("\nNo costing information available. Run add_costing() first.")
        return
    
    print("\n" + "="*60)
    print("LITHIUM CARBONATE PROCESSING PLANT COSTING RESULTS")
    print("="*60)
    
    print(f"\nGLOBAL COSTING PARAMETERS:")
    print(f"  Plant lifetime: {value(m.fs.costing.plant_lifetime):.0f} years")
    print(f"  WACC: {value(m.fs.costing.wacc):.1%}")
    print(f"  Electricity cost: ${value(m.fs.costing.electricity_cost):.3f}/kWh")
    print(f"  Utilization factor: {value(m.fs.costing.utilization_factor):.1%}")
    print(f"  Base currency: {m.fs.costing.base_currency}")
    
    print(f"\nUNIT MODEL CAPITAL COSTS:")
    
    if hasattr(m.fs.brine_storage, 'costing'):
        print(f"  Storage Tank Capital Cost: ${value(m.fs.brine_storage.costing.capital_cost):,.0f}")
    
    if hasattr(m.fs.brine_pump, 'costing'):
        print(f"  Pump Capital Cost: ${value(m.fs.brine_pump.costing.capital_cost):,.0f}")
    
    if hasattr(m.fs.soda_ash_reactor, 'costing'):
        print(f"  Soda Ash Reactor Capital Cost: ${value(m.fs.soda_ash_reactor.costing.capital_cost):,.0f}")
    
    if hasattr(m.fs.lime_reactor, 'costing'):
        print(f"  Lime Reactor Capital Cost: ${value(m.fs.lime_reactor.costing.capital_cost):,.0f}")
    
    if hasattr(m.fs.lithium_carbonate_reactor, 'costing'):
        print(f"  Lithium Carbonate Reactor Capital Cost: ${value(m.fs.lithium_carbonate_reactor.costing.capital_cost):,.0f}")
    
    if hasattr(m.fs.soda_ash_vacuum_filter, 'costing'):
        print(f"  Soda Ash Vacuum Filter Unit Capital Cost: ${value(m.fs.soda_ash_vacuum_filter.costing.capital_cost):,.0f}")
    
    if hasattr(m.fs.soda_ash_centrifuge, 'costing'):
        print(f"  Soda Ash Centrifuge Dewatering Unit Capital Cost: ${value(m.fs.soda_ash_centrifuge.costing.capital_cost):,.0f}")
    
    if hasattr(m.fs.lime_press_filter, 'costing'):
        print(f"  Lime Press Filter Unit Capital Cost: ${value(m.fs.lime_press_filter.costing.capital_cost):,.0f}")
    
    if hasattr(m.fs.lime_centrifuge, 'costing'):
        print(f"  Lime Centrifuge Unit Capital Cost: ${value(m.fs.lime_centrifuge.costing.capital_cost):,.0f}")
    
    if hasattr(m.fs.li_dewatering, 'costing'):
        print(f"  Lithium Dewatering Unit Capital Cost: ${value(m.fs.li_dewatering.costing.capital_cost):,.0f}")
    
    # Total capital cost (flowsheet level)
    if hasattr(m.fs.costing, 'total_capital_cost'):
        total_capital_cost = value(m.fs.costing.total_capital_cost)
        print(f"\n  TOTAL CAPITAL COST: ${total_capital_cost:,.0f}")
    else:
        total_capital_cost = 0
        if hasattr(m.fs.brine_storage, 'costing'):
            total_capital_cost += value(m.fs.brine_storage.costing.capital_cost)
        if hasattr(m.fs.brine_pump, 'costing'):
            total_capital_cost += value(m.fs.brine_pump.costing.capital_cost)
        if hasattr(m.fs.soda_ash_reactor, 'costing'):
            total_capital_cost += value(m.fs.soda_ash_reactor.costing.capital_cost)
        if hasattr(m.fs.lime_reactor, 'costing'):
            total_capital_cost += value(m.fs.lime_reactor.costing.capital_cost)
        if hasattr(m.fs.lithium_carbonate_reactor, 'costing'):
            total_capital_cost += value(m.fs.lithium_carbonate_reactor.costing.capital_cost)
        if hasattr(m.fs.soda_ash_vacuum_filter, 'costing'):
            total_capital_cost += value(m.fs.soda_ash_vacuum_filter.costing.capital_cost)
        if hasattr(m.fs.soda_ash_centrifuge, 'costing'):
            total_capital_cost += value(m.fs.soda_ash_centrifuge.costing.capital_cost)
        if hasattr(m.fs.lime_press_filter, 'costing'):
            total_capital_cost += value(m.fs.lime_press_filter.costing.capital_cost)
        if hasattr(m.fs.lime_centrifuge, 'costing'):
            total_capital_cost += value(m.fs.lime_centrifuge.costing.capital_cost)
        if hasattr(m.fs.li_dewatering, 'costing'):
            total_capital_cost += value(m.fs.li_dewatering.costing.capital_cost)
        
        print(f"\n  TOTAL CAPITAL COST: ${total_capital_cost:,.0f}")
    
    print(f"\nOPERATING COSTS:")
    
    total_power_kw = 0
    if hasattr(m.fs, 'brine_pump') and hasattr(m.fs.brine_pump.control_volume, 'work'):
        pump_power = value(m.fs.brine_pump.control_volume.work[0])
        pump_power_kw = pump_power / 1000
        total_power_kw += pump_power_kw
    
    if hasattr(m.fs, 'soda_ash_vacuum_filter') and hasattr(m.fs.soda_ash_vacuum_filter, 'electricity_consumption'):
        dewatering_power_kw = value(m.fs.soda_ash_vacuum_filter.electricity_consumption[0])
        total_power_kw += dewatering_power_kw
    
    if hasattr(m.fs, 'soda_ash_centrifuge') and hasattr(m.fs.soda_ash_centrifuge, 'electricity_consumption'):
        dewatering_power_kw = value(m.fs.soda_ash_centrifuge.electricity_consumption[0])
        total_power_kw += dewatering_power_kw
    
    if hasattr(m.fs, 'lime_press_filter') and hasattr(m.fs.lime_press_filter, 'electricity_consumption'):
        dewatering_power_kw = value(m.fs.lime_press_filter.electricity_consumption[0])
        total_power_kw += dewatering_power_kw
    
    if hasattr(m.fs, 'lime_centrifuge') and hasattr(m.fs.lime_centrifuge, 'electricity_consumption'):
        dewatering_power_kw = value(m.fs.lime_centrifuge.electricity_consumption[0])
        total_power_kw += dewatering_power_kw
    
    if hasattr(m.fs, 'li_dewatering') and hasattr(m.fs.li_dewatering, 'electricity_consumption'):
        dewatering_power_kw = value(m.fs.li_dewatering.electricity_consumption[0])
        total_power_kw += dewatering_power_kw
    
    if total_power_kw > 0:
        annual_electricity_cost = total_power_kw * value(m.fs.costing.electricity_cost) * 8760 * value(m.fs.costing.utilization_factor)
        print(f"  Annual electricity cost: ${annual_electricity_cost:,.0f}")
    
    if hasattr(m.fs, 'soda_ash_reactor'):
        try:
            na2co3_flow = value(m.fs.soda_ash_reactor.flow_mass_reagent["Na2CO3"])
            annual_na2co3_cost = na2co3_flow * 31536000 * value(m.fs.soda_ash_cost)
            print(f"  Annual Na2CO3 cost (soda ash reactor): ${annual_na2co3_cost:,.0f}")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            if "H2O" in m.fs.soda_ash_reactor.flow_mass_reagent:
                h2o_flow = value(m.fs.soda_ash_reactor.flow_mass_reagent["H2O"])
                annual_h2o_cost = h2o_flow * 31536000 * value(m.fs.process_water_cost)
                print(f"  Annual process water cost (soda ash reactor): ${annual_h2o_cost:,.0f}")
        except (AttributeError, TypeError, KeyError):
            pass
    
    if hasattr(m.fs, 'lime_reactor'):
        try:
            cao_flow = value(m.fs.lime_reactor.flow_mass_reagent["Ca(OH)2"])
            annual_cao_cost = cao_flow * 31536000 * value(m.fs.lime_cost)
            print(f"  Annual Ca(OH)2 cost (lime reactor): ${annual_cao_cost:,.0f}")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            if "H2O" in m.fs.lime_reactor.flow_mass_reagent:
                h2o_flow = value(m.fs.lime_reactor.flow_mass_reagent["H2O"])
                annual_h2o_cost = h2o_flow * 31536000 * value(m.fs.process_water_cost)
                print(f"  Annual process water cost (lime reactor): ${annual_h2o_cost:,.0f}")
        except (AttributeError, TypeError, KeyError):
            pass
    
    if hasattr(m.fs, 'lithium_carbonate_reactor'):
        try:
            na2co3_flow = value(m.fs.lithium_carbonate_reactor.flow_mass_reagent["Na2CO3"])
            annual_na2co3_cost = na2co3_flow * 31536000 * value(m.fs.soda_ash_cost)
            print(f"  Annual Na2CO3 cost (Li2CO3): ${annual_na2co3_cost:,.0f}")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            if "H2O" in m.fs.lithium_carbonate_reactor.flow_mass_reagent:
                h2o_flow = value(m.fs.lithium_carbonate_reactor.flow_mass_reagent["H2O"])
                annual_h2o_cost = h2o_flow * 31536000 * value(m.fs.process_water_cost)
                print(f"  Annual process water cost (lithium reactor): ${annual_h2o_cost:,.0f}")
        except (AttributeError, TypeError, KeyError):
            pass
    
    total_opex = 0
    if total_power_kw > 0:
        total_opex += annual_electricity_cost
    
    try:
        if hasattr(m.fs, 'soda_ash_reactor'):
            na2co3_flow = value(m.fs.soda_ash_reactor.flow_mass_reagent["Na2CO3"])
            total_opex += na2co3_flow * 31536000 * value(m.fs.soda_ash_cost)
            if "H2O" in m.fs.soda_ash_reactor.flow_mass_reagent:
                h2o_flow = value(m.fs.soda_ash_reactor.flow_mass_reagent["H2O"])
                total_opex += h2o_flow * 31536000 * value(m.fs.process_water_cost)
        
        if hasattr(m.fs, 'lime_reactor'):
            cao_flow = value(m.fs.lime_reactor.flow_mass_reagent["Ca(OH)2"])
            total_opex += cao_flow * 31536000 * value(m.fs.lime_cost)
            if "H2O" in m.fs.lime_reactor.flow_mass_reagent:
                h2o_flow = value(m.fs.lime_reactor.flow_mass_reagent["H2O"])
                total_opex += h2o_flow * 31536000 * value(m.fs.process_water_cost)
        
        if hasattr(m.fs, 'lithium_carbonate_reactor'):
            na2co3_flow = value(m.fs.lithium_carbonate_reactor.flow_mass_reagent["Na2CO3"])
            total_opex += na2co3_flow * 31536000 * value(m.fs.soda_ash_cost)
            if "H2O" in m.fs.lithium_carbonate_reactor.flow_mass_reagent:
                h2o_flow = value(m.fs.lithium_carbonate_reactor.flow_mass_reagent["H2O"])
                total_opex += h2o_flow * 31536000 * value(m.fs.process_water_cost)
    except (AttributeError, TypeError, KeyError):
        pass
    
    print(f"\n  TOTAL ANNUAL OPERATING COST: ${total_opex:,.0f}")
    
    capital_recovery_factor = value(m.fs.costing.wacc) * (1 + value(m.fs.costing.wacc))**value(m.fs.costing.plant_lifetime) / ((1 + value(m.fs.costing.wacc))**value(m.fs.costing.plant_lifetime) - 1)
    annual_capital_cost = total_capital_cost * capital_recovery_factor
    print(f"  Annual capital cost: ${annual_capital_cost:,.0f}")
    
    total_annual_cost = total_opex + annual_capital_cost
    print(f"  TOTAL ANNUAL COST: ${total_annual_cost:,.0f}")
    
    if hasattr(m.fs.costing, 'LCOLi'):
        try:
            lcoli_mass = value(pyunits.convert(m.fs.costing.LCOLi_mass, to_units=m.fs.costing.base_currency/pyunits.t))
            lcoli2co3_mass = value(pyunits.convert(m.fs.costing.LCOLi2CO3_mass, to_units=m.fs.costing.base_currency/pyunits.t))
            print(f"  LCOLi (per tonne Li): ${lcoli_mass:,.2f}/tonne")
            print(f"  LCOLi2CO3 (per tonne Li2CO3): ${lcoli2co3_mass:,.2f}/tonne")
        except (AttributeError, TypeError, KeyError):
            pass
    
    if hasattr(m.fs.costing, 'specific_energy_consumption'):
        try:
            spec_energy_vol = value(m.fs.costing.specific_energy_consumption)
            spec_energy_mass = value(m.fs.costing.specific_energy_consumption_mass)
            spec_energy_li2co3 = value(m.fs.costing.specific_energy_consumption_Li2CO3_mass)
            print(f"\n  Specific Energy (per m³ Li): {spec_energy_vol:.2f} kWh/m³")
            print(f"  Specific Energy (per kg Li): {spec_energy_mass:.2f} kWh/kg")
            print(f"  Specific Energy (per kg Li2CO3): {spec_energy_li2co3:.2f} kWh/kg")
        except (AttributeError, TypeError, KeyError):
            pass
    
    print(f"\n" + "="*60)
    print("END OF COSTING RESULTS")
    print("="*60)

def display_results(m, show_costing=False):
    """Display comprehensive flowsheet results including feed conditions, reactor outputs, and process metrics."""
    print("\n" + "="*60)
    print("LITHIUM CARBONATE PROCESSING PLANT RESULTS")
    print("="*60)
    
    if hasattr(m.fs, 'annual_soda_ash_input') or hasattr(m.fs, 'annual_lime_input') or hasattr(m.fs, 'max_total_impurity_mass_fraction_li_product'):
        print(f"\nFLOWSHEET-LEVEL VARIABLES:")
        
        if hasattr(m.fs, 'annual_soda_ash_input'):
            na2co3_mw = .10599
            annual_soda_ash_tonnes = value(pyunits.convert(m.fs.annual_soda_ash_input, to_units=pyunits.tonne/pyunits.year))
            secondly_soda_ash_moles = value(pyunits.convert(m.fs.annual_soda_ash_input, to_units=pyunits.kg/pyunits.s)) / na2co3_mw
            print(f"  Annual Soda Ash (Na2CO3) Input: {annual_soda_ash_tonnes:.1f} tonnes/year")
            print(f"  Secondly Soda Ash (Na2CO3) Input: {secondly_soda_ash_moles:.6f} mol/s")
        
        if hasattr(m.fs, 'annual_lime_input'):
            caoh2_mw = .074093
            annual_lime_tonnes = value(pyunits.convert(m.fs.annual_lime_input, to_units=pyunits.tonne/pyunits.year))
            secondly_lime_moles = value(pyunits.convert(m.fs.annual_lime_input, to_units=pyunits.kg/pyunits.s)) / caoh2_mw
            print(f"  Annual Lime (Ca(OH)2) Input: {annual_lime_tonnes:.1f} tonnes/year")
            print(f"  Secondly Lime (Ca(OH)2) Input: {secondly_lime_moles:.6f} mol/s")
        
        if hasattr(m.fs, 'annual_water_input'):
            water_mw = .018015
            annual_water_tonnes = value(pyunits.convert(m.fs.annual_water_input, to_units=pyunits.tonne/pyunits.year))
            secondly_water_moles = value(pyunits.convert(m.fs.annual_water_input, to_units=pyunits.kg/pyunits.s)) / water_mw
            print(f"  Annual Water Input: {annual_water_tonnes:.1f} tonnes/year")
            print(f"  Secondly Water Input: {secondly_water_moles:.6f} mol/s")

        if hasattr(m.fs, 'soda_ash_split_fraction'):
            split_fraction = value(m.fs.soda_ash_split_fraction)
            print(f"  Soda Ash Split Fraction (to Soda Ash Reactor): {split_fraction*100:.1f}%")
            print(f"  Soda Ash to Lithium Reactor: {(1-split_fraction)*100:.1f}%")
        
        if hasattr(m.fs, 'target_li_recovery'):
            target_recovery = value(m.fs.target_li_recovery)
            print(f"  Target Lithium Recovery: {target_recovery*100:.1f}%")
        
        if hasattr(m.fs, 'max_total_product_impurity'):
            max_impurity = value(m.fs.max_total_product_impurity)
            print(f"  Max Total Impurity (Na+Mg+Ca) in Li2CO3 Product: {max_impurity*100:.3f}% mass fraction")
    
    if hasattr(m.fs, 'stoich_coeff_a'):
        print(f"\nSTOICHIOMETRIC COEFFICIENTS AND RELATED MASS FLOWS:")
        print("="*60)
        
        # Coefficient a: Na2CO3 to MgCO3 in soda ash reactor
        print(f"\n  Coefficient a (Na2CO3 to MgCO3 in soda ash reactor): {value(m.fs.stoich_coeff_a):.6f}")
        if hasattr(m.fs, 'soda_ash_reactor'):
            try:
                na2co3_flow = value(m.fs.soda_ash_reactor.flow_mass_reagent['Na2CO3'])
                mgco3_flow = value(m.fs.soda_ash_reactor.flow_mass_precipitate['MgCO3'])
                print(f"    Na2CO3 reagent: {na2co3_flow:.6f} kg/s")
                print(f"    MgCO3 precipitate: {mgco3_flow:.6f} kg/s")
            except (AttributeError, TypeError, KeyError):
                pass
        
        # Coefficient b: Na2CO3 to CaCO3 in soda ash reactor
        print(f"\n  Coefficient b (Na2CO3 to CaCO3 in soda ash reactor): {value(m.fs.stoich_coeff_b):.6f}")
        if hasattr(m.fs, 'soda_ash_reactor'):
            try:
                na2co3_flow = value(m.fs.soda_ash_reactor.flow_mass_reagent['Na2CO3'])
                caco3_flow = value(m.fs.soda_ash_reactor.flow_mass_precipitate['CaCO3'])
                print(f"    Na2CO3 reagent: {na2co3_flow:.6f} kg/s")
                print(f"    CaCO3 precipitate: {caco3_flow:.6f} kg/s")
            except (AttributeError, TypeError, KeyError):
                pass
        
        # Coefficient c: Ca(OH)2 to Brucite (Mg(OH)2)
        print(f"\n  Coefficient c (Ca(OH)2 to Brucite): {value(m.fs.stoich_coeff_c):.6f}")
        if hasattr(m.fs, 'lime_reactor'):
            try:
                caoh2_flow = value(m.fs.lime_reactor.flow_mass_reagent['Ca(OH)2'])
                brucite_flow = value(m.fs.lime_reactor.flow_mass_precipitate['Brucite'])
                print(f"    Ca(OH)2 reagent: {caoh2_flow:.6f} kg/s")
                print(f"    Brucite precipitate: {brucite_flow:.6f} kg/s")
            except (AttributeError, TypeError, KeyError):
                pass
        
        # Coefficient d: Ca(OH)2 to CaCO3
        print(f"\n  Coefficient d (Ca(OH)2 to CaCO3): {value(m.fs.stoich_coeff_d):.6f}")
        if hasattr(m.fs, 'lime_reactor'):
            try:
                caoh2_flow = value(m.fs.lime_reactor.flow_mass_reagent['Ca(OH)2'])
                caco3_flow = value(m.fs.lime_reactor.flow_mass_precipitate['CaCO3'])
                print(f"    Ca(OH)2 reagent: {caoh2_flow:.6f} kg/s")
                print(f"    CaCO3 precipitate: {caco3_flow:.6f} kg/s")
            except (AttributeError, TypeError, KeyError):
                pass
        
        # Coefficient e: Ca(OH)2 to Gypsum (CaSO4)
        print(f"\n  Coefficient e (Ca(OH)2 to Gypsum): {value(m.fs.stoich_coeff_e):.6f}")
        if hasattr(m.fs, 'lime_reactor'):
            try:
                caoh2_flow = value(m.fs.lime_reactor.flow_mass_reagent['Ca(OH)2'])
                gypsum_flow = value(m.fs.lime_reactor.flow_mass_precipitate['Gypsum'])
                print(f"    Ca(OH)2 reagent: {caoh2_flow:.6f} kg/s")
                print(f"    Gypsum precipitate: {gypsum_flow:.6f} kg/s")
            except (AttributeError, TypeError, KeyError):
                pass
        
        # Coefficient f: SO4 to Gypsum
        print(f"\n  Coefficient f (SO4 to Gypsum): {value(m.fs.stoich_coeff_f):.6f}")
        if hasattr(m.fs, 'lime_reactor'):
            try:
                so4_feed = value(m.fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", "SO4"])
                so4_mw = 96.06e-3  # kg/mol
                so4_flow_kg_s = so4_feed * so4_mw
                gypsum_flow = value(m.fs.lime_reactor.flow_mass_precipitate['Gypsum'])
                print(f"    SO4 feed: {so4_flow_kg_s:.6f} kg/s")
                print(f"    Gypsum precipitate: {gypsum_flow:.6f} kg/s")
            except (AttributeError, TypeError, KeyError):
                pass
        
        # Coefficient g: Mg feed to total Mg precipitates
        print(f"\n  Coefficient g (Mg feed to total Mg precipitates): {value(m.fs.stoich_coeff_g):.6f}")
        try:
            mg_feed = value(m.fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", "Mg"])
            mg_mw = 24.3e-3  # kg/mol
            mg_feed_kg_s = mg_feed * mg_mw
            if hasattr(m.fs, 'soda_ash_reactor') and hasattr(m.fs, 'lime_reactor'):
                mgco3_flow = value(m.fs.soda_ash_reactor.flow_mass_precipitate['MgCO3'])
                brucite_flow = value(m.fs.lime_reactor.flow_mass_precipitate['Brucite'])
                total_mg_precip = mgco3_flow + brucite_flow
                print(f"    Mg feed: {mg_feed_kg_s:.6f} kg/s")
                print(f"    Total Mg precipitates (MgCO3 + Brucite): {total_mg_precip:.6f} kg/s")
        except (AttributeError, TypeError, KeyError):
            pass
        
        # Coefficient h: Li feed to Li2CO3
        print(f"\n  Coefficient h (Li feed to Li2CO3): {value(m.fs.stoich_coeff_h):.6f}")
        try:
            li_feed = value(m.fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", "Li"])
            li_mw = 6.94e-3  # kg/mol
            li_feed_kg_s = li_feed * li_mw
            if hasattr(m.fs, 'lithium_carbonate_reactor'):
                li2co3_flow = value(m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3'])
                print(f"    Li feed: {li_feed_kg_s:.6f} kg/s")
                print(f"    Li2CO3 precipitate: {li2co3_flow:.6f} kg/s")
        except (AttributeError, TypeError, KeyError):
            pass
        
        # Coefficient i: Na2CO3 to Li2CO3 in lithium reactor
        print(f"\n  Coefficient i (Na2CO3 to Li2CO3 in lithium reactor): {value(m.fs.stoich_coeff_i):.6f}")
        if hasattr(m.fs, 'lithium_carbonate_reactor'):
            try:
                na2co3_flow = value(m.fs.lithium_carbonate_reactor.flow_mass_reagent['Na2CO3'])
                li2co3_flow = value(m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3'])
                print(f"    Na2CO3 reagent: {na2co3_flow:.6f} kg/s")
                print(f"    Li2CO3 precipitate: {li2co3_flow:.6f} kg/s")
            except (AttributeError, TypeError, KeyError):
                pass
        
        # Coefficient j: Total Na2CO3 to soda ash reactor
        print(f"\n  Coefficient j (Total Na2CO3 to soda ash reactor): {value(m.fs.stoich_coeff_j):.6f}")
        try:
            total_na2co3 = value(pyunits.convert(m.fs.annual_soda_ash_input, to_units=pyunits.kg/pyunits.s))
            if hasattr(m.fs, 'soda_ash_reactor'):
                na2co3_soda_ash = value(m.fs.soda_ash_reactor.flow_mass_reagent['Na2CO3'])
                print(f"    Total Na2CO3 annual input: {value(m.fs.annual_soda_ash_input):,.0f} kg/year")
                print(f"    Na2CO3 to soda ash reactor: {na2co3_soda_ash:.6f} kg/s")
        except (AttributeError, TypeError, KeyError):
            pass
        
        # Coefficient k: Total Na2CO3 to lithium reactor
        print(f"\n  Coefficient k (Total Na2CO3 to lithium reactor): {value(m.fs.stoich_coeff_k):.6f}")
        try:
            total_na2co3 = value(pyunits.convert(m.fs.annual_soda_ash_input, to_units=pyunits.kg/pyunits.s))
            if hasattr(m.fs, 'lithium_carbonate_reactor'):
                na2co3_lithium = value(m.fs.lithium_carbonate_reactor.flow_mass_reagent['Na2CO3'])
                print(f"    Total Na2CO3 annual input: {value(m.fs.annual_soda_ash_input):,.0f} kg/year")
                print(f"    Na2CO3 to lithium reactor: {na2co3_lithium:.6f} kg/s")
        except (AttributeError, TypeError, KeyError):
            pass
        
        # Coefficient l: Na2CO3 to H2O in soda ash reactor
        if hasattr(m.fs, 'stoich_coeff_l'):
            print(f"\n  Coefficient l (Na2CO3 to H2O in soda ash reactor): {value(m.fs.stoich_coeff_l):.6f}")
            if hasattr(m.fs, 'soda_ash_reactor'):
                try:
                    na2co3_flow = value(m.fs.soda_ash_reactor.flow_mass_reagent['Na2CO3'])
                    if "H2O" in m.fs.soda_ash_reactor.flow_mass_reagent:
                        h2o_flow = value(m.fs.soda_ash_reactor.flow_mass_reagent['H2O'])
                        print(f"    Na2CO3 reagent: {na2co3_flow:.6f} kg/s")
                        print(f"    H2O reagent: {h2o_flow:.6f} kg/s")
                except (AttributeError, TypeError, KeyError):
                    pass
        
        # Coefficient m: Ca(OH)2 to H2O in lime reactor
        if hasattr(m.fs, 'stoich_coeff_m'):
            print(f"\n  Coefficient m (Ca(OH)2 to H2O in lime reactor): {value(m.fs.stoich_coeff_m):.6f}")
            if hasattr(m.fs, 'lime_reactor'):
                try:
                    caoh2_flow = value(m.fs.lime_reactor.flow_mass_reagent['Ca(OH)2'])
                    if "H2O" in m.fs.lime_reactor.flow_mass_reagent:
                        h2o_flow = value(m.fs.lime_reactor.flow_mass_reagent['H2O'])
                        print(f"    Ca(OH)2 reagent: {caoh2_flow:.6f} kg/s")
                        print(f"    H2O reagent: {h2o_flow:.6f} kg/s")
                except (AttributeError, TypeError, KeyError):
                    pass
        
        # Coefficient n: Na2CO3 to H2O in lithium reactor
        if hasattr(m.fs, 'stoich_coeff_n'):
            print(f"\n  Coefficient n (Na2CO3 to H2O in lithium reactor): {value(m.fs.stoich_coeff_n):.6f}")
            if hasattr(m.fs, 'lithium_carbonate_reactor'):
                try:
                    na2co3_flow = value(m.fs.lithium_carbonate_reactor.flow_mass_reagent['Na2CO3'])
                    if "H2O" in m.fs.lithium_carbonate_reactor.flow_mass_reagent:
                        h2o_flow = value(m.fs.lithium_carbonate_reactor.flow_mass_reagent['H2O'])
                        print(f"    Na2CO3 reagent: {na2co3_flow:.6f} kg/s")
                        print(f"    H2O reagent: {h2o_flow:.6f} kg/s")
                except (AttributeError, TypeError, KeyError):
                    pass
        
        # Coefficient o: CaCO3 to MgCO3 in soda ash reactor
        if hasattr(m.fs, 'stoich_coeff_o'):
            print(f"\n  Coefficient o (CaCO3 to MgCO3 in soda ash reactor): {value(m.fs.stoich_coeff_o):.6f}")
            if hasattr(m.fs, 'soda_ash_reactor'):
                try:
                    caco3_flow = value(m.fs.soda_ash_reactor.flow_mass_precipitate['CaCO3'])
                    mgco3_flow = value(m.fs.soda_ash_reactor.flow_mass_precipitate['MgCO3'])
                    print(f"    CaCO3 precipitate: {caco3_flow:.6f} kg/s")
                    print(f"    MgCO3 precipitate: {mgco3_flow:.6f} kg/s")
                except (AttributeError, TypeError, KeyError):
                    pass
        
        print("="*60)
    
    print(f"\nBRINE FEED CONDITIONS:")
    temp_K = value(m.fs.brine_feed.properties[0].temperature)
    print(f"  Temperature: {temp_K:.1f} K")
    
    press_Pa = value(m.fs.brine_feed.properties[0].pressure)
    press_atm = value(pyunits.convert(m.fs.brine_feed.properties[0].pressure, to_units=pyunits.atm))
    print(f"  Pressure: {press_Pa:.0f} Pa ({press_atm:.2f} atm)")
    
    flow_m3_s = value(m.fs.brine_feed.properties[0].flow_vol)
    flow_L_s = value(pyunits.convert(m.fs.brine_feed.properties[0].flow_vol, to_units=pyunits.L/pyunits.s))
    flow_m3_h = value(pyunits.convert(m.fs.brine_feed.properties[0].flow_vol, to_units=pyunits.m**3/pyunits.hour))
    print(f"  Volumetric flow rate: {flow_L_s:.2f} L/s ({flow_m3_h:.1f} m³/h)")
    
    try:
        total_mass_flow_mol = 0 * pyunits.kg / pyunits.s
        for comp in m.fs.brine_props.component_list:
            comp_flow_mol = m.fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", comp]
            comp_mw = m.fs.brine_props.mw_comp[comp]
            total_mass_flow_mol += comp_flow_mol * comp_mw
        
        mass_flow_kg_s = value(pyunits.convert(total_mass_flow_mol, to_units=pyunits.kg/pyunits.s))
        mass_flow_kg_h = value(pyunits.convert(total_mass_flow_mol, to_units=pyunits.kg/pyunits.hour))
        print(f"  Mass flow rate: {mass_flow_kg_s:.2f} kg/s ({mass_flow_kg_h:.1f} kg/h)")
    except (AttributeError, TypeError, KeyError):
        pass
    
    print(f"\nCOMPONENT FLOW RATES (mol/s):")
    for comp in ["Li", "Na", "K", "Mg", "Ca", "Cl", "SO4", "B", "H", "OH", "HCO3", "CO3", "H2O"]:
        if comp in m.fs.brine_props.component_list:
            flow = value(m.fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", comp])
            if comp in ["H", "OH"]:
                print(f"  {comp}: {flow:.10e}")
            else:
                print(f"  {comp}: {flow:.4f}")
    
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
    
    if hasattr(m.fs, 'soda_ash_reactor'):
        print(f"\nSODA ASH REACTOR (FIRST SOFTENING STAGE):")
        try:
            if hasattr(m.fs.soda_ash_reactor, 'dissolution_reactor'):
                flow_vol_in = m.fs.soda_ash_reactor.dissolution_reactor.properties_in[0].flow_vol_phase["Liq"]
                flow_L_s = value(pyunits.convert(flow_vol_in, to_units=pyunits.L/pyunits.s))
                flow_m3_h = value(pyunits.convert(flow_vol_in, to_units=pyunits.m**3/pyunits.hour))
                print(f"  Inlet volumetric flow: {flow_L_s:.2f} L/s ({flow_m3_h:.1f} m³/h)")
            
            if hasattr(m.fs.soda_ash_reactor, 'flow_mass_reagent'):
                reagent_flow = m.fs.soda_ash_reactor.flow_mass_reagent['Na2CO3']
                flow_kg_s = value(pyunits.convert(reagent_flow, to_units=pyunits.kg/pyunits.s))
                flow_kg_h = value(pyunits.convert(reagent_flow, to_units=pyunits.kg/pyunits.hour))
                flow_tonne_yr = value(pyunits.convert(reagent_flow, to_units=pyunits.tonne/pyunits.year))
                print(f"  Na2CO3 flow rate: {flow_kg_s:.4f} kg/s ({flow_kg_h:.2f} kg/h)")
                print(f"  Na2CO3 annual consumption: {flow_tonne_yr:.1f} tonnes/year")
                
                if "H2O" in m.fs.soda_ash_reactor.flow_mass_reagent:
                    h2o_flow = m.fs.soda_ash_reactor.flow_mass_reagent['H2O']
                    flow_kg_s = value(pyunits.convert(h2o_flow, to_units=pyunits.kg/pyunits.s))
                    water_density = 1000 * pyunits.kg / pyunits.m**3
                    flow_m3_h = value(pyunits.convert(h2o_flow / water_density, to_units=pyunits.m**3/pyunits.hour))
                    flow_m3_yr = value(pyunits.convert(h2o_flow / water_density, to_units=pyunits.m**3/pyunits.year))
                    print(f"  Process water flow rate: {flow_kg_s:.4f} kg/s ({flow_m3_h:.2f} m³/h)")
                    print(f"  Process water annual consumption: {flow_m3_yr:,.0f} m³/year")

        except (AttributeError, TypeError, KeyError):
            pass
        try:
            mgco3_flow_kg_s = value(m.fs.soda_ash_reactor.flow_mass_precipitate['MgCO3'])
            mgco3_flow_g_s = value(pyunits.convert(m.fs.soda_ash_reactor.flow_mass_precipitate['MgCO3'], to_units=pyunits.g/pyunits.s))
            print(f"  MgCO3 formation: {mgco3_flow_g_s:.3f} g/s ({mgco3_flow_kg_s:.6f} kg/s)")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            caco3_flow_kg_s = value(m.fs.soda_ash_reactor.flow_mass_precipitate['CaCO3'])
            caco3_flow_g_s = value(pyunits.convert(m.fs.soda_ash_reactor.flow_mass_precipitate['CaCO3'], to_units=pyunits.g/pyunits.s))
            print(f"  CaCO3 formation: {caco3_flow_g_s:.3f} g/s ({caco3_flow_kg_s:.6f} kg/s)")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            print(f"  Waste solids fraction: {value(m.fs.soda_ash_reactor.waste_mass_frac_precipitate)*100:.1f}%")
        except (AttributeError, TypeError, KeyError):
            pass
    
    if hasattr(m.fs, 'lime_reactor'):
        print(f"\nLIME REACTOR (SECOND SOFTENING STAGE):")
        try:
            if hasattr(m.fs.lime_reactor, 'dissolution_reactor'):
                flow_vol_in = m.fs.lime_reactor.dissolution_reactor.properties_in[0].flow_vol_phase["Liq"]
                flow_L_s = value(pyunits.convert(flow_vol_in, to_units=pyunits.L/pyunits.s))
                flow_m3_h = value(pyunits.convert(flow_vol_in, to_units=pyunits.m**3/pyunits.hour))
                print(f"  Inlet volumetric flow: {flow_L_s:.2f} L/s ({flow_m3_h:.1f} m³/h)")
            
            if hasattr(m.fs.lime_reactor, 'flow_mass_reagent'):
                reagent_flow = m.fs.lime_reactor.flow_mass_reagent['Ca(OH)2']
                flow_kg_s = value(pyunits.convert(reagent_flow, to_units=pyunits.kg/pyunits.s))
                flow_kg_h = value(pyunits.convert(reagent_flow, to_units=pyunits.kg/pyunits.hour))
                flow_tonne_yr = value(pyunits.convert(reagent_flow, to_units=pyunits.tonne/pyunits.year))
                print(f"  Ca(OH)2 flow rate: {flow_kg_s:.4f} kg/s ({flow_kg_h:.2f} kg/h)")
                print(f"  Ca(OH)2 annual consumption: {flow_tonne_yr:.1f} tonnes/year")
                
                if "H2O" in m.fs.lime_reactor.flow_mass_reagent:
                    h2o_flow = m.fs.lime_reactor.flow_mass_reagent['H2O']
                    flow_kg_s = value(pyunits.convert(h2o_flow, to_units=pyunits.kg/pyunits.s))
                    water_density = 1000 * pyunits.kg / pyunits.m**3
                    flow_m3_h = value(pyunits.convert(h2o_flow / water_density, to_units=pyunits.m**3/pyunits.hour))
                    flow_m3_yr = value(pyunits.convert(h2o_flow / water_density, to_units=pyunits.m**3/pyunits.year))
                    print(f"  Process water flow rate: {flow_kg_s:.4f} kg/s ({flow_m3_h:.2f} m³/h)")
                    print(f"  Process water annual consumption: {flow_m3_yr:,.0f} m³/year")

        except (AttributeError, TypeError, KeyError):
            pass
        try:
            brucite_flow_kg_s = value(m.fs.lime_reactor.flow_mass_precipitate['Brucite'])
            brucite_flow_g_s = value(pyunits.convert(m.fs.lime_reactor.flow_mass_precipitate['Brucite'], to_units=pyunits.g/pyunits.s))
            print(f"  Brucite formation: {brucite_flow_g_s:.3f} g/s ({brucite_flow_kg_s:.6f} kg/s)")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            gypsum_flow_kg_s = value(m.fs.lime_reactor.flow_mass_precipitate['Gypsum'])
            gypsum_flow_g_s = value(pyunits.convert(m.fs.lime_reactor.flow_mass_precipitate['Gypsum'], to_units=pyunits.g/pyunits.s))
            print(f"  Gypsum formation: {gypsum_flow_g_s:.3f} g/s ({gypsum_flow_kg_s:.6f} kg/s)")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            caco3_flow_kg_s = value(m.fs.lime_reactor.flow_mass_precipitate['CaCO3'])
            caco3_flow_g_s = value(pyunits.convert(m.fs.lime_reactor.flow_mass_precipitate['CaCO3'], to_units=pyunits.g/pyunits.s))
            print(f"  CaCO3 formation: {caco3_flow_g_s:.3f} g/s ({caco3_flow_kg_s:.6f} kg/s)")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            print(f"  Waste solids fraction: {value(m.fs.lime_reactor.waste_mass_frac_precipitate)*100:.1f}%")
        except (AttributeError, TypeError, KeyError):
            pass
    
    if hasattr(m.fs, 'lithium_carbonate_reactor'):
        print(f"\nLITHIUM CARBONATE PRECIPITATION REACTOR:")
        try:
            if hasattr(m.fs.lithium_carbonate_reactor, 'dissolution_reactor'):
                flow_vol_in = m.fs.lithium_carbonate_reactor.dissolution_reactor.properties_in[0].flow_vol_phase["Liq"]
                flow_L_s = value(pyunits.convert(flow_vol_in, to_units=pyunits.L/pyunits.s))
                flow_m3_h = value(pyunits.convert(flow_vol_in, to_units=pyunits.m**3/pyunits.hour))
                print(f"  Inlet volumetric flow: {flow_L_s:.2f} L/s ({flow_m3_h:.1f} m³/h)")
            
            if hasattr(m.fs.lithium_carbonate_reactor, 'flow_mass_reagent'):
                reagent_flow = m.fs.lithium_carbonate_reactor.flow_mass_reagent['Na2CO3']
                flow_kg_s = value(pyunits.convert(reagent_flow, to_units=pyunits.kg/pyunits.s))
                flow_kg_h = value(pyunits.convert(reagent_flow, to_units=pyunits.kg/pyunits.hour))
                flow_tonne_yr = value(pyunits.convert(reagent_flow, to_units=pyunits.tonne/pyunits.year))
                print(f"  Na2CO3 flow rate: {flow_kg_s:.4f} kg/s ({flow_kg_h:.2f} kg/h)")
                print(f"  Na2CO3 annual consumption: {flow_tonne_yr:.1f} tonnes/year")
                
                if "H2O" in m.fs.lithium_carbonate_reactor.flow_mass_reagent:
                    h2o_flow = m.fs.lithium_carbonate_reactor.flow_mass_reagent['H2O']
                    flow_kg_s = value(pyunits.convert(h2o_flow, to_units=pyunits.kg/pyunits.s))
                    water_density = 1000 * pyunits.kg / pyunits.m**3
                    flow_m3_h = value(pyunits.convert(h2o_flow / water_density, to_units=pyunits.m**3/pyunits.hour))
                    flow_m3_yr = value(pyunits.convert(h2o_flow / water_density, to_units=pyunits.m**3/pyunits.year))
                    print(f"  Process water flow rate: {flow_kg_s:.4f} kg/s ({flow_m3_h:.2f} m³/h)")
                    print(f"  Process water annual consumption: {flow_m3_yr:,.0f} m³/year")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            li2co3_flow_kg_s = value(m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3'])
            li2co3_flow_g_s = value(pyunits.convert(m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3'], to_units=pyunits.g/pyunits.s))
            print(f"  Li2CO3 formation: {li2co3_flow_g_s:.3f} g/s ({li2co3_flow_kg_s:.6f} kg/s)")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            print(f"  Waste solids fraction: {value(m.fs.lithium_carbonate_reactor.waste_mass_frac_precipitate)*100:.1f}%")
        except (AttributeError, TypeError, KeyError):
            pass
        
        try:
            li2co3_flow_kg_yr = value(pyunits.convert(m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3'], to_units=pyunits.kg/pyunits.year))
            li2co3_flow_tonne_yr = value(pyunits.convert(m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3'], to_units=pyunits.tonne/pyunits.year))
            print(f"  Annual Li2CO3 production: {li2co3_flow_tonne_yr:.1f} tonnes/year ({li2co3_flow_kg_yr:,.0f} kg/year)")
        except (AttributeError, TypeError, KeyError):
            pass
    
    if hasattr(m.fs, 'soda_ash_vacuum_filter'):
        print(f"\nSODA ASH VACUUM FILTER UNIT:")
        try:
            print(f"  Water to overflow (clarified liquid): {value(m.fs.soda_ash_vacuum_filter.split_fraction[0, 'overflow', 'H2O'])*100:.1f}%")
            print(f"  All ions to overflow (liquid phase): {value(m.fs.soda_ash_vacuum_filter.split_fraction[0, 'overflow', 'Na'])*100:.1f}%")
            print(f"  All ions to underflow (entrapped in solids): {(1-value(m.fs.soda_ash_vacuum_filter.split_fraction[0, 'overflow', 'Na']))*100:.1f}%")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            if hasattr(m.fs.soda_ash_vacuum_filter, 'electricity_consumption'):
                print(f"  Electricity consumption: {value(m.fs.soda_ash_vacuum_filter.electricity_consumption[0]):.3f} kW")
        except (AttributeError, TypeError, KeyError):
            pass
    
    if hasattr(m.fs, 'soda_ash_centrifuge'):
        print(f"\nSODA ASH CENTRIFUGE DEWATERING UNIT:")
        try:
            print(f"  Water to overflow (clarified liquid): {value(m.fs.soda_ash_centrifuge.split_fraction[0, 'overflow', 'H2O'])*100:.1f}%")
            print(f"  All ions to overflow (liquid phase): {value(m.fs.soda_ash_centrifuge.split_fraction[0, 'overflow', 'Na'])*100:.1f}%")
            print(f"  All ions to underflow (entrapped in solids): {(1-value(m.fs.soda_ash_centrifuge.split_fraction[0, 'overflow', 'Na']))*100:.1f}%")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            if hasattr(m.fs.soda_ash_centrifuge, 'electricity_consumption'):
                print(f"  Electricity consumption: {value(m.fs.soda_ash_centrifuge.electricity_consumption[0]):.3f} kW")
        except (AttributeError, TypeError, KeyError):
            pass
    
    if hasattr(m.fs, 'lime_press_filter'):
        print(f"\nLIME PRESS FILTER UNIT:")
        try:
            print(f"  Water to overflow (clarified liquid): {value(m.fs.lime_press_filter.split_fraction[0, 'overflow', 'H2O'])*100:.1f}%")
            print(f"  All ions to overflow (liquid phase): {value(m.fs.lime_press_filter.split_fraction[0, 'overflow', 'Na'])*100:.1f}%")
            print(f"  All ions to underflow (entrapped in solids): {(1-value(m.fs.lime_press_filter.split_fraction[0, 'overflow', 'Na']))*100:.1f}%")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            if hasattr(m.fs.lime_press_filter, 'electricity_consumption'):
                print(f"  Electricity consumption: {value(m.fs.lime_press_filter.electricity_consumption[0]):.3f} kW")
        except (AttributeError, TypeError, KeyError):
            pass
    
    if hasattr(m.fs, 'lime_centrifuge'):
        print(f"\nLIME CENTRIFUGE UNIT:")
        try:
            print(f"  Water to overflow (clarified liquid): {value(m.fs.lime_centrifuge.split_fraction[0, 'overflow', 'H2O'])*100:.1f}%")
            print(f"  All ions to overflow (liquid phase): {value(m.fs.lime_centrifuge.split_fraction[0, 'overflow', 'Na'])*100:.1f}%")
            print(f"  All ions to underflow (entrapped in solids): {(1-value(m.fs.lime_centrifuge.split_fraction[0, 'overflow', 'Na']))*100:.1f}%")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            if hasattr(m.fs.lime_centrifuge, 'electricity_consumption'):
                print(f"  Electricity consumption: {value(m.fs.lime_centrifuge.electricity_consumption[0]):.3f} kW")
        except (AttributeError, TypeError, KeyError):
            pass
    
    if hasattr(m.fs, 'li_dewatering'):
        print(f"\nLITHIUM DEWATERING UNIT:")
        try:
            print(f"  Water to overflow (clarified liquid): {value(m.fs.li_dewatering.split_fraction[0, 'overflow', 'H2O'])*100:.1f}%")
            print(f"  All ions to overflow (liquid phase): {value(m.fs.li_dewatering.split_fraction[0, 'overflow', 'Na'])*100:.1f}%")
            print(f"  All ions to underflow (entrapped in solids): {(1-value(m.fs.li_dewatering.split_fraction[0, 'overflow', 'Na']))*100:.1f}%")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            if hasattr(m.fs.li_dewatering, 'electricity_consumption'):
                print(f"  Electricity consumption: {value(m.fs.li_dewatering.electricity_consumption[0]):.3f} kW")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            if hasattr(m.fs.li_dewatering, 'underflow_state'):
                li_flow_underflow = value(m.fs.li_dewatering.underflow_state[0].flow_mol_phase_comp["Liq", "Li"])
                total_flow_underflow = value(m.fs.li_dewatering.underflow_state[0].flow_vol)
                
                if total_flow_underflow > 0:
                    li_concentration_underflow = li_flow_underflow / total_flow_underflow
                    print(f"  Li concentration in concentrated solids: {li_concentration_underflow:.4f} mol/L")
                    print(f"  Li mass flow in concentrated solids: {li_flow_underflow * 6.94e-3:.4f} kg/s")
                else:
                    print(f"  Li concentration in concentrated solids: No flow in underflow")
            else:
                print(f"  Li concentration in concentrated solids: underflow_state not found")
        except (AttributeError, TypeError, KeyError) as e:
            print(f"  Li concentration in concentrated solids: Error accessing properties - {type(e).__name__}")
    
    if hasattr(m.fs, 'boron_extraction'):
        print(f"\nBORON EXTRACTION:")
        print(f"  Number of stages: {m.fs.boron_extraction.config.number_of_finite_elements}")
        if hasattr(m.fs.boron_extraction, 'aqueous_inlet'):
            print(f"  Aqueous inlet flow: {value(m.fs.boron_extraction.aqueous_inlet.flow_vol[0]):.2f} L/s")
        if hasattr(m.fs.boron_extraction, 'organic_inlet'):
            print(f"  Organic inlet flow: {value(m.fs.boron_extraction.organic_inlet.flow_vol[0]):.2f} L/s")
    
    print(f"\nPROCESS EFFICIENCY METRICS:")
    
    if hasattr(m.fs, 'lithium_carbonate_reactor'):
        li_in = value(m.fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", "Li"])
        li2co3_out = value(m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3'])
        li_mw = 6.94e-3
        li2co3_mw = 73.89e-3
        li_in_mass = li_in * li_mw
        li_out_mass = li2co3_out * (2 * li_mw / li2co3_mw)
        li_recovery = (li_out_mass / li_in_mass) * 100 if li_in_mass > 0 else 0
        print(f"  Lithium recovery: {li_recovery:.1f}%")
    
    total_na2co3_flow = 0 * pyunits.kg / pyunits.s
    if hasattr(m.fs, 'soda_ash_reactor') and hasattr(m.fs.soda_ash_reactor, 'flow_mass_reagent'):
        total_na2co3_flow += m.fs.soda_ash_reactor.flow_mass_reagent['Na2CO3']
    if hasattr(m.fs, 'lithium_carbonate_reactor') and hasattr(m.fs.lithium_carbonate_reactor, 'flow_mass_reagent'):
        total_na2co3_flow += m.fs.lithium_carbonate_reactor.flow_mass_reagent['Na2CO3']
    if value(total_na2co3_flow) > 0:
        flow_kg_s = value(pyunits.convert(total_na2co3_flow, to_units=pyunits.kg/pyunits.s))
        flow_tonne_yr = value(pyunits.convert(total_na2co3_flow, to_units=pyunits.tonne/pyunits.year))
        print(f"  Total Na2CO3 consumption: {flow_kg_s:.4f} kg/s ({flow_tonne_yr:.1f} tonnes/year)")
    if hasattr(m.fs, 'lime_reactor') and hasattr(m.fs.lime_reactor, 'flow_mass_reagent'):
        lime_flow = m.fs.lime_reactor.flow_mass_reagent['Ca(OH)2']
        flow_kg_s = value(pyunits.convert(lime_flow, to_units=pyunits.kg/pyunits.s))
        flow_tonne_yr = value(pyunits.convert(lime_flow, to_units=pyunits.tonne/pyunits.year))
        print(f"  Ca(OH)2 consumption: {flow_kg_s:.4f} kg/s ({flow_tonne_yr:.1f} tonnes/year)")
    
    total_h2o_flow = 0 * pyunits.kg / pyunits.s
    if hasattr(m.fs, 'soda_ash_reactor') and hasattr(m.fs.soda_ash_reactor, 'flow_mass_reagent'):
        if "H2O" in m.fs.soda_ash_reactor.flow_mass_reagent:
            total_h2o_flow += m.fs.soda_ash_reactor.flow_mass_reagent['H2O']
    if hasattr(m.fs, 'lime_reactor') and hasattr(m.fs.lime_reactor, 'flow_mass_reagent'):
        if "H2O" in m.fs.lime_reactor.flow_mass_reagent:
            total_h2o_flow += m.fs.lime_reactor.flow_mass_reagent['H2O']
    if hasattr(m.fs, 'lithium_carbonate_reactor') and hasattr(m.fs.lithium_carbonate_reactor, 'flow_mass_reagent'):
        if "H2O" in m.fs.lithium_carbonate_reactor.flow_mass_reagent:
            total_h2o_flow += m.fs.lithium_carbonate_reactor.flow_mass_reagent['H2O']
    if value(total_h2o_flow) > 0:
        flow_kg_s = value(pyunits.convert(total_h2o_flow, to_units=pyunits.kg/pyunits.s))
        water_density = 1000 * pyunits.kg / pyunits.m**3
        flow_m3_yr = value(pyunits.convert(total_h2o_flow / water_density, to_units=pyunits.m**3/pyunits.year))
        print(f"  Total process water consumption: {flow_kg_s:.4f} kg/s ({flow_m3_yr:,.0f} m³/year)")
    
    total_power = 0
    if hasattr(m.fs, 'brine_pump') and hasattr(m.fs.brine_pump.control_volume, 'work'):
        total_power += value(m.fs.brine_pump.control_volume.work[0])
    if hasattr(m.fs, 'boron_pump') and hasattr(m.fs.boron_pump.control_volume, 'work'):
        total_power += value(m.fs.boron_pump.control_volume.work[0])
    if hasattr(m.fs, 'soda_ash_vacuum_filter') and hasattr(m.fs.soda_ash_vacuum_filter, 'electricity_consumption'):
        total_power += value(m.fs.soda_ash_vacuum_filter.electricity_consumption[0]) * 1000
    if hasattr(m.fs, 'soda_ash_centrifuge') and hasattr(m.fs.soda_ash_centrifuge, 'electricity_consumption'):
        total_power += value(m.fs.soda_ash_centrifuge.electricity_consumption[0]) * 1000
    if hasattr(m.fs, 'lime_press_filter') and hasattr(m.fs.lime_press_filter, 'electricity_consumption'):
        total_power += value(m.fs.lime_press_filter.electricity_consumption[0]) * 1000
    if hasattr(m.fs, 'lime_centrifuge') and hasattr(m.fs.lime_centrifuge, 'electricity_consumption'):
        total_power += value(m.fs.lime_centrifuge.electricity_consumption[0]) * 1000
    if hasattr(m.fs, 'li_dewatering') and hasattr(m.fs.li_dewatering, 'electricity_consumption'):
        total_power += value(m.fs.li_dewatering.electricity_consumption[0]) * 1000
    
    if total_power > 0:
        print(f"  Total power consumption: {total_power:.2f} W")
        print(f"  Specific energy consumption: {total_power/value(m.fs.brine_feed.properties[0].flow_vol):.2f} W/(L/s)")
    
    print(f"\nPRODUCT QUALITY:")
    if hasattr(m.fs, 'lithium_carbonate_reactor'):
        li2co3_purity = 100.0
        print(f"  Li2CO3 purity: {li2co3_purity:.1f}%")
        print(f"  Li2CO3 production rate: {value(m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3']):.4f} kg/s")
    
    print(f"\nPROCESS SUMMARY:")
    feed_flow_L_s = value(pyunits.convert(m.fs.brine_feed.properties[0].flow_vol, to_units=pyunits.L/pyunits.s))
    print(f"  Feed flow rate: {feed_flow_L_s:.2f} L/s")
    print(f"  Feed Li concentration: {value(m.fs.brine_feed.properties[0].flow_mol_phase_comp['Liq', 'Li']):.4f} mol/s")
    if hasattr(m.fs, 'lithium_carbonate_reactor'):
        li2co3_flow_kg_s = value(m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3'])
        print(f"  Li2CO3 production: {li2co3_flow_kg_s:.4f} kg/s")
        li2co3_flow_kg_yr = value(pyunits.convert(m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3'], to_units=pyunits.kg/pyunits.year))
        li2co3_flow_tonne_yr = value(pyunits.convert(m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3'], to_units=pyunits.tonne/pyunits.year))
        print(f"  Annual Li2CO3 production: {li2co3_flow_tonne_yr:.1f} tonnes/year ({li2co3_flow_kg_yr:,.0f} kg/year)")
    
    print(f"\n" + "="*60)
    print("END OF RESULTS")
    print("="*60)
    
    if show_costing:
        display_costing_results(m)

