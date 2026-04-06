"""Display module for lithium processing flowsheet results.

Costing output includes the softening waste Product block when present: capital
follows ``costing_parameters.yaml`` → ``waste_handling`` (fixed + per metric
tonne dry salt/s, after TIC; dry salt = non-H2O liquid mass), and variable OPEX
uses the ``waste_handling`` flow type at $/dry metric tonne of salt (stored as $/kg dry salt).
"""

from math import log
from pyomo.environ import units as pyunits, value


_MW = {
    "Li": 6.941e-3, "Na": 22.990e-3, "K": 39.098e-3, "Mg": 24.305e-3,
    "Ca": 40.078e-3, "Cl": 35.453e-3, "SO4": 96.06e-3, "B": 10.811e-3,
    "H2O": 18.015e-3, "H": 1.008e-3, "OH": 17.008e-3,
    "HCO3": 61.016e-3, "CO3": 60.009e-3,
}


def _total_mass_flow(state):
    """Return total mass flow in kg/s from an MCAS state block, or None on failure."""
    try:
        total = 0.0
        for (phase, comp), var in state.flow_mol_phase_comp.items():
            mw = _MW.get(comp)
            if mw is not None:
                total += value(var) * mw
        return total if total > 0 else None
    except Exception:
        return None


def _stream_summary(state, indent="  "):
    """Print Li/Mg/Ca concentrations (mol/L, mg/L, wt%) and volumetric flow for any MCAS state block."""
    # Compute shared quantities once
    fv_L_s = None
    try:
        try:
            fv_L_s = value(pyunits.convert(state.flow_vol, to_units=pyunits.L / pyunits.s))
            fv_m3_h = value(pyunits.convert(state.flow_vol, to_units=pyunits.m**3 / pyunits.hour))
        except Exception:
            fv_L_s = value(pyunits.convert(state.flow_vol_phase["Liq"], to_units=pyunits.L / pyunits.s))
            fv_m3_h = value(pyunits.convert(state.flow_vol_phase["Liq"], to_units=pyunits.m**3 / pyunits.hour))
        print(f"{indent}Volumetric flow: {fv_L_s:.3f} L/s ({fv_m3_h:.1f} m³/h)")
    except Exception:
        pass

    total_mass = _total_mass_flow(state)

    for comp in ["Li", "Na", "Mg", "Ca"]:
        try:
            mol_s = value(state.flow_mol_phase_comp["Liq", comp])
            parts = []
            if fv_L_s is not None and fv_L_s > 0:
                conc_mol_L = mol_s / fv_L_s
                mg_L = conc_mol_L * _MW[comp] * 1e6
                parts.append(f"{conc_mol_L:.4f} mol/L")
                parts.append(f"{mg_L:.1f} mg/L")
            if total_mass is not None:
                wt_pct = mol_s * _MW[comp] / total_mass * 100
                parts.append(f"{wt_pct:.4f} wt%")
            conc_str = "  |  ".join(parts)
            print(f"{indent}{comp}: {conc_str}  [{mol_s:.4f} mol/s]")
        except Exception:
            pass

