"""Save model results to CSV file.

This module provides functionality to save flowsheet simulation results
to a CSV file for post-processing and analysis.
"""

import csv
import os
from pyomo.environ import units as pyunits, value


def save_results(m, filename="li_processing_results.csv"):
    """
    Save comprehensive flowsheet results to a CSV file.
    
    Args:
        m: Pyomo model object containing the flowsheet
        filename: Name of the output CSV file (default: "li_processing_results.csv")
    
    Returns:
        str: Path to the saved CSV file
    """
    results = {}
    
    results["Feed Conditions"] = {}
    if hasattr(m.fs, 'brine_feed'):
        try:
            results["Feed Conditions"]["Temperature (K)"] = value(m.fs.brine_feed.properties[0].temperature)
            results["Feed Conditions"]["Pressure (Pa)"] = value(m.fs.brine_feed.properties[0].pressure)
            results["Feed Conditions"]["Volumetric Flow Rate (L/s)"] = value(
                pyunits.convert(m.fs.brine_feed.properties[0].flow_vol, to_units=pyunits.L/pyunits.s)
            )
            results["Feed Conditions"]["Volumetric Flow Rate (m3/h)"] = value(
                pyunits.convert(m.fs.brine_feed.properties[0].flow_vol, to_units=pyunits.m**3/pyunits.hour)
            )
            
            for comp in ["Li", "Na", "K", "Mg", "Ca", "Cl", "SO4", "B", "HCO3", "CO3"]:
                if comp in m.fs.brine_props.component_list:
                    results["Feed Conditions"][f"{comp} Flow (mol/s)"] = value(
                        m.fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", comp]
                    )
        except (AttributeError, TypeError, KeyError):
            pass
    
    results["Storage and Pump"] = {}
    if hasattr(m.fs, 'brine_storage'):
        try:
            if hasattr(m.fs.brine_storage, 'storage_time'):
                results["Storage and Pump"]["Storage Time (hours)"] = value(m.fs.brine_storage.storage_time[0])
        except (AttributeError, TypeError, KeyError):
            pass
    
    if hasattr(m.fs, 'brine_pump'):
        try:
            if hasattr(m.fs.brine_pump, 'deltaP'):
                results["Storage and Pump"]["Pump Pressure Increase (Pa)"] = value(m.fs.brine_pump.deltaP[0])
            if hasattr(m.fs.brine_pump, 'efficiency_pump'):
                results["Storage and Pump"]["Pump Efficiency"] = value(m.fs.brine_pump.efficiency_pump[0])
            if hasattr(m.fs.brine_pump.control_volume, 'work'):
                results["Storage and Pump"]["Pump Power (W)"] = value(m.fs.brine_pump.control_volume.work[0])
        except (AttributeError, TypeError, KeyError):
            pass
    
    results["Soda Ash Reactor"] = {}
    if hasattr(m.fs, 'soda_ash_reactor'):
        try:
            if hasattr(m.fs.soda_ash_reactor, 'flow_mass_reagent'):
                na2co3_flow = m.fs.soda_ash_reactor.flow_mass_reagent['Na2CO3']
                results["Soda Ash Reactor"]["Na2CO3 Flow (kg/s)"] = value(
                    pyunits.convert(na2co3_flow, to_units=pyunits.kg/pyunits.s)
                )
                results["Soda Ash Reactor"]["Na2CO3 Annual (tonnes/year)"] = value(
                    pyunits.convert(na2co3_flow, to_units=pyunits.tonne/pyunits.year)
                )
                if "H2O" in m.fs.soda_ash_reactor.flow_mass_reagent:
                    h2o_flow = m.fs.soda_ash_reactor.flow_mass_reagent['H2O']
                    results["Soda Ash Reactor"]["Process Water Flow (kg/s)"] = value(
                        pyunits.convert(h2o_flow, to_units=pyunits.kg/pyunits.s)
                    )
            if hasattr(m.fs.soda_ash_reactor, 'flow_mass_precipitate'):
                if 'MgCO3' in m.fs.soda_ash_reactor.flow_mass_precipitate:
                    results["Soda Ash Reactor"]["MgCO3 Formation (kg/s)"] = value(
                        m.fs.soda_ash_reactor.flow_mass_precipitate['MgCO3']
                    )
                if 'CaCO3' in m.fs.soda_ash_reactor.flow_mass_precipitate:
                    results["Soda Ash Reactor"]["CaCO3 Formation (kg/s)"] = value(
                        m.fs.soda_ash_reactor.flow_mass_precipitate['CaCO3']
                    )
        except (AttributeError, TypeError, KeyError):
            pass
    
    results["Lime Reactor"] = {}
    if hasattr(m.fs, 'lime_reactor'):
        try:
            if hasattr(m.fs.lime_reactor, 'flow_mass_reagent'):
                cao_flow = m.fs.lime_reactor.flow_mass_reagent['Ca(OH)2']
                results["Lime Reactor"]["Ca(OH)2 Flow (kg/s)"] = value(
                    pyunits.convert(cao_flow, to_units=pyunits.kg/pyunits.s)
                )
                results["Lime Reactor"]["Ca(OH)2 Annual (tonnes/year)"] = value(
                    pyunits.convert(cao_flow, to_units=pyunits.tonne/pyunits.year)
                )
                if "H2O" in m.fs.lime_reactor.flow_mass_reagent:
                    h2o_flow = m.fs.lime_reactor.flow_mass_reagent['H2O']
                    results["Lime Reactor"]["Process Water Flow (kg/s)"] = value(
                        pyunits.convert(h2o_flow, to_units=pyunits.kg/pyunits.s)
                    )
            if hasattr(m.fs.lime_reactor, 'flow_mass_precipitate'):
                if 'Brucite' in m.fs.lime_reactor.flow_mass_precipitate:
                    results["Lime Reactor"]["Brucite Formation (kg/s)"] = value(
                        m.fs.lime_reactor.flow_mass_precipitate['Brucite']
                    )
                if 'Gypsum' in m.fs.lime_reactor.flow_mass_precipitate:
                    results["Lime Reactor"]["Gypsum Formation (kg/s)"] = value(
                        m.fs.lime_reactor.flow_mass_precipitate['Gypsum']
                    )
                if 'CaCO3' in m.fs.lime_reactor.flow_mass_precipitate:
                    results["Lime Reactor"]["CaCO3 Formation (kg/s)"] = value(
                        m.fs.lime_reactor.flow_mass_precipitate['CaCO3']
                    )
        except (AttributeError, TypeError, KeyError):
            pass
    
    results["Lithium Carbonate Reactor"] = {}
    if hasattr(m.fs, 'lithium_carbonate_reactor'):
        try:
            if hasattr(m.fs.lithium_carbonate_reactor, 'flow_mass_reagent'):
                na2co3_flow = m.fs.lithium_carbonate_reactor.flow_mass_reagent['Na2CO3']
                results["Lithium Carbonate Reactor"]["Na2CO3 Flow (kg/s)"] = value(
                    pyunits.convert(na2co3_flow, to_units=pyunits.kg/pyunits.s)
                )
                results["Lithium Carbonate Reactor"]["Na2CO3 Annual (tonnes/year)"] = value(
                    pyunits.convert(na2co3_flow, to_units=pyunits.tonne/pyunits.year)
                )
                if "H2O" in m.fs.lithium_carbonate_reactor.flow_mass_reagent:
                    h2o_flow = m.fs.lithium_carbonate_reactor.flow_mass_reagent['H2O']
                    results["Lithium Carbonate Reactor"]["Process Water Flow (kg/s)"] = value(
                        pyunits.convert(h2o_flow, to_units=pyunits.kg/pyunits.s)
                    )
            if hasattr(m.fs.lithium_carbonate_reactor, 'flow_mass_precipitate'):
                if 'Li2CO3' in m.fs.lithium_carbonate_reactor.flow_mass_precipitate:
                    li2co3_flow = m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3']
                    results["Lithium Carbonate Reactor"]["Li2CO3 Formation (kg/s)"] = value(li2co3_flow)
                    results["Lithium Carbonate Reactor"]["Li2CO3 Annual (tonnes/year)"] = value(
                        pyunits.convert(li2co3_flow, to_units=pyunits.tonne/pyunits.year)
                    )
        except (AttributeError, TypeError, KeyError):
            pass
    
    results["Dewatering Units"] = {}
    dewatering_units = [
        ('soda_ash_vacuum_filter', 'Soda Ash Vacuum Filter'),
        ('soda_ash_centrifuge', 'Soda Ash Centrifuge'),
        ('lime_press_filter', 'Lime Press Filter'),
        ('lime_centrifuge', 'Lime Centrifuge'),
        ('li_dewatering', 'Lithium Dewatering')
    ]
    
    for unit_attr, unit_name in dewatering_units:
        if hasattr(m.fs, unit_attr):
            unit = getattr(m.fs, unit_attr)
            try:
                if hasattr(unit, 'electricity_consumption'):
                    results["Dewatering Units"][f"{unit_name} Power (kW)"] = value(
                        unit.electricity_consumption[0]
                    )
            except (AttributeError, TypeError, KeyError):
                pass
    
    results["Process Metrics"] = {}
    if hasattr(m.fs, 'lithium_carbonate_reactor') and hasattr(m.fs, 'brine_feed'):
        try:
            li_in = value(m.fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", "Li"])
            li2co3_out = value(m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3'])
            li_mw = 6.94e-3 * pyunits.kg / pyunits.mol
            li2co3_mw = 73.89e-3 * pyunits.kg / pyunits.mol
            li_in_mass = li_in * li_mw
            li_out_mass = li2co3_out * (2 * li_mw / li2co3_mw)
            li_recovery = (li_out_mass / li_in_mass) * 100 if value(li_in_mass) > 0 else 0
            results["Process Metrics"]["Lithium Recovery (%)"] = value(li_recovery)
        except (AttributeError, TypeError, KeyError):
            pass
    
    total_power = 0 * pyunits.W
    if hasattr(m.fs, 'brine_pump') and hasattr(m.fs.brine_pump.control_volume, 'work'):
        total_power += m.fs.brine_pump.control_volume.work[0]
    for unit_attr, _ in dewatering_units:
        if hasattr(m.fs, unit_attr):
            unit = getattr(m.fs, unit_attr)
            if hasattr(unit, 'electricity_consumption'):
                total_power += unit.electricity_consumption[0] * 1000 * pyunits.W / pyunits.kW
    
    if value(total_power) > 0:
        results["Process Metrics"]["Total Power Consumption (W)"] = value(total_power)
        if hasattr(m.fs, 'brine_feed'):
            try:
                flow_vol = m.fs.brine_feed.properties[0].flow_vol
                spec_energy = total_power / flow_vol
                results["Process Metrics"]["Specific Energy (W/(L/s))"] = value(
                    pyunits.convert(spec_energy, to_units=pyunits.W/(pyunits.L/pyunits.s))
                )
            except (AttributeError, TypeError, KeyError):
                pass
    
    results["Costing"] = {}
    if hasattr(m.fs, 'costing'):
        try:
            if hasattr(m.fs.costing, 'total_capital_cost'):
                results["Costing"]["Total Capital Cost ($)"] = value(m.fs.costing.total_capital_cost)
            if hasattr(m.fs.costing, 'plant_lifetime'):
                results["Costing"]["Plant Lifetime (years)"] = value(m.fs.costing.plant_lifetime)
            if hasattr(m.fs.costing, 'wacc'):
                results["Costing"]["WACC"] = value(m.fs.costing.wacc)
            if hasattr(m.fs.costing, 'electricity_cost'):
                results["Costing"]["Electricity Cost ($/kWh)"] = value(m.fs.costing.electricity_cost)
            if hasattr(m.fs.costing, 'utilization_factor'):
                results["Costing"]["Utilization Factor"] = value(m.fs.costing.utilization_factor)
            
            total_opex = 0
            if hasattr(m.fs, 'brine_pump') and hasattr(m.fs.brine_pump.control_volume, 'work'):
                pump_power_kw = value(pyunits.convert(m.fs.brine_pump.control_volume.work[0], to_units=pyunits.kW))
                total_opex += pump_power_kw * value(m.fs.costing.electricity_cost) * 8760 * value(m.fs.costing.utilization_factor)
            
            for unit_attr, _ in dewatering_units:
                if hasattr(m.fs, unit_attr):
                    unit = getattr(m.fs, unit_attr)
                    if hasattr(unit, 'electricity_consumption'):
                        power_kw = value(unit.electricity_consumption[0])
                        total_opex += power_kw * value(m.fs.costing.electricity_cost) * 8760 * value(m.fs.costing.utilization_factor)
            
            if hasattr(m.fs, 'soda_ash_reactor') and hasattr(m.fs.soda_ash_reactor, 'flow_mass_reagent'):
                na2co3_flow = value(m.fs.soda_ash_reactor.flow_mass_reagent['Na2CO3'])
                if hasattr(m.fs, 'soda_ash_cost'):
                    total_opex += na2co3_flow * 31536000 * value(m.fs.soda_ash_cost)
            
            if hasattr(m.fs, 'lime_reactor') and hasattr(m.fs.lime_reactor, 'flow_mass_reagent'):
                cao_flow = value(m.fs.lime_reactor.flow_mass_reagent['Ca(OH)2'])
                if hasattr(m.fs, 'lime_cost'):
                    total_opex += cao_flow * 31536000 * value(m.fs.lime_cost)
            
            if hasattr(m.fs, 'lithium_carbonate_reactor') and hasattr(m.fs.lithium_carbonate_reactor, 'flow_mass_reagent'):
                na2co3_flow = value(m.fs.lithium_carbonate_reactor.flow_mass_reagent['Na2CO3'])
                if hasattr(m.fs, 'soda_ash_cost'):
                    total_opex += na2co3_flow * 31536000 * value(m.fs.soda_ash_cost)
            
            results["Costing"]["Total Annual Operating Cost ($)"] = total_opex
            
            if hasattr(m.fs.costing, 'total_capital_cost'):
                capital_recovery_factor = value(m.fs.costing.wacc) * (1 + value(m.fs.costing.wacc))**value(m.fs.costing.plant_lifetime) / ((1 + value(m.fs.costing.wacc))**value(m.fs.costing.plant_lifetime) - 1)
                annual_capital_cost = value(m.fs.costing.total_capital_cost) * capital_recovery_factor
                results["Costing"]["Annual Capital Cost ($)"] = annual_capital_cost
                results["Costing"]["Total Annual Cost ($)"] = total_opex + annual_capital_cost
            
            if hasattr(m.fs.costing, 'LCOLi_mass'):
                lcoli_mass = value(pyunits.convert(m.fs.costing.LCOLi_mass, to_units=m.fs.costing.base_currency/pyunits.t))
                results["Costing"]["LCOLi ($/tonne Li)"] = lcoli_mass
            if hasattr(m.fs.costing, 'LCOLi2CO3_mass'):
                lcoli2co3_mass = value(pyunits.convert(m.fs.costing.LCOLi2CO3_mass, to_units=m.fs.costing.base_currency/pyunits.t))
                results["Costing"]["LCOLi2CO3 ($/tonne Li2CO3)"] = lcoli2co3_mass
        except (AttributeError, TypeError, KeyError):
            pass
    
    rows = []
    for category, data in results.items():
        if data:
            rows.append([category, ""])
            for key, val in data.items():
                rows.append([key, val])
            rows.append(["", ""])
    
    filepath = os.path.join(os.getcwd(), filename)
    with open(filepath, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Parameter", "Value"])
        writer.writerows(rows)
    
    print(f"\nResults saved to: {filepath}")
    return filepath
