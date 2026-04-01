"""Save model results to CSV file.

This module provides functionality to save flowsheet simulation results
to a CSV file for post-processing and analysis.
"""

import csv
import os
from pyomo.environ import units as pyunits, value

_MW = {
    "Li": 6.941e-3, "Na": 22.990e-3, "K": 39.098e-3, "Mg": 24.305e-3,
    "Ca": 40.078e-3, "Cl": 35.453e-3, "SO4": 96.06e-3, "B": 10.811e-3,
    "H2O": 18.015e-3, "H": 1.008e-3, "OH": 17.008e-3,
    "HCO3": 61.016e-3, "CO3": 60.009e-3,
}


def _stream_dict(state, prefix):
    """Return a flat dict of stream results for CSV writing.

    Includes volumetric flow, Li/Mg/Ca concentrations (mol/L, mg/L, wt%),
    and molar flows for Li, Mg, Ca.  Keys are prefixed with *prefix*.
    Returns an empty dict on failure.
    """
    d = {}
    try:
        try:
            fv_L_s = value(pyunits.convert(state.flow_vol, to_units=pyunits.L / pyunits.s))
            fv_m3_h = value(pyunits.convert(state.flow_vol, to_units=pyunits.m**3 / pyunits.hour))
        except Exception:
            fv_L_s = value(pyunits.convert(state.flow_vol_phase["Liq"], to_units=pyunits.L / pyunits.s))
            fv_m3_h = value(pyunits.convert(state.flow_vol_phase["Liq"], to_units=pyunits.m**3 / pyunits.hour))
        d[f"{prefix} Vol Flow (L/s)"] = fv_L_s
        d[f"{prefix} Vol Flow (m3/h)"] = fv_m3_h
    except Exception:
        fv_L_s = None

    # total mass flow for wt%
    total_mass = None
    try:
        total_mass = sum(
            value(var) * _MW[comp]
            for (phase, comp), var in state.flow_mol_phase_comp.items()
            if comp in _MW
        )
        if total_mass <= 0:
            total_mass = None
    except Exception:
        pass

    for comp in ["Li", "Na", "Mg", "Ca"]:
        try:
            mol_s = value(state.flow_mol_phase_comp["Liq", comp])
            d[f"{prefix} {comp} Flow (mol/s)"] = mol_s
            d[f"{prefix} {comp} Flow (kg/s)"] = mol_s * _MW[comp]
            if fv_L_s is not None and fv_L_s > 0:
                conc = mol_s / fv_L_s
                d[f"{prefix} {comp} (mol/L)"] = conc
                d[f"{prefix} {comp} (mg/L)"] = conc * _MW[comp] * 1e6
            if total_mass is not None:
                d[f"{prefix} {comp} (wt%)"] = mol_s * _MW[comp] / total_mass * 100
        except Exception:
            pass
    return d


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

    # ------------------------------------------------------------------ Feed
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
            results["Feed Conditions"].update(
                _stream_dict(m.fs.brine_feed.properties[0], "Feed")
            )
        except (AttributeError, TypeError, KeyError):
            pass

    # ------------------------------------------------------------------ Storage & pumps
    results["Storage and Pumps"] = {}
    if hasattr(m.fs, 'brine_storage'):
        try:
            if hasattr(m.fs.brine_storage, 'storage_time'):
                results["Storage and Pumps"]["Storage Time (hours)"] = value(m.fs.brine_storage.storage_time[0])
        except (AttributeError, TypeError, KeyError):
            pass

    if hasattr(m.fs, 'brine_pump'):
        try:
            if hasattr(m.fs.brine_pump, 'deltaP'):
                results["Storage and Pumps"]["Brine Pump Pressure Increase (Pa)"] = value(m.fs.brine_pump.deltaP[0])
            if hasattr(m.fs.brine_pump, 'efficiency_pump'):
                results["Storage and Pumps"]["Brine Pump Efficiency"] = value(m.fs.brine_pump.efficiency_pump[0])
            if hasattr(m.fs.brine_pump.control_volume, 'work'):
                results["Storage and Pumps"]["Brine Pump Power (W)"] = value(m.fs.brine_pump.control_volume.work[0])
        except (AttributeError, TypeError, KeyError):
            pass

    if hasattr(m.fs, 'second_pump'):
        try:
            if hasattr(m.fs.second_pump, 'deltaP'):
                results["Storage and Pumps"]["Second Pump Pressure Increase (Pa)"] = value(m.fs.second_pump.deltaP[0])
            if hasattr(m.fs.second_pump, 'efficiency_pump'):
                results["Storage and Pumps"]["Second Pump Efficiency"] = value(m.fs.second_pump.efficiency_pump[0])
            if hasattr(m.fs.second_pump.control_volume, 'work'):
                results["Storage and Pumps"]["Second Pump Power (W)"] = value(m.fs.second_pump.control_volume.work[0])
            results["Storage and Pumps"].update(
                _stream_dict(m.fs.second_pump.control_volume.properties_out[0], "Second Pump Outlet")
            )
        except (AttributeError, TypeError, KeyError):
            pass

    # ------------------------------------------------------------------ Recycle mixer
    results["Recycle Mixer"] = {}
    if hasattr(m.fs, 'recycle_mixer'):
        try:
            results["Recycle Mixer"].update(_stream_dict(m.fs.recycle_mixer.from_pump_state[0], "From Pump"))
            results["Recycle Mixer"].update(_stream_dict(m.fs.recycle_mixer.from_recycle_state[0], "From Recycle"))
            results["Recycle Mixer"].update(_stream_dict(m.fs.recycle_mixer.mixed_state[0], "Mixed Outlet"))
            try:
                pump_flow = value(pyunits.convert(m.fs.recycle_mixer.from_pump_state[0].flow_vol, to_units=pyunits.L / pyunits.s))
                recycle_flow = value(pyunits.convert(m.fs.recycle_mixer.from_recycle_state[0].flow_vol, to_units=pyunits.L / pyunits.s))
                if pump_flow > 0:
                    results["Recycle Mixer"]["Recycle-to-Feed Ratio (%)"] = recycle_flow / pump_flow * 100
            except Exception:
                pass
        except (AttributeError, TypeError, KeyError):
            pass

    # ------------------------------------------------------------------ Soda ash reactor
    results["Soda Ash Reactor"] = {}
    if hasattr(m.fs, 'soda_ash_reactor'):
        try:
            if hasattr(m.fs.soda_ash_reactor, 'flow_mass_reagent'):
                na2co3_flow = m.fs.soda_ash_reactor.flow_mass_reagent['Na2CO3']
                results["Soda Ash Reactor"]["Na2CO3 Flow (kg/s)"] = value(
                    pyunits.convert(na2co3_flow, to_units=pyunits.kg/pyunits.s))
                results["Soda Ash Reactor"]["Na2CO3 Annual (tonnes/year)"] = value(
                    pyunits.convert(na2co3_flow, to_units=pyunits.tonne/pyunits.year))
                if "H2O" in m.fs.soda_ash_reactor.flow_mass_reagent:
                    h2o_flow = m.fs.soda_ash_reactor.flow_mass_reagent['H2O']
                    results["Soda Ash Reactor"]["Process Water Flow (kg/s)"] = value(
                        pyunits.convert(h2o_flow, to_units=pyunits.kg/pyunits.s))
            if hasattr(m.fs.soda_ash_reactor, 'flow_mass_precipitate'):
                for ppt in ['MgCO3', 'CaCO3']:
                    if ppt in m.fs.soda_ash_reactor.flow_mass_precipitate:
                        results["Soda Ash Reactor"][f"{ppt} Formation (kg/s)"] = value(
                            m.fs.soda_ash_reactor.flow_mass_precipitate[ppt])
            if hasattr(m.fs.soda_ash_reactor, 'reaction_rate_constant_mg'):
                results["Soda Ash Reactor"]["Reaction Rate Constant Mg (1/s)"] = value(
                    m.fs.soda_ash_reactor.reaction_rate_constant_mg)
            if hasattr(m.fs.soda_ash_reactor, 'reactor_volume'):
                results["Soda Ash Reactor"]["Reactor Volume (m3)"] = value(m.fs.soda_ash_reactor.reactor_volume)
                results["Soda Ash Reactor"]["Reactor Volume (L)"] = value(
                    pyunits.convert(m.fs.soda_ash_reactor.reactor_volume, to_units=pyunits.L))
            # Outlet stream Li/Mg/Ca
            try:
                results["Soda Ash Reactor"].update(
                    _stream_dict(m.fs.soda_ash_reactor.precipitation_reactor.properties_out[0], "Reactor Outlet"))
            except Exception:
                pass
        except (AttributeError, TypeError, KeyError):
            pass

    # ------------------------------------------------------------------ Soda ash vacuum filter
    results["Soda Ash Dewatering"] = {}
    if hasattr(m.fs, 'soda_ash_vacuum_filter'):
        try:
            results["Soda Ash Dewatering"]["Vacuum Filter H2O to Overflow (%)"] = value(
                m.fs.soda_ash_vacuum_filter.split_fraction[0, 'overflow', 'H2O']) * 100
            results["Soda Ash Dewatering"]["Vacuum Filter Ion to Overflow (%)"] = value(
                m.fs.soda_ash_vacuum_filter.split_fraction[0, 'overflow', 'Na']) * 100
            if hasattr(m.fs.soda_ash_vacuum_filter, 'electricity_consumption'):
                results["Soda Ash Dewatering"]["Vacuum Filter Power (kW)"] = value(
                    m.fs.soda_ash_vacuum_filter.electricity_consumption[0])
            results["Soda Ash Dewatering"].update(
                _stream_dict(m.fs.soda_ash_vacuum_filter.overflow_state[0], "Vacuum Filter Overflow"))
        except (AttributeError, TypeError, KeyError):
            pass

    if hasattr(m.fs, 'soda_ash_centrifuge'):
        try:
            results["Soda Ash Dewatering"]["Centrifuge H2O to Overflow (%)"] = value(
                m.fs.soda_ash_centrifuge.split_fraction[0, 'overflow', 'H2O']) * 100
            results["Soda Ash Dewatering"]["Centrifuge Ion to Overflow (%)"] = value(
                m.fs.soda_ash_centrifuge.split_fraction[0, 'overflow', 'Na']) * 100
            if hasattr(m.fs.soda_ash_centrifuge, 'electricity_consumption'):
                results["Soda Ash Dewatering"]["Centrifuge Power (kW)"] = value(
                    m.fs.soda_ash_centrifuge.electricity_consumption[0])
            results["Soda Ash Dewatering"].update(
                _stream_dict(m.fs.soda_ash_centrifuge.overflow_state[0], "Centrifuge Overflow"))
        except (AttributeError, TypeError, KeyError):
            pass

    # ------------------------------------------------------------------ Soda ash mixer
    results["Soda Ash Mixer"] = {}
    if hasattr(m.fs, 'soda_ash_mixer'):
        try:
            results["Soda Ash Mixer"].update(_stream_dict(m.fs.soda_ash_mixer.from_reactor_state[0], "From Reactor"))
            results["Soda Ash Mixer"].update(_stream_dict(m.fs.soda_ash_mixer.from_vacuum_filter_state[0], "From Vacuum Filter"))
            results["Soda Ash Mixer"].update(_stream_dict(m.fs.soda_ash_mixer.from_centrifuge_state[0], "From Centrifuge"))
            results["Soda Ash Mixer"].update(_stream_dict(m.fs.soda_ash_mixer.mixed_state[0], "Mixed Outlet"))
        except (AttributeError, TypeError, KeyError):
            pass

    # ------------------------------------------------------------------ Softening waste product (combined soda ash + lime)
    results["Softening Waste"] = {}
    if hasattr(m.fs, 'softening_waste'):
        try:
            results["Softening Waste"].update(_stream_dict(m.fs.softening_waste.properties[0], "Softening Waste"))
            for comp in ["Mg", "Ca", "Na", "SO4"]:
                try:
                    flow = value(m.fs.softening_waste.properties[0].flow_mol_phase_comp["Liq", comp])
                    results["Softening Waste"][f"{comp} Flow (mol/s)"] = flow
                except Exception:
                    pass
        except (AttributeError, TypeError, KeyError):
            pass

    # ------------------------------------------------------------------ Lime reactor
    results["Lime Reactor"] = {}
    if hasattr(m.fs, 'lime_reactor'):
        try:
            if hasattr(m.fs.lime_reactor, 'flow_mass_reagent'):
                cao_flow = m.fs.lime_reactor.flow_mass_reagent['Ca(OH)2']
                results["Lime Reactor"]["Ca(OH)2 Flow (kg/s)"] = value(
                    pyunits.convert(cao_flow, to_units=pyunits.kg/pyunits.s))
                results["Lime Reactor"]["Ca(OH)2 Annual (tonnes/year)"] = value(
                    pyunits.convert(cao_flow, to_units=pyunits.tonne/pyunits.year))
                if "H2O" in m.fs.lime_reactor.flow_mass_reagent:
                    h2o_flow = m.fs.lime_reactor.flow_mass_reagent['H2O']
                    results["Lime Reactor"]["Process Water Flow (kg/s)"] = value(
                        pyunits.convert(h2o_flow, to_units=pyunits.kg/pyunits.s))
            if hasattr(m.fs.lime_reactor, 'flow_mass_precipitate'):
                for ppt in ['Brucite', 'Gypsum', 'CaCO3']:
                    if ppt in m.fs.lime_reactor.flow_mass_precipitate:
                        results["Lime Reactor"][f"{ppt} Formation (kg/s)"] = value(
                            m.fs.lime_reactor.flow_mass_precipitate[ppt])
            if hasattr(m.fs.lime_reactor, 'reaction_rate_constant_mg'):
                results["Lime Reactor"]["Reaction Rate Constant Mg (1/s)"] = value(
                    m.fs.lime_reactor.reaction_rate_constant_mg)
            if hasattr(m.fs.lime_reactor, 'reactor_volume'):
                results["Lime Reactor"]["Reactor Volume (m3)"] = value(m.fs.lime_reactor.reactor_volume)
                results["Lime Reactor"]["Reactor Volume (L)"] = value(
                    pyunits.convert(m.fs.lime_reactor.reactor_volume, to_units=pyunits.L))
            try:
                results["Lime Reactor"].update(
                    _stream_dict(m.fs.lime_reactor.precipitation_reactor.properties_out[0], "Reactor Outlet"))
            except Exception:
                pass
        except (AttributeError, TypeError, KeyError):
            pass

    # ------------------------------------------------------------------ Lime dewatering
    results["Lime Dewatering"] = {}
    if hasattr(m.fs, 'lime_press_filter'):
        try:
            results["Lime Dewatering"]["Press Filter H2O to Overflow (%)"] = value(
                m.fs.lime_press_filter.split_fraction[0, 'overflow', 'H2O']) * 100
            results["Lime Dewatering"]["Press Filter Ion to Overflow (%)"] = value(
                m.fs.lime_press_filter.split_fraction[0, 'overflow', 'Na']) * 100
            if hasattr(m.fs.lime_press_filter, 'electricity_consumption'):
                results["Lime Dewatering"]["Press Filter Power (kW)"] = value(
                    m.fs.lime_press_filter.electricity_consumption[0])
            results["Lime Dewatering"].update(
                _stream_dict(m.fs.lime_press_filter.overflow_state[0], "Press Filter Overflow"))
        except (AttributeError, TypeError, KeyError):
            pass

    if hasattr(m.fs, 'lime_centrifuge'):
        try:
            results["Lime Dewatering"]["Centrifuge H2O to Overflow (%)"] = value(
                m.fs.lime_centrifuge.split_fraction[0, 'overflow', 'H2O']) * 100
            results["Lime Dewatering"]["Centrifuge Ion to Overflow (%)"] = value(
                m.fs.lime_centrifuge.split_fraction[0, 'overflow', 'Na']) * 100
            if hasattr(m.fs.lime_centrifuge, 'electricity_consumption'):
                results["Lime Dewatering"]["Centrifuge Power (kW)"] = value(
                    m.fs.lime_centrifuge.electricity_consumption[0])
            results["Lime Dewatering"].update(
                _stream_dict(m.fs.lime_centrifuge.overflow_state[0], "Centrifuge Overflow"))
        except (AttributeError, TypeError, KeyError):
            pass

    # ------------------------------------------------------------------ Lime mixer
    results["Lime Mixer"] = {}
    if hasattr(m.fs, 'lime_mixer'):
        try:
            results["Lime Mixer"].update(_stream_dict(m.fs.lime_mixer.from_reactor_state[0], "From Reactor"))
            results["Lime Mixer"].update(_stream_dict(m.fs.lime_mixer.from_press_filter_state[0], "From Press Filter"))
            results["Lime Mixer"].update(_stream_dict(m.fs.lime_mixer.from_centrifuge_state[0], "From Centrifuge"))
            results["Lime Mixer"].update(_stream_dict(m.fs.lime_mixer.mixed_state[0], "Mixed Outlet"))
        except (AttributeError, TypeError, KeyError):
            pass


    # ------------------------------------------------------------------ Lithium carbonate reactor
    results["Lithium Carbonate Reactor"] = {}
    if hasattr(m.fs, 'lithium_carbonate_reactor'):
        try:
            if hasattr(m.fs.lithium_carbonate_reactor, 'flow_mass_reagent'):
                na2co3_flow = m.fs.lithium_carbonate_reactor.flow_mass_reagent['Na2CO3']
                results["Lithium Carbonate Reactor"]["Na2CO3 Flow (kg/s)"] = value(
                    pyunits.convert(na2co3_flow, to_units=pyunits.kg/pyunits.s))
                results["Lithium Carbonate Reactor"]["Na2CO3 Annual (tonnes/year)"] = value(
                    pyunits.convert(na2co3_flow, to_units=pyunits.tonne/pyunits.year))
                if "H2O" in m.fs.lithium_carbonate_reactor.flow_mass_reagent:
                    h2o_flow = m.fs.lithium_carbonate_reactor.flow_mass_reagent['H2O']
                    results["Lithium Carbonate Reactor"]["Process Water Flow (kg/s)"] = value(
                        pyunits.convert(h2o_flow, to_units=pyunits.kg/pyunits.s))
            if hasattr(m.fs.lithium_carbonate_reactor, 'flow_mass_precipitate'):
                if 'Li2CO3' in m.fs.lithium_carbonate_reactor.flow_mass_precipitate:
                    li2co3_flow = m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3']
                    results["Lithium Carbonate Reactor"]["Li2CO3 Formation (kg/s)"] = value(li2co3_flow)
                    results["Lithium Carbonate Reactor"]["Li2CO3 Annual (tonnes/year)"] = value(
                        pyunits.convert(li2co3_flow, to_units=pyunits.tonne/pyunits.year))
            if hasattr(m.fs.lithium_carbonate_reactor, 'reaction_rate_constant_li'):
                results["Lithium Carbonate Reactor"]["Reaction Rate Constant Li (1/s)"] = value(
                    m.fs.lithium_carbonate_reactor.reaction_rate_constant_li)
            if hasattr(m.fs.lithium_carbonate_reactor, 'reactor_volume'):
                results["Lithium Carbonate Reactor"]["Reactor Volume (m3)"] = value(
                    m.fs.lithium_carbonate_reactor.reactor_volume)
                results["Lithium Carbonate Reactor"]["Reactor Volume (L)"] = value(
                    pyunits.convert(m.fs.lithium_carbonate_reactor.reactor_volume, to_units=pyunits.L))
            try:
                results["Lithium Carbonate Reactor"].update(
                    _stream_dict(m.fs.lithium_carbonate_reactor.precipitation_reactor.properties_out[0],
                                 "Reactor Outlet"))
            except Exception:
                pass
        except (AttributeError, TypeError, KeyError):
            pass

    # ------------------------------------------------------------------ Li dewatering
    results["Lithium Dewatering"] = {}
    if hasattr(m.fs, 'li_dewatering'):
        try:
            results["Lithium Dewatering"]["H2O to Overflow (%)"] = value(
                m.fs.li_dewatering.split_fraction[0, 'overflow', 'H2O']) * 100
            results["Lithium Dewatering"]["Ion to Overflow (%)"] = value(
                m.fs.li_dewatering.split_fraction[0, 'overflow', 'Na']) * 100
            if hasattr(m.fs.li_dewatering, 'electricity_consumption'):
                results["Lithium Dewatering"]["Power (kW)"] = value(m.fs.li_dewatering.electricity_consumption[0])
            results["Lithium Dewatering"].update(
                _stream_dict(m.fs.li_dewatering.overflow_state[0], "Overflow"))
            results["Lithium Dewatering"].update(
                _stream_dict(m.fs.li_dewatering.underflow_state[0], "Underflow (Product Cake)"))
        except (AttributeError, TypeError, KeyError):
            pass

    # ------------------------------------------------------------------ Li mixer
    results["Lithium Mixer"] = {}
    if hasattr(m.fs, 'li_mixer'):
        try:
            results["Lithium Mixer"].update(_stream_dict(m.fs.li_mixer.from_reactor_state[0], "From Reactor"))
            results["Lithium Mixer"].update(_stream_dict(m.fs.li_mixer.from_dewatering_state[0], "From Dewatering"))
            results["Lithium Mixer"].update(_stream_dict(m.fs.li_mixer.mixed_state[0], "Mixed Outlet (Mother Liquor)"))
        except (AttributeError, TypeError, KeyError):
            pass

    # ------------------------------------------------------------------ Mother liquor separator
    results["Mother Liquor Separator"] = {}
    if hasattr(m.fs, 'mother_liquor_separator'):
        try:
            if hasattr(m.fs, 'mother_liquor_recycle_fraction'):
                recycle_frac = value(m.fs.mother_liquor_recycle_fraction)
                results["Mother Liquor Separator"]["Recycle Fraction (%)"] = recycle_frac * 100
                results["Mother Liquor Separator"]["Purge Fraction (%)"] = (1 - recycle_frac) * 100
            results["Mother Liquor Separator"].update(
                _stream_dict(m.fs.mother_liquor_separator.mixed_state[0], "Inlet"))
            results["Mother Liquor Separator"].update(
                _stream_dict(m.fs.mother_liquor_separator.recycle_state[0], "Recycle"))
            results["Mother Liquor Separator"].update(
                _stream_dict(m.fs.mother_liquor_separator.purge_state[0], "Purge"))
            # Li lost in purge vs. feed
            try:
                li_purge = value(m.fs.mother_liquor_separator.purge_state[0].flow_mol_phase_comp["Liq", "Li"])
                li_feed = value(m.fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", "Li"])
                if li_feed > 0:
                    results["Mother Liquor Separator"]["Li Lost in Purge vs Feed (%)"] = li_purge / li_feed * 100
            except Exception:
                pass
        except (AttributeError, TypeError, KeyError):
            pass

    # ------------------------------------------------------------------ Process metrics
    results["Process Metrics"] = {}
    if hasattr(m.fs, 'lithium_carbonate_reactor') and hasattr(m.fs, 'brine_feed'):
        try:
            li_in = value(m.fs.brine_feed.properties[0].flow_mol_phase_comp["Liq", "Li"])
            li2co3_out = value(m.fs.lithium_carbonate_reactor.flow_mass_precipitate['Li2CO3'])
            li_mw = 6.941e-3
            li2co3_mw = 73.89e-3
            li_in_mass = li_in * li_mw
            li_out_mass = li2co3_out * (2 * li_mw / li2co3_mw)
            results["Process Metrics"]["Lithium Recovery (%)"] = (li_out_mass / li_in_mass * 100
                                                                   if li_in_mass > 0 else 0)
        except (AttributeError, TypeError, KeyError):
            pass

    total_reactor_volume = 0
    for attr in ['soda_ash_reactor', 'lime_reactor', 'lithium_carbonate_reactor']:
        unit = getattr(m.fs, attr, None)
        if unit is not None and hasattr(unit, 'reactor_volume'):
            total_reactor_volume += value(unit.reactor_volume)
    if total_reactor_volume > 0:
        results["Process Metrics"]["Total Reactor Volume (m3)"] = total_reactor_volume

    dewatering_units = [
        ('soda_ash_vacuum_filter', 'Soda Ash Vacuum Filter'),
        ('soda_ash_centrifuge', 'Soda Ash Centrifuge'),
        ('lime_press_filter', 'Lime Press Filter'),
        ('lime_centrifuge', 'Lime Centrifuge'),
        ('li_dewatering', 'Lithium Dewatering'),
    ]

    total_power = 0.0
    if hasattr(m.fs, 'brine_pump') and hasattr(m.fs.brine_pump.control_volume, 'work'):
        total_power += value(m.fs.brine_pump.control_volume.work[0])
    if hasattr(m.fs, 'second_pump') and hasattr(m.fs.second_pump.control_volume, 'work'):
        total_power += value(m.fs.second_pump.control_volume.work[0])
    for unit_attr, _ in dewatering_units:
        unit = getattr(m.fs, unit_attr, None)
        if unit is not None and hasattr(unit, 'electricity_consumption'):
            total_power += value(unit.electricity_consumption[0]) * 1000  # kW → W

    if total_power > 0:
        results["Process Metrics"]["Total Power Consumption (W)"] = total_power
        try:
            flow_vol = value(pyunits.convert(m.fs.brine_feed.properties[0].flow_vol,
                                             to_units=pyunits.L / pyunits.s))
            results["Process Metrics"]["Specific Energy (W/(L/s))"] = total_power / flow_vol
        except Exception:
            pass

    # ------------------------------------------------------------------ Costing
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

            total_opex = 0.0
            if hasattr(m.fs, 'brine_pump') and hasattr(m.fs.brine_pump.control_volume, 'work'):
                pump_power_kw = value(pyunits.convert(m.fs.brine_pump.control_volume.work[0], to_units=pyunits.kW))
                total_opex += pump_power_kw * value(m.fs.costing.electricity_cost) * 8760 * value(m.fs.costing.utilization_factor)
            if hasattr(m.fs, 'second_pump') and hasattr(m.fs.second_pump.control_volume, 'work'):
                pump2_power_kw = value(pyunits.convert(m.fs.second_pump.control_volume.work[0], to_units=pyunits.kW))
                total_opex += pump2_power_kw * value(m.fs.costing.electricity_cost) * 8760 * value(m.fs.costing.utilization_factor)
            for unit_attr, _ in dewatering_units:
                unit = getattr(m.fs, unit_attr, None)
                if unit is not None and hasattr(unit, 'electricity_consumption'):
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
                crf = (value(m.fs.costing.wacc) * (1 + value(m.fs.costing.wacc))**value(m.fs.costing.plant_lifetime)
                       / ((1 + value(m.fs.costing.wacc))**value(m.fs.costing.plant_lifetime) - 1))
                annual_capex = value(m.fs.costing.total_capital_cost) * crf
                results["Costing"]["Annual Capital Cost ($)"] = annual_capex
                results["Costing"]["Total Annual Cost ($)"] = total_opex + annual_capex
            if hasattr(m.fs.costing, 'LCOLi_mass'):
                results["Costing"]["LCOLi ($/tonne Li)"] = value(
                    pyunits.convert(m.fs.costing.LCOLi_mass, to_units=m.fs.costing.base_currency/pyunits.t))
            if hasattr(m.fs.costing, 'LCOLi2CO3_mass'):
                results["Costing"]["LCOLi2CO3 ($/tonne Li2CO3)"] = value(
                    pyunits.convert(m.fs.costing.LCOLi2CO3_mass, to_units=m.fs.costing.base_currency/pyunits.t))
        except (AttributeError, TypeError, KeyError):
            pass

    # ------------------------------------------------------------------ Write CSV
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