def display_costing_results(m):
    """Display costing results including capital costs, operating costs, LCOLi metrics, and softening waste handling."""
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
    if hasattr(m.fs.costing, "waste_handling"):
        try:
            wh = m.fs.costing.waste_handling
            cf = value(wh.capital_fixed_usd)
            cp = value(wh.capital_usd_per_dry_metric_ton_salt_rate)
            print(f"  Waste handling (capital correlation on fs.softening_waste):")
            print(f"    capital_cost = TIC * (capital_fixed_usd + capital_usd_per_dry_metric_ton_salt_rate * ṁ_dry)")
            _wn = getattr(m.fs, "waste_handling_water_component_name", "H2O")
            print(f"    ṁ_dry = inlet liquid mass flow excluding {_wn} [metric tonne dry salt / s]")
            print(f"    capital_fixed_usd: ${cf:,.0f}")
            print(f"    capital_usd_per_dry_metric_ton_salt_rate: ${cp:,.0f} per (metric tonne dry salt / s)")
        except (AttributeError, TypeError, ValueError):
            pass
    if hasattr(m.fs, "waste_handling_cost"):
        try:
            usd_per_kg = value(m.fs.waste_handling_cost)
            print(f"  Waste handling (variable OPEX): ${usd_per_kg * 1000:.2f}/dry metric tonne salt (${usd_per_kg:.5f}/kg dry salt; cost_flow type 'waste_handling')")
        except (AttributeError, TypeError, ValueError):
            pass
    
    print(f"\nUNIT MODEL CAPITAL COSTS:")
    
    if hasattr(m.fs, 'brine_storage') and hasattr(m.fs.brine_storage, 'costing'):
        print(f"  Storage Tank Capital Cost: ${value(m.fs.brine_storage.costing.capital_cost):,.0f}")
    
    if hasattr(m.fs, 'brine_pump') and hasattr(m.fs.brine_pump, 'costing'):
        print(f"  Brine Pump Capital Cost: ${value(m.fs.brine_pump.costing.capital_cost):,.0f}")
    
    if hasattr(m.fs, 'second_pump') and hasattr(m.fs.second_pump, 'costing'):
        print(f"  Second Pump Capital Cost: ${value(m.fs.second_pump.costing.capital_cost):,.0f}")
    
    if hasattr(m.fs, 'soda_ash_reactor') and hasattr(m.fs.soda_ash_reactor, 'costing'):
        print(f"  Soda Ash Reactor Capital Cost: ${value(m.fs.soda_ash_reactor.costing.capital_cost):,.0f}")
    
    if hasattr(m.fs, 'lime_reactor') and hasattr(m.fs.lime_reactor, 'costing'):
        print(f"  Lime Reactor Capital Cost: ${value(m.fs.lime_reactor.costing.capital_cost):,.0f}")
    
    if hasattr(m.fs, 'lithium_carbonate_reactor') and hasattr(m.fs.lithium_carbonate_reactor, 'costing'):
        print(f"  Lithium Carbonate Reactor Capital Cost: ${value(m.fs.lithium_carbonate_reactor.costing.capital_cost):,.0f}")
    
    if hasattr(m.fs, 'soda_ash_vacuum_filter') and hasattr(m.fs.soda_ash_vacuum_filter, 'costing'):
        print(f"  Soda Ash Vacuum Filter Unit Capital Cost: ${value(m.fs.soda_ash_vacuum_filter.costing.capital_cost):,.0f}")
    
    if hasattr(m.fs, 'soda_ash_centrifuge') and hasattr(m.fs.soda_ash_centrifuge, 'costing'):
        print(f"  Soda Ash Centrifuge Dewatering Unit Capital Cost: ${value(m.fs.soda_ash_centrifuge.costing.capital_cost):,.0f}")
    
    if hasattr(m.fs, 'lime_press_filter') and hasattr(m.fs.lime_press_filter, 'costing'):
        print(f"  Lime Press Filter Unit Capital Cost: ${value(m.fs.lime_press_filter.costing.capital_cost):,.0f}")
    
    if hasattr(m.fs, 'lime_centrifuge') and hasattr(m.fs.lime_centrifuge, 'costing'):
        print(f"  Lime Centrifuge Unit Capital Cost: ${value(m.fs.lime_centrifuge.costing.capital_cost):,.0f}")
    
    if hasattr(m.fs, 'li_dewatering') and hasattr(m.fs.li_dewatering, 'costing'):
        print(f"  Lithium Dewatering Unit Capital Cost: ${value(m.fs.li_dewatering.costing.capital_cost):,.0f}")
    
    if hasattr(m.fs, 'softening_waste') and hasattr(m.fs.softening_waste, 'costing'):
        print(f"  Softening Waste Product (waste handling) Capital Cost: ${value(m.fs.softening_waste.costing.capital_cost):,.0f}")
    
    # Total capital cost (flowsheet level)
    if hasattr(m.fs.costing, 'total_capital_cost'):
        total_capital_cost = value(m.fs.costing.total_capital_cost)
        print(f"\n  TOTAL CAPITAL COST: ${total_capital_cost:,.0f}")
    else:
        total_capital_cost = 0
        if hasattr(m.fs, 'brine_storage') and hasattr(m.fs.brine_storage, 'costing'):
            total_capital_cost += value(m.fs.brine_storage.costing.capital_cost)
        if hasattr(m.fs, 'brine_pump') and hasattr(m.fs.brine_pump, 'costing'):
            total_capital_cost += value(m.fs.brine_pump.costing.capital_cost)
        if hasattr(m.fs, 'second_pump') and hasattr(m.fs.second_pump, 'costing'):
            total_capital_cost += value(m.fs.second_pump.costing.capital_cost)
        if hasattr(m.fs, 'soda_ash_reactor') and hasattr(m.fs.soda_ash_reactor, 'costing'):
            total_capital_cost += value(m.fs.soda_ash_reactor.costing.capital_cost)
        if hasattr(m.fs, 'lime_reactor') and hasattr(m.fs.lime_reactor, 'costing'):
            total_capital_cost += value(m.fs.lime_reactor.costing.capital_cost)
        if hasattr(m.fs, 'lithium_carbonate_reactor') and hasattr(m.fs.lithium_carbonate_reactor, 'costing'):
            total_capital_cost += value(m.fs.lithium_carbonate_reactor.costing.capital_cost)
        if hasattr(m.fs, 'soda_ash_vacuum_filter') and hasattr(m.fs.soda_ash_vacuum_filter, 'costing'):
            total_capital_cost += value(m.fs.soda_ash_vacuum_filter.costing.capital_cost)
        if hasattr(m.fs, 'soda_ash_centrifuge') and hasattr(m.fs.soda_ash_centrifuge, 'costing'):
            total_capital_cost += value(m.fs.soda_ash_centrifuge.costing.capital_cost)
        if hasattr(m.fs, 'lime_press_filter') and hasattr(m.fs.lime_press_filter, 'costing'):
            total_capital_cost += value(m.fs.lime_press_filter.costing.capital_cost)
        if hasattr(m.fs, 'lime_centrifuge') and hasattr(m.fs.lime_centrifuge, 'costing'):
            total_capital_cost += value(m.fs.lime_centrifuge.costing.capital_cost)
        if hasattr(m.fs, 'li_dewatering') and hasattr(m.fs.li_dewatering, 'costing'):
            total_capital_cost += value(m.fs.li_dewatering.costing.capital_cost)
        if hasattr(m.fs, 'softening_waste') and hasattr(m.fs.softening_waste, 'costing'):
            total_capital_cost += value(m.fs.softening_waste.costing.capital_cost)
        
        print(f"\n  TOTAL CAPITAL COST: ${total_capital_cost:,.0f}")
    
    print(f"\nOPERATING COSTS:")
    
    total_power_kw = 0
    if hasattr(m.fs, 'brine_pump') and hasattr(m.fs.brine_pump.control_volume, 'work'):
        pump_power = value(m.fs.brine_pump.control_volume.work[0])
        pump_power_kw = pump_power / 1000
        total_power_kw += pump_power_kw
    
    if hasattr(m.fs, 'second_pump') and hasattr(m.fs.second_pump.control_volume, 'work'):
        second_pump_power = value(m.fs.second_pump.control_volume.work[0])
        second_pump_power_kw = second_pump_power / 1000
        total_power_kw += second_pump_power_kw
    
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
    
    annual_waste_handling_cost = 0.0
    if hasattr(m.fs, "softening_waste") and hasattr(m.fs, "waste_handling_cost"):
        try:
            props = m.fs.softening_waste.properties[0]
            water_name = getattr(m.fs, "waste_handling_water_component_name", "H2O")
            dry_mass_flow = sum(
                props.flow_mass_phase_comp["Liq", j]
                for j in props.params.component_list
                if j != water_name
            )
            annual_waste_handling_cost = value(dry_mass_flow) * 31536000 * value(m.fs.waste_handling_cost)
            dry_tonnes_yr = value(dry_mass_flow) * 31536000 / 1000.0
            print(f"  Annual waste handling cost (dry salt basis @ waste_handling $/dry tonne): ${annual_waste_handling_cost:,.0f}")
            print(f"    (approx. {dry_tonnes_yr:,.0f} dry metric tonnes salt/year)")
        except (AttributeError, TypeError, KeyError, ValueError):
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
    total_opex += annual_waste_handling_cost
    
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
    """Display comprehensive flowsheet results including feed conditions, reactor outputs, and process metrics.

    With ``show_costing=True``, also prints ``display_costing_results`` (including softening waste
    capital and waste_handling OPEX when those blocks exist).
    """
    print("\n" + "="*60)
    print("LITHIUM CARBONATE PROCESSING PLANT RESULTS")
    print("="*60)
    
    if hasattr(m.fs, 'annual_soda_ash_input') or hasattr(m.fs, 'annual_lime_input') or hasattr(m.fs, 'max_total_impurity_mass_fraction_li_product') or hasattr(m.fs, 'soda_ash_split_fraction'):
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

        if hasattr(m.fs, 'soda_ash_solution_molality'):
            molality = value(m.fs.soda_ash_solution_molality)
            print(f"  Soda Ash Solution Molality: {molality:.4f} mol/kg")

        if hasattr(m.fs, 'lime_solution_molality'):
            molality = value(m.fs.lime_solution_molality)
            print(f"  Lime Solution Molality: {molality:.4f} mol/kg")

        if hasattr(m.fs, 'soda_ash_input_split_fraction'):
            split_fraction = value(m.fs.soda_ash_input_split_fraction)
            print(f"  Soda Ash Split Fraction (to Soda Ash Reactor): {split_fraction*100:.2f}%")
            print(f"  Soda Ash to Lithium Reactor: {(1-split_fraction)*100:.2f}%")
        
        if hasattr(m.fs, 'target_li_recovery'):
            target_recovery = value(m.fs.target_li_recovery)
            print(f"  Target Lithium Recovery: {target_recovery*100:.1f}%")
        
        if hasattr(m.fs, 'max_total_product_impurity'):
            max_impurity = value(m.fs.max_total_product_impurity)
            print(f"  Max Total Impurity (Na+Mg+Ca) in Li2CO3 Product: {max_impurity*100:.3f}% mass fraction")
    
    if hasattr(m.fs, 'magnesium_removal_fraction_soda_ash_reactor'):
        print(f"\nREMOVAL FRACTIONS AND ION SPLIT FRACTIONS:")
        print("="*60)
        
        if hasattr(m.fs, 'magnesium_removal_fraction_soda_ash_reactor'):
            print(f"\n  Magnesium Removal Fraction (Soda Ash Reactor): {value(m.fs.magnesium_removal_fraction_soda_ash_reactor):.6f}")
            if hasattr(m.fs, 'soda_ash_reactor'):
                try:
                    mg_in = value(m.fs.soda_ash_reactor.precipitation_reactor.properties_in[0].flow_mol_phase_comp["Liq", "Mg"])
                    mg_mw = 24.3e-3
                    mg_in_kg_s = mg_in * mg_mw
                    mgco3_flow = value(m.fs.soda_ash_reactor.flow_mass_precipitate['MgCO3'])
                    print(f"    Mg inlet: {mg_in_kg_s:.6f} kg/s")
                    print(f"    MgCO3 precipitate: {mgco3_flow:.6f} kg/s")
                except (AttributeError, TypeError, KeyError):
                    pass
        
        if hasattr(m.fs, 'magnesium_removal_fraction_lime_reactor'):
            print(f"\n  Magnesium Removal Fraction (Lime Reactor): {value(m.fs.magnesium_removal_fraction_lime_reactor):.6f}")
            if hasattr(m.fs, 'lime_reactor'):
                try:
                    mg_in = value(m.fs.lime_reactor.precipitation_reactor.properties_in[0].flow_mol_phase_comp["Liq", "Mg"])
                    mg_mw = 24.3e-3
                    mg_in_kg_s = mg_in * mg_mw
                    brucite_flow = value(m.fs.lime_reactor.flow_mass_precipitate['Brucite'])
                    print(f"    Mg inlet: {mg_in_kg_s:.6f} kg/s")
                    print(f"    Brucite precipitate: {brucite_flow:.6f} kg/s")
                except (AttributeError, TypeError, KeyError):
                    pass
        
        if hasattr(m.fs, 'calcium_removal_fraction_soda_ash_reactor'):
            print(f"\n  Calcium Removal Fraction (Soda Ash Reactor): {value(m.fs.calcium_removal_fraction_soda_ash_reactor):.6f}")
            if hasattr(m.fs, 'soda_ash_reactor'):
                try:
                    ca_in = value(m.fs.soda_ash_reactor.precipitation_reactor.properties_in[0].flow_mol_phase_comp["Liq", "Ca"])
                    ca_mw = 40.08e-3
                    ca_in_kg_s = ca_in * ca_mw
                    caco3_flow = value(m.fs.soda_ash_reactor.flow_mass_precipitate['CaCO3'])
                    print(f"    Ca inlet: {ca_in_kg_s:.6f} kg/s")
                    print(f"    CaCO3 precipitate: {caco3_flow:.6f} kg/s")
                except (AttributeError, TypeError, KeyError):
                    pass
        
        if hasattr(m.fs, 'calcium_removal_fraction_lime_reactor'):
            print(f"\n  Calcium Removal Fraction (Lime Reactor): {value(m.fs.calcium_removal_fraction_lime_reactor):.6f}")
            if hasattr(m.fs, 'lime_reactor'):
                try:
                    ca_in = value(m.fs.lime_reactor.precipitation_reactor.properties_in[0].flow_mol_phase_comp["Liq", "Ca"])
                    ca_mw = 40.08e-3
                    ca_in_kg_s = ca_in * ca_mw
                    caco3_flow = value(m.fs.lime_reactor.flow_mass_precipitate['CaCO3'])
                    print(f"    Ca inlet: {ca_in_kg_s:.6f} kg/s")
                    print(f"    CaCO3 precipitate: {caco3_flow:.6f} kg/s")
                except (AttributeError, TypeError, KeyError):
                    pass
        
        if hasattr(m.fs, 'sulfate_removal_fraction_lime_reactor'):
            print(f"\n  Sulfate Removal Fraction (Lime Reactor): {value(m.fs.sulfate_removal_fraction_lime_reactor):.6f}")
            if hasattr(m.fs, 'lime_reactor'):
                try:
                    so4_in = value(m.fs.lime_reactor.precipitation_reactor.properties_in[0].flow_mol_phase_comp["Liq", "SO4"])
                    so4_mw = 96.06e-3
                    so4_in_kg_s = so4_in * so4_mw
                    gypsum_flow = value(m.fs.lime_reactor.flow_mass_precipitate['Gypsum'])
                    print(f"    SO4 inlet: {so4_in_kg_s:.6f} kg/s")
                    print(f"    Gypsum precipitate: {gypsum_flow:.6f} kg/s")
                except (AttributeError, TypeError, KeyError):
                    pass
        
        if hasattr(m.fs, 'lithium_removal_fraction_lithium_reactor'):
            print(f"\n  Lithium Removal Fraction (Lithium Reactor): {value(m.fs.lithium_removal_fraction_lithium_reactor):.6f}")
            if hasattr(m.fs, 'lithium_carbonate_reactor'):
                try:
                    li_in = value(m.fs.lithium_carbonate_reactor.precipitation_reactor.properties_in[0].flow_mol_phase_comp["Liq", "Li"])
                    li_mw = 6.94e-3
                    li_in_kg_s = li_in * li_mw
                    li2co3_flow = value(m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3'])
                    print(f"    Li inlet: {li_in_kg_s:.6f} kg/s")
                    print(f"    Li2CO3 precipitate: {li2co3_flow:.6f} kg/s")
                except (AttributeError, TypeError, KeyError):
                    pass
        
        if hasattr(m.fs, 'soda_ash_dissolved_ion_split_fraction'):
            print(f"\n  Soda Ash Dewatering Train Split Fractions:")
            print(f"    Dissolved ions to overflow: {value(m.fs.soda_ash_dissolved_ion_split_fraction):.4f}  (Na, K, Li, Cl, SO4, B, etc.)")
            print(f"    Precipitate ions (Mg, Ca) to overflow: {value(m.fs.soda_ash_precipitate_ion_split_fraction):.4f}")
            if hasattr(m.fs, 'soda_ash_vacuum_filter_cake_solids_fraction'):
                print(f"    Vacuum filter cake solids: {value(m.fs.soda_ash_vacuum_filter_cake_solids_fraction)*100:.0f}%")
                print(f"    Centrifuge cake solids: {value(m.fs.soda_ash_centrifuge_cake_solids_fraction)*100:.0f}%")

        if hasattr(m.fs, 'lime_dissolved_ion_split_fraction'):
            print(f"\n  Lime Dewatering Train Split Fractions:")
            print(f"    Dissolved ions to overflow: {value(m.fs.lime_dissolved_ion_split_fraction):.4f}  (Na, K, Li, Cl, SO4, B, etc.)")
            print(f"    Precipitate ions (Mg, Ca) to overflow: {value(m.fs.lime_precipitate_ion_split_fraction):.4f}")
            if hasattr(m.fs, 'lime_press_filter_cake_solids_fraction'):
                print(f"    Press filter cake solids: {value(m.fs.lime_press_filter_cake_solids_fraction)*100:.0f}%")
                print(f"    Centrifuge cake solids: {value(m.fs.lime_centrifuge_cake_solids_fraction)*100:.0f}%")

        if hasattr(m.fs, 'li_dewatering_dissolved_ion_split_fraction'):
            print(f"\n  Lithium Dewatering Split Fractions:")
            print(f"    Dissolved ions to overflow: {value(m.fs.li_dewatering_dissolved_ion_split_fraction):.4f}  (Na, K, Cl, SO4, B, etc.)")
            print(f"    Precipitate ion (Li) to overflow: {value(m.fs.li_dewatering_precipitate_ion_split_fraction):.4f}")
            if hasattr(m.fs, 'li_dewatering_cake_solids_fraction'):
                print(f"    Cake solids: {value(m.fs.li_dewatering_cake_solids_fraction)*100:.0f}%")

        if hasattr(m.fs, 'mother_liquor_recycle_fraction'):
            print(f"\n  Mother Liquor Recycle Fraction: {value(m.fs.mother_liquor_recycle_fraction)*100:.1f}% recycled, {(1-value(m.fs.mother_liquor_recycle_fraction))*100:.1f}% purged")
        
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
    
    if hasattr(m.fs, 'recycle_mixer'):
        print(f"\nRECYCLE MIXER:")
        try:
            print(f"  Pump inlet stream:")
            _stream_summary(m.fs.recycle_mixer.from_pump_state[0], indent="    ")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            print(f"  Recycle stream (from mother liquor separator):")
            _stream_summary(m.fs.recycle_mixer.from_recycle_state[0], indent="    ")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            print(f"  Mixed outlet:")
            _stream_summary(m.fs.recycle_mixer.mixed_state[0], indent="    ")
            try:
                pump_flow = value(pyunits.convert(m.fs.recycle_mixer.from_pump_state[0].flow_vol, to_units=pyunits.L / pyunits.s))
                recycle_flow = value(pyunits.convert(m.fs.recycle_mixer.from_recycle_state[0].flow_vol, to_units=pyunits.L / pyunits.s))
                if pump_flow > 0:
                    recycle_ratio = recycle_flow / pump_flow * 100
                    print(f"    Recycle-to-feed ratio: {recycle_ratio:.1f}%")
            except Exception:
                pass
        except (AttributeError, TypeError, KeyError):
            pass

    if hasattr(m.fs, 'second_pump'):
        print(f"\nSECOND PUMP (TO SODA ASH REACTOR):")
        try:
            print(f"  Pressure increase: {value(m.fs.second_pump.deltaP[0]):.0f} Pa")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            print(f"  Pump efficiency: {value(m.fs.second_pump.efficiency_pump[0]):.1%}")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            if hasattr(m.fs.second_pump.control_volume, 'work'):
                print(f"  Power consumption: {value(m.fs.second_pump.control_volume.work[0]):.2f} W")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            print(f"  Outlet stream:")
            _stream_summary(m.fs.second_pump.control_volume.properties_out[0], indent="    ")
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
            if hasattr(m.fs.soda_ash_reactor, 'waste_mass_frac_precipitate'):
                print(f"  Waste solids fraction: {value(m.fs.soda_ash_reactor.waste_mass_frac_precipitate)*100:.10f}%")
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
            if hasattr(m.fs.soda_ash_reactor, 'reaction_rate_constant_mg'):
                k_mg = value(m.fs.soda_ash_reactor.reaction_rate_constant_mg)
                print(f"  First-order reaction rate constant (Mg): {k_mg:.6f} s⁻¹")
                if k_mg > 0:
                    t_half_s = log(2) / k_mg
                    t_half_h = t_half_s / 3600
                    print(f"  Half-life (Mg): {t_half_s:.1f} s ({t_half_h:.2f} h)")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            if hasattr(m.fs.soda_ash_reactor, 'reactor_volume'):
                vol_m3 = value(m.fs.soda_ash_reactor.reactor_volume)
                vol_L = value(pyunits.convert(m.fs.soda_ash_reactor.reactor_volume, to_units=pyunits.L))
                print(f"  Reactor volume: {vol_m3:.2f} m³ ({vol_L:,.0f} L)")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            props_in = m.fs.soda_ash_reactor.dissolution_reactor.properties_in[0]
            li_mass_in = props_in.flow_mol_phase_comp["Liq", "Li"] * m.fs.brine_props.mw_comp["Li"]
            total_mass_in = sum(
                props_in.flow_mol_phase_comp["Liq", comp] * m.fs.brine_props.mw_comp[comp]
                for comp in m.fs.brine_props.component_list
            )
            li_pct_in = value(pyunits.convert(li_mass_in / total_mass_in, to_units=pyunits.dimensionless)) * 100
            print(f"  Li mass % (inlet): {li_pct_in:.4f}%")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            props_out = m.fs.soda_ash_reactor.precipitation_reactor.properties_out[0]
            li_mass_out = props_out.flow_mol_phase_comp["Liq", "Li"] * m.fs.brine_props.mw_comp["Li"]
            total_mass_out = sum(
                props_out.flow_mol_phase_comp["Liq", comp] * m.fs.brine_props.mw_comp[comp]
                for comp in m.fs.brine_props.component_list
            )
            li_pct_out = value(pyunits.convert(li_mass_out / total_mass_out, to_units=pyunits.dimensionless)) * 100
            print(f"  Li mass % (outlet): {li_pct_out:.4f}%")
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
            if hasattr(m.fs.lime_reactor, 'waste_mass_frac_precipitate'):
                print(f"  Waste solids fraction: {value(m.fs.lime_reactor.waste_mass_frac_precipitate)*100:.4f}%")
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
            if hasattr(m.fs.lime_reactor, 'reaction_rate_constant_mg'):
                k_mg = value(m.fs.lime_reactor.reaction_rate_constant_mg)
                print(f"  First-order reaction rate constant (Mg): {k_mg:.6f} s⁻¹")
                if k_mg > 0:
                    t_half_s = log(2) / k_mg
                    t_half_h = t_half_s / 3600
                    print(f"  Half-life (Mg): {t_half_s:.1f} s ({t_half_h:.2f} h)")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            if hasattr(m.fs.lime_reactor, 'reactor_volume'):
                vol_m3 = value(m.fs.lime_reactor.reactor_volume)
                vol_L = value(pyunits.convert(m.fs.lime_reactor.reactor_volume, to_units=pyunits.L))
                print(f"  Reactor volume: {vol_m3:.2f} m³ ({vol_L:,.0f} L)")
        except (AttributeError, TypeError, KeyError):
            pass
    
    if hasattr(m.fs, 'lithium_carbonate_reactor'):
        print(f"\nLITHIUM CARBONATE PRECIPITATION REACTOR:")
        try:
            # Full feed composition into the lithium carbonate reactor
            if hasattr(m.fs.lithium_carbonate_reactor, 'dissolution_reactor'):
                feed_state = m.fs.lithium_carbonate_reactor.dissolution_reactor.properties_in[0]
                try:
                    fv_L_s = value(pyunits.convert(feed_state.flow_vol, to_units=pyunits.L / pyunits.s))
                    fv_m3_h = value(pyunits.convert(feed_state.flow_vol, to_units=pyunits.m**3 / pyunits.hour))
                except Exception:
                    fv_L_s = value(pyunits.convert(feed_state.flow_vol_phase["Liq"], to_units=pyunits.L / pyunits.s))
                    fv_m3_h = value(pyunits.convert(feed_state.flow_vol_phase["Liq"], to_units=pyunits.m**3 / pyunits.hour))
                print(f"  Feed composition (before Na2CO3 addition):")
                print(f"    Volumetric flow: {fv_L_s:.3f} L/s ({fv_m3_h:.1f} m³/h)")
                for comp in ["Li", "Na", "K", "Mg", "Ca", "Cl", "SO4", "HCO3", "CO3", "B", "H", "OH"]:
                    try:
                        mol_s = value(feed_state.flow_mol_phase_comp["Liq", comp])
                        mw = _MW.get(comp)
                        if mw is not None and fv_L_s > 0:
                            conc_mol_L = mol_s / fv_L_s
                            mg_L = conc_mol_L * mw * 1e6
                            print(f"    {comp:>5}: {mol_s:.4e} mol/s  |  {conc_mol_L:.4f} mol/L  |  {mg_L:.1f} mg/L")
                        else:
                            print(f"    {comp:>5}: {mol_s:.4e} mol/s")
                    except (AttributeError, KeyError):
                        pass

            # HCO3:Li molar ratio after Na2CO3 dissolution but before Li2CO3 precipitation
            try:
                if hasattr(m.fs.lithium_carbonate_reactor, "precipitation_reactor"):
                    mid_state = m.fs.lithium_carbonate_reactor.precipitation_reactor.properties_in[0]
                    hco3_mid = value(mid_state.flow_mol_phase_comp["Liq", "HCO3"])
                    li_mid = value(mid_state.flow_mol_phase_comp["Liq", "Li"])
                    if li_mid > 0:
                        hco3_li_ratio = hco3_mid / li_mid
                        print(f"  HCO3:Li molar ratio (post-dissolution, pre-precipitation): {hco3_li_ratio:.4f}")
                        print(f"    (HCO3 = {hco3_mid:.4e} mol/s, Li = {li_mid:.4e} mol/s)")
            except (AttributeError, TypeError, KeyError, ZeroDivisionError):
                pass

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
            if hasattr(m.fs.lithium_carbonate_reactor, 'waste_mass_frac_precipitate'):
                print(f"  Waste solids fraction: {value(m.fs.lithium_carbonate_reactor.waste_mass_frac_precipitate)*100:.4f}%")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            li2co3_flow_kg_s = value(m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3'])
            li2co3_flow_g_s = value(pyunits.convert(m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3'], to_units=pyunits.g/pyunits.s))
            print(f"  Li2CO3 formation: {li2co3_flow_g_s:.3f} g/s ({li2co3_flow_kg_s:.6f} kg/s)")
        except (AttributeError, TypeError, KeyError):
            pass
        
        try:
            li2co3_flow_kg_yr = value(pyunits.convert(m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3'], to_units=pyunits.kg/pyunits.year))
            li2co3_flow_tonne_yr = value(pyunits.convert(m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3'], to_units=pyunits.tonne/pyunits.year))
            print(f"  Annual Li2CO3 production: {li2co3_flow_tonne_yr:.1f} tonnes/year ({li2co3_flow_kg_yr:,.0f} kg/year)")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            if hasattr(m.fs.lithium_carbonate_reactor, 'reaction_rate_constant_li'):
                k_li = value(m.fs.lithium_carbonate_reactor.reaction_rate_constant_li)
                print(f"  First-order reaction rate constant (Li): {k_li:.6f} s⁻¹")
                if k_li > 0:
                    t_half_s = log(2) / k_li
                    t_half_h = t_half_s / 3600
                    print(f"  Half-life (Li): {t_half_s:.1f} s ({t_half_h:.2f} h)")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            if hasattr(m.fs.lithium_carbonate_reactor, 'reactor_volume'):
                vol_m3 = value(m.fs.lithium_carbonate_reactor.reactor_volume)
                vol_L = value(pyunits.convert(m.fs.lithium_carbonate_reactor.reactor_volume, to_units=pyunits.L))
                print(f"  Reactor volume: {vol_m3:.2f} m³ ({vol_L:,.0f} L)")
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
    
    if hasattr(m.fs, 'soda_ash_mixer'):
        print(f"\nSODA ASH MIXER (RECOMBINES LIQUID STREAMS):")
        try:
            print(f"  From soda ash reactor (clarified outlet):")
            _stream_summary(m.fs.soda_ash_mixer.from_reactor_state[0], indent="    ")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            print(f"  From vacuum filter overflow:")
            _stream_summary(m.fs.soda_ash_mixer.from_vacuum_filter_state[0], indent="    ")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            print(f"  From centrifuge overflow:")
            _stream_summary(m.fs.soda_ash_mixer.from_centrifuge_state[0], indent="    ")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            print(f"  Mixed outlet (to lime reactor):")
            _stream_summary(m.fs.soda_ash_mixer.mixed_state[0], indent="    ")
        except (AttributeError, TypeError, KeyError):
            pass

    if hasattr(m.fs, 'softening_waste_mixer'):
        print(f"\nSOFTENING WASTE MIXER (SODA ASH + LIME CENTRIFUGE UNDERFLOWS):")
        try:
            print(f"  From soda ash centrifuge underflow:")
            _stream_summary(m.fs.softening_waste_mixer.from_soda_ash_state[0], indent="    ")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            print(f"  From lime centrifuge underflow:")
            _stream_summary(m.fs.softening_waste_mixer.from_lime_state[0], indent="    ")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            print(f"  Combined outlet:")
            _stream_summary(m.fs.softening_waste_mixer.mixed_state[0], indent="    ")
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
    
    if hasattr(m.fs, 'lime_mixer'):
        print(f"\nLIME MIXER (RECOMBINES LIQUID STREAMS):")
        try:
            print(f"  From lime reactor (clarified outlet):")
            _stream_summary(m.fs.lime_mixer.from_reactor_state[0], indent="    ")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            print(f"  From press filter overflow:")
            _stream_summary(m.fs.lime_mixer.from_press_filter_state[0], indent="    ")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            print(f"  From centrifuge overflow:")
            _stream_summary(m.fs.lime_mixer.from_centrifuge_state[0], indent="    ")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            print(f"  Mixed outlet (to lithium reactor):")
            _stream_summary(m.fs.lime_mixer.mixed_state[0], indent="    ")
        except (AttributeError, TypeError, KeyError):
            pass

    if hasattr(m.fs, 'softening_waste'):
        print(f"\nSOFTENING WASTE PRODUCT (COMBINED SODA ASH + LIME SOLIDS):")
        if hasattr(m.fs.softening_waste, 'costing'):
            print(f"  Costing attached: capital (TIC × correlation vs dry tonne/s) and variable OPEX (flow type 'waste_handling', $/dry metric tonne salt); see costing section when show_costing=True.")
        try:
            _stream_summary(m.fs.softening_waste.properties[0], indent="  ")
            for comp, label in [("Mg", "Mg"), ("Ca", "Ca"), ("Na", "Na"), ("SO4", "SO4")]:
                try:
                    flow = value(m.fs.softening_waste.properties[0].flow_mol_phase_comp["Liq", comp])
                    print(f"  {label} molar flow: {flow:.4e} mol/s")
                except Exception:
                    pass
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
    
    if hasattr(m.fs, 'li_mixer'):
        print(f"\nLITHIUM MIXER (MOTHER LIQUOR COLLECTION):")
        try:
            print(f"  From lithium carbonate reactor (clarified outlet):")
            _stream_summary(m.fs.li_mixer.from_reactor_state[0], indent="    ")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            print(f"  From lithium dewatering overflow:")
            _stream_summary(m.fs.li_mixer.from_dewatering_state[0], indent="    ")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            print(f"  Mixed outlet (dilute Li mother liquor):")
            _stream_summary(m.fs.li_mixer.mixed_state[0], indent="    ")
        except (AttributeError, TypeError, KeyError):
            pass

    if hasattr(m.fs, 'mother_liquor_separator'):
        print(f"\nMOTHER LIQUOR SEPARATOR:")
        try:
            if hasattr(m.fs, 'mother_liquor_recycle_fraction'):
                recycle_frac = value(m.fs.mother_liquor_recycle_fraction)
                print(f"  Recycle fraction: {recycle_frac*100:.1f}%  |  Purge fraction: {(1-recycle_frac)*100:.1f}%")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            print(f"  Inlet (mother liquor):")
            _stream_summary(m.fs.mother_liquor_separator.mixed_state[0], indent="    ")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            print(f"  Recycle stream (returned to brine feed loop):")
            _stream_summary(m.fs.mother_liquor_separator.recycle_state[0], indent="    ")
        except (AttributeError, TypeError, KeyError):
            pass
        try:
            print(f"  Purge stream (dilute Li brine purge):")
            _stream_summary(m.fs.mother_liquor_separator.purge_state[0], indent="    ")
            # Li loss in purge
            try:
                li_purge = value(m.fs.mother_liquor_separator.purge_state[0].flow_mol_phase_comp["Liq", "Li"])
                li_feed = value(m.fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", "Li"])
                if li_feed > 0:
                    li_loss_pct = li_purge / li_feed * 100
                    print(f"    Li lost in purge vs. feed: {li_loss_pct:.2f}%")
            except Exception:
                pass
        except (AttributeError, TypeError, KeyError):
            pass

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
    
    print(f"\n  REACTOR KINETICS AND SIZING:")
    total_reactor_volume = 0
    if hasattr(m.fs, 'soda_ash_reactor') and hasattr(m.fs.soda_ash_reactor, 'reactor_volume'):
        vol_m3 = value(m.fs.soda_ash_reactor.reactor_volume)
        total_reactor_volume += vol_m3
        if hasattr(m.fs.soda_ash_reactor, 'reaction_rate_constant_mg'):
            k_mg = value(m.fs.soda_ash_reactor.reaction_rate_constant_mg)
            print(f"    Soda ash reactor: {vol_m3:.2f} m³, k_Mg = {k_mg:.6f} s⁻¹")
            if k_mg > 0:
                t_half_s = log(2) / k_mg
                t_half_h = t_half_s / 3600
                print(f"      Half-life: {t_half_s:.1f} s ({t_half_h:.2f} h)")
    if hasattr(m.fs, 'lime_reactor') and hasattr(m.fs.lime_reactor, 'reactor_volume'):
        vol_m3 = value(m.fs.lime_reactor.reactor_volume)
        total_reactor_volume += vol_m3
        if hasattr(m.fs.lime_reactor, 'reaction_rate_constant_mg'):
            k_mg = value(m.fs.lime_reactor.reaction_rate_constant_mg)
            print(f"    Lime reactor: {vol_m3:.2f} m³, k_Mg = {k_mg:.6f} s⁻¹")
            if k_mg > 0:
                t_half_s = log(2) / k_mg
                t_half_h = t_half_s / 3600
                print(f"      Half-life: {t_half_s:.1f} s ({t_half_h:.2f} h)")
    if hasattr(m.fs, 'lithium_carbonate_reactor') and hasattr(m.fs.lithium_carbonate_reactor, 'reactor_volume'):
        vol_m3 = value(m.fs.lithium_carbonate_reactor.reactor_volume)
        total_reactor_volume += vol_m3
        if hasattr(m.fs.lithium_carbonate_reactor, 'reaction_rate_constant_li'):
            k_li = value(m.fs.lithium_carbonate_reactor.reaction_rate_constant_li)
            print(f"    Lithium carbonate reactor: {vol_m3:.2f} m³, k_Li = {k_li:.6f} s⁻¹")
            if k_li > 0:
                t_half_s = log(2) / k_li
                t_half_h = t_half_s / 3600
                print(f"      Half-life: {t_half_s:.1f} s ({t_half_h:.2f} h)")
    if total_reactor_volume > 0:
        print(f"    Total reactor volume: {total_reactor_volume:.2f} m³")
    
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
    if hasattr(m.fs, 'second_pump') and hasattr(m.fs.second_pump.control_volume, 'work'):
        total_power += value(m.fs.second_pump.control_volume.work[0])
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

