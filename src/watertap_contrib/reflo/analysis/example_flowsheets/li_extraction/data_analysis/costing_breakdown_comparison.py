"""Results comparison visualization for lithium extraction flowsheet.

Creates cost breakdown visualization for two WaterTAP model results with detailed categories.
"""

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np


def calculate_lithium_costs_model1(inflation_factor=1.0):
    """Calculate lithium costs for WaterTAP Model 1.
    
    Args:
        inflation_factor (float): Factor to adjust all costs for inflation (default: 1.0 = no adjustment)
        
    Returns:
        dict: Dictionary containing all calculated cost values and percentages
    """
    # WaterTAP Model 1 numbers
    crf = 0.10369  # capital recovery factor
    watertap_capex = 1190831515 * inflation_factor
    watertap_opex = (183273065+245213739) * inflation_factor
    watertap_revenue = 245213739 * inflation_factor

    utilization_factor = 0.98

    # Q calculation
    inlet_li_conc = 2  # g/kg
    li_recovery = 0.6  # fraction
    inlet_flow_vol = 1280  # m^3/s
    li_outflow = inlet_li_conc * li_recovery * inlet_flow_vol / 1000  # kg/s
    Q = li_outflow * 3600 * 24 * 365 / 1000  # mt/year

    LCOLi_watertap_total = (crf * watertap_capex + watertap_opex - watertap_revenue) / (utilization_factor * Q)
    LCOLi_watertap_capex = (crf * watertap_capex) / (utilization_factor * Q)
    LCOLi_watertap_opex = watertap_opex / (utilization_factor * Q)
    LCOLi_watertap_revenue = watertap_revenue / (utilization_factor * Q)
    
    # Raw category values for WaterTAP capex (total costs in USD millions)
    watertap_capex_solids_handling_raw = 440.8 * inflation_factor
    watertap_capex_liner_cost_raw = 273.4 * inflation_factor
    watertap_capex_well_cost_raw = 104.7 * inflation_factor
    watertap_capex_pipe_pump_cost_raw = 104.7 * inflation_factor
    watertap_capex_dike_cost_raw = 103.5 * inflation_factor
    watertap_capex_shipping_cost_raw = 49.4 * inflation_factor
    watertap_capex_electrical_cost_raw = 38.9 * inflation_factor
    watertap_capex_land_clearing_cost_raw = 17.0 * inflation_factor
    watertap_capex_road_cost_raw = 8.9 * inflation_factor
    
    # Calculate percentages for WaterTAP capex
    watertap_capex_total_raw = (watertap_capex_solids_handling_raw + watertap_capex_liner_cost_raw + watertap_capex_well_cost_raw + 
                               watertap_capex_pipe_pump_cost_raw + watertap_capex_dike_cost_raw + 
                               watertap_capex_shipping_cost_raw + watertap_capex_electrical_cost_raw + 
                               watertap_capex_land_clearing_cost_raw + watertap_capex_road_cost_raw)
    
    watertap_capex_solids_handling_pct = watertap_capex_solids_handling_raw / watertap_capex_total_raw
    watertap_capex_liner_cost_pct = watertap_capex_liner_cost_raw / watertap_capex_total_raw
    watertap_capex_well_cost_pct = watertap_capex_well_cost_raw / watertap_capex_total_raw
    watertap_capex_pipe_pump_cost_pct = watertap_capex_pipe_pump_cost_raw / watertap_capex_total_raw
    watertap_capex_dike_cost_pct = watertap_capex_dike_cost_raw / watertap_capex_total_raw
    watertap_capex_shipping_cost_pct = watertap_capex_shipping_cost_raw / watertap_capex_total_raw
    watertap_capex_electrical_cost_pct = watertap_capex_electrical_cost_raw / watertap_capex_total_raw
    watertap_capex_land_clearing_cost_pct = watertap_capex_land_clearing_cost_raw / watertap_capex_total_raw
    watertap_capex_road_cost_pct = watertap_capex_road_cost_raw / watertap_capex_total_raw
    
    # Raw category values for WaterTAP opex (total costs in USD millions per year)
    watertap_opex_electricity_raw = 69.3 * inflation_factor
    watertap_opex_solids_handling_raw = 153.9 * inflation_factor
    watertap_opex_government_agreements_raw = 131.8 * inflation_factor
    watertap_opex_shipping_raw = 23.7 * inflation_factor
    watertap_opex_maintenance_labor_chemical_raw = 35.7 * inflation_factor
    watertap_opex_liner_replacement_raw = 13.7 * inflation_factor
    
    # Calculate percentages for WaterTAP opex
    watertap_opex_total_raw = (watertap_opex_electricity_raw + watertap_opex_solids_handling_raw + 
                              watertap_opex_government_agreements_raw + watertap_opex_shipping_raw + 
                              watertap_opex_maintenance_labor_chemical_raw + watertap_opex_liner_replacement_raw)
    
    watertap_opex_electricity_pct = watertap_opex_electricity_raw / watertap_opex_total_raw
    watertap_opex_solids_handling_pct = watertap_opex_solids_handling_raw / watertap_opex_total_raw
    watertap_opex_government_agreements_pct = watertap_opex_government_agreements_raw / watertap_opex_total_raw
    watertap_opex_shipping_pct = watertap_opex_shipping_raw / watertap_opex_total_raw
    watertap_opex_maintenance_labor_chemical_pct = watertap_opex_maintenance_labor_chemical_raw / watertap_opex_total_raw
    watertap_opex_liner_replacement_pct = watertap_opex_liner_replacement_raw / watertap_opex_total_raw
    
    return {
        'watertap_total': LCOLi_watertap_total,
        'watertap_capex': LCOLi_watertap_capex,
        'watertap_opex': LCOLi_watertap_opex,
        'watertap_revenue': LCOLi_watertap_revenue,
        'Q': Q,
        # WaterTAP capex categories
        'watertap_capex_total': LCOLi_watertap_capex,
        'watertap_capex_solids_handling': LCOLi_watertap_capex * watertap_capex_solids_handling_pct,
        'watertap_capex_liner_cost': LCOLi_watertap_capex * watertap_capex_liner_cost_pct,
        'watertap_capex_well_cost': LCOLi_watertap_capex * watertap_capex_well_cost_pct,
        'watertap_capex_pipe_pump_cost': LCOLi_watertap_capex * watertap_capex_pipe_pump_cost_pct,
        'watertap_capex_dike_cost': LCOLi_watertap_capex * watertap_capex_dike_cost_pct,
        'watertap_capex_shipping_cost': LCOLi_watertap_capex * watertap_capex_shipping_cost_pct,
        'watertap_capex_electrical_cost': LCOLi_watertap_capex * watertap_capex_electrical_cost_pct,
        'watertap_capex_land_clearing_cost': LCOLi_watertap_capex * watertap_capex_land_clearing_cost_pct,
        'watertap_capex_road_cost': LCOLi_watertap_capex * watertap_capex_road_cost_pct,
        'watertap_capex_solids_handling_pct': watertap_capex_solids_handling_pct,
        'watertap_capex_liner_cost_pct': watertap_capex_liner_cost_pct,
        'watertap_capex_well_cost_pct': watertap_capex_well_cost_pct,
        'watertap_capex_pipe_pump_cost_pct': watertap_capex_pipe_pump_cost_pct,
        'watertap_capex_dike_cost_pct': watertap_capex_dike_cost_pct,
        'watertap_capex_shipping_cost_pct': watertap_capex_shipping_cost_pct,
        'watertap_capex_electrical_cost_pct': watertap_capex_electrical_cost_pct,
        'watertap_capex_land_clearing_cost_pct': watertap_capex_land_clearing_cost_pct,
        'watertap_capex_road_cost_pct': watertap_capex_road_cost_pct,
        # WaterTAP opex categories
        'watertap_opex_total': LCOLi_watertap_opex,
        'watertap_opex_electricity': LCOLi_watertap_opex * watertap_opex_electricity_pct,
        'watertap_opex_solids_handling': LCOLi_watertap_opex * watertap_opex_solids_handling_pct,
        'watertap_opex_government_agreements': LCOLi_watertap_opex * watertap_opex_government_agreements_pct,
        'watertap_opex_shipping': LCOLi_watertap_opex * watertap_opex_shipping_pct,
        'watertap_opex_maintenance_labor_chemical': LCOLi_watertap_opex * watertap_opex_maintenance_labor_chemical_pct,
        'watertap_opex_liner_replacement': LCOLi_watertap_opex * watertap_opex_liner_replacement_pct,
        'watertap_opex_electricity_pct': watertap_opex_electricity_pct,
        'watertap_opex_solids_handling_pct': watertap_opex_solids_handling_pct,
        'watertap_opex_government_agreements_pct': watertap_opex_government_agreements_pct,
        'watertap_opex_shipping_pct': watertap_opex_shipping_pct,
        'watertap_opex_maintenance_labor_chemical_pct': watertap_opex_maintenance_labor_chemical_pct,
        'watertap_opex_liner_replacement_pct': watertap_opex_liner_replacement_pct
    }

def calculate_lithium_costs_model2(inflation_factor=1.0):
    """Calculate lithium costs for WaterTAP Model 2 (modified parameters).
    
    Args:
        inflation_factor (float): Factor to adjust all costs for inflation (default: 1.0 = no adjustment)
        
    Returns:
        dict: Dictionary containing all calculated cost values and percentages
    """
    # WaterTAP Model 2 numbers (modified for comparison)
    crf = 0.10369  # capital recovery factor
    watertap_capex = 1165484482 * inflation_factor  # Modified capex
    watertap_opex = (190774352+245213739) * inflation_factor  # Modified opex
    watertap_revenue = 245213739 * inflation_factor  # Modified revenue

    utilization_factor = 0.98

    # Q calculation
    inlet_li_conc = 2  # g/kg
    li_recovery = 0.6  # fraction
    inlet_flow_vol = 1280  # m^3/s
    li_outflow = inlet_li_conc * li_recovery * inlet_flow_vol / 1000  # kg/s
    Q = li_outflow * 3600 * 24 * 365 / 1000  # mt/year

    LCOLi_watertap_total = (crf * watertap_capex + watertap_opex - watertap_revenue) / (utilization_factor * Q)
    LCOLi_watertap_capex = (crf * watertap_capex) / (utilization_factor * Q)
    LCOLi_watertap_opex = watertap_opex / (utilization_factor * Q)
    LCOLi_watertap_revenue = watertap_revenue / (utilization_factor * Q)
    
    # Raw category values for WaterTAP capex (total costs in USD millions) - modified for Model 2
    watertap_capex_solids_handling_raw = 440.8 * inflation_factor
    watertap_capex_liner_cost_raw = 253.2 * inflation_factor
    watertap_capex_well_cost_raw = 104.7 * inflation_factor
    watertap_capex_pipe_pump_cost_raw = 104.7 * inflation_factor
    watertap_capex_dike_cost_raw = 99.7 * inflation_factor
    watertap_capex_shipping_cost_raw = 49.4 * inflation_factor
    watertap_capex_electrical_cost_raw = 38.9 * inflation_factor
    watertap_capex_land_clearing_cost_raw = 15.9 * inflation_factor
    watertap_capex_road_cost_raw = 8.6 * inflation_factor
    
    # Calculate percentages for WaterTAP capex
    watertap_capex_total_raw = (watertap_capex_solids_handling_raw + watertap_capex_liner_cost_raw + watertap_capex_well_cost_raw + 
                               watertap_capex_pipe_pump_cost_raw + watertap_capex_dike_cost_raw + 
                               watertap_capex_shipping_cost_raw + watertap_capex_electrical_cost_raw + 
                               watertap_capex_land_clearing_cost_raw + watertap_capex_road_cost_raw)
    
    watertap_capex_solids_handling_pct = watertap_capex_solids_handling_raw / watertap_capex_total_raw
    watertap_capex_liner_cost_pct = watertap_capex_liner_cost_raw / watertap_capex_total_raw
    watertap_capex_well_cost_pct = watertap_capex_well_cost_raw / watertap_capex_total_raw
    watertap_capex_pipe_pump_cost_pct = watertap_capex_pipe_pump_cost_raw / watertap_capex_total_raw
    watertap_capex_dike_cost_pct = watertap_capex_dike_cost_raw / watertap_capex_total_raw
    watertap_capex_shipping_cost_pct = watertap_capex_shipping_cost_raw / watertap_capex_total_raw
    watertap_capex_electrical_cost_pct = watertap_capex_electrical_cost_raw / watertap_capex_total_raw
    watertap_capex_land_clearing_cost_pct = watertap_capex_land_clearing_cost_raw / watertap_capex_total_raw
    watertap_capex_road_cost_pct = watertap_capex_road_cost_raw / watertap_capex_total_raw
    
    # Raw category values for WaterTAP opex (total costs in USD millions per year) - modified for Model 2
    watertap_opex_electricity_raw = 69.3 * inflation_factor
    watertap_opex_solids_handling_raw = 153.9 * inflation_factor
    watertap_opex_government_agreements_raw = 131.8 * inflation_factor
    watertap_opex_shipping_raw = 23.7 * inflation_factor
    watertap_opex_maintenance_labor_chemical_raw = 35.0 * inflation_factor
    watertap_opex_liner_replacement_raw = 12.7 * inflation_factor
    watertap_opex_dye_raw = 9.5 * inflation_factor
    
    # Calculate percentages for WaterTAP opex
    watertap_opex_total_raw = (watertap_opex_electricity_raw + watertap_opex_solids_handling_raw + 
                              watertap_opex_government_agreements_raw + watertap_opex_shipping_raw + 
                              watertap_opex_maintenance_labor_chemical_raw + watertap_opex_liner_replacement_raw +
                              watertap_opex_dye_raw)
    
    watertap_opex_electricity_pct = watertap_opex_electricity_raw / watertap_opex_total_raw
    watertap_opex_solids_handling_pct = watertap_opex_solids_handling_raw / watertap_opex_total_raw
    watertap_opex_government_agreements_pct = watertap_opex_government_agreements_raw / watertap_opex_total_raw
    watertap_opex_shipping_pct = watertap_opex_shipping_raw / watertap_opex_total_raw
    watertap_opex_maintenance_labor_chemical_pct = watertap_opex_maintenance_labor_chemical_raw / watertap_opex_total_raw
    watertap_opex_liner_replacement_pct = watertap_opex_liner_replacement_raw / watertap_opex_total_raw
    watertap_opex_dye_pct = watertap_opex_dye_raw / watertap_opex_total_raw

    return {
        'watertap_total': LCOLi_watertap_total,
        'watertap_capex': LCOLi_watertap_capex,
        'watertap_opex': LCOLi_watertap_opex,
        'watertap_revenue': LCOLi_watertap_revenue,
        'Q': Q,
        # WaterTAP capex categories
        'watertap_capex_total': LCOLi_watertap_capex,
        'watertap_capex_solids_handling': LCOLi_watertap_capex * watertap_capex_solids_handling_pct,
        'watertap_capex_liner_cost': LCOLi_watertap_capex * watertap_capex_liner_cost_pct,
        'watertap_capex_well_cost': LCOLi_watertap_capex * watertap_capex_well_cost_pct,
        'watertap_capex_pipe_pump_cost': LCOLi_watertap_capex * watertap_capex_pipe_pump_cost_pct,
        'watertap_capex_dike_cost': LCOLi_watertap_capex * watertap_capex_dike_cost_pct,
        'watertap_capex_shipping_cost': LCOLi_watertap_capex * watertap_capex_shipping_cost_pct,
        'watertap_capex_electrical_cost': LCOLi_watertap_capex * watertap_capex_electrical_cost_pct,
        'watertap_capex_land_clearing_cost': LCOLi_watertap_capex * watertap_capex_land_clearing_cost_pct,
        'watertap_capex_road_cost': LCOLi_watertap_capex * watertap_capex_road_cost_pct,
        'watertap_capex_solids_handling_pct': watertap_capex_solids_handling_pct,
        'watertap_capex_liner_cost_pct': watertap_capex_liner_cost_pct,
        'watertap_capex_well_cost_pct': watertap_capex_well_cost_pct,
        'watertap_capex_pipe_pump_cost_pct': watertap_capex_pipe_pump_cost_pct,
        'watertap_capex_dike_cost_pct': watertap_capex_dike_cost_pct,
        'watertap_capex_shipping_cost_pct': watertap_capex_shipping_cost_pct,
        'watertap_capex_electrical_cost_pct': watertap_capex_electrical_cost_pct,
        'watertap_capex_land_clearing_cost_pct': watertap_capex_land_clearing_cost_pct,
        'watertap_capex_road_cost_pct': watertap_capex_road_cost_pct,
        # WaterTAP opex categories
        'watertap_opex_total': LCOLi_watertap_opex,
        'watertap_opex_electricity': LCOLi_watertap_opex * watertap_opex_electricity_pct,
        'watertap_opex_solids_handling': LCOLi_watertap_opex * watertap_opex_solids_handling_pct,
        'watertap_opex_government_agreements': LCOLi_watertap_opex * watertap_opex_government_agreements_pct,
        'watertap_opex_shipping': LCOLi_watertap_opex * watertap_opex_shipping_pct,
        'watertap_opex_maintenance_labor_chemical': LCOLi_watertap_opex * watertap_opex_maintenance_labor_chemical_pct,
        'watertap_opex_liner_replacement': LCOLi_watertap_opex * watertap_opex_liner_replacement_pct,
        'watertap_opex_dye': LCOLi_watertap_opex * watertap_opex_dye_pct,
        'watertap_opex_electricity_pct': watertap_opex_electricity_pct,
        'watertap_opex_solids_handling_pct': watertap_opex_solids_handling_pct,
        'watertap_opex_government_agreements_pct': watertap_opex_government_agreements_pct,
        'watertap_opex_shipping_pct': watertap_opex_shipping_pct,
        'watertap_opex_maintenance_labor_chemical_pct': watertap_opex_maintenance_labor_chemical_pct,
        'watertap_opex_liner_replacement_pct': watertap_opex_liner_replacement_pct,
        'watertap_opex_dye_pct': watertap_opex_dye_pct
    }

def create_cost_breakdown_plot(costs_model1, costs_model2):
    """Create the cost breakdown comparison plot.
    
    Args:
        costs_model1 (dict): Dictionary containing Model 1 cost values
        costs_model2 (dict): Dictionary containing Model 2 cost values
    """
    # WaterTAP Model 1 data
    total_capex_model1 = costs_model1['watertap_capex_total']
    total_opex_model1 = costs_model1['watertap_opex_total']
    revenue_model1 = costs_model1['watertap_revenue']

    # WaterTAP Model 2 data
    total_capex_model2 = costs_model2['watertap_capex_total']
    total_opex_model2 = costs_model2['watertap_opex_total']
    revenue_model2 = costs_model2['watertap_revenue']

    # WaterTAP Model 1 capital cost breakdown percentages (reorganized to match categories)
    capex_breakdown_model1 = {
        'Evaporation ponds': (costs_model1['watertap_capex_liner_cost_pct'] + 
                             costs_model1['watertap_capex_dike_cost_pct'] + 
                             costs_model1['watertap_capex_land_clearing_cost_pct'] + 
                             costs_model1['watertap_capex_road_cost_pct']),
        'Precipitated salts processing': costs_model1['watertap_capex_solids_handling_pct'],
        'Extraction wells': (costs_model1['watertap_capex_well_cost_pct'] + 
                            costs_model1['watertap_capex_pipe_pump_cost_pct'] + 
                            costs_model1['watertap_capex_electrical_cost_pct']),
        'Other (capex)': costs_model1['watertap_capex_shipping_cost_pct']
    }

    # WaterTAP Model 1 operating cost breakdown percentages
    opex_breakdown_model1 = {
        'Precipitated salts processing (opex)': costs_model1['watertap_opex_solids_handling_pct'],
        'Government agreements': costs_model1['watertap_opex_government_agreements_pct'],
        'Electricity': costs_model1['watertap_opex_electricity_pct'],
        'Maintenance-labor-chemical': costs_model1['watertap_opex_maintenance_labor_chemical_pct'],
        'Shipping': costs_model1['watertap_opex_shipping_pct'],
        'Liner replacement': costs_model1['watertap_opex_liner_replacement_pct']
    }

    # WaterTAP Model 2 capital cost breakdown percentages (reorganized to match categories)
    capex_breakdown_model2 = {
        'Evaporation ponds': (costs_model2['watertap_capex_liner_cost_pct'] + 
                             costs_model2['watertap_capex_dike_cost_pct'] + 
                             costs_model2['watertap_capex_land_clearing_cost_pct'] + 
                             costs_model2['watertap_capex_road_cost_pct']),
        'Precipitated salts processing': costs_model2['watertap_capex_solids_handling_pct'],
        'Extraction wells': (costs_model2['watertap_capex_well_cost_pct'] + 
                            costs_model2['watertap_capex_pipe_pump_cost_pct'] + 
                            costs_model2['watertap_capex_electrical_cost_pct']),
        'Other (capex)': costs_model2['watertap_capex_shipping_cost_pct']
    }

    # WaterTAP Model 2 operating cost breakdown percentages
    opex_breakdown_model2 = {
        'Precipitated salts processing (opex)': costs_model2['watertap_opex_solids_handling_pct'],
        'Government agreements': costs_model2['watertap_opex_government_agreements_pct'],
        'Electricity': costs_model2['watertap_opex_electricity_pct'],
        'Maintenance-labor-chemical': costs_model2['watertap_opex_maintenance_labor_chemical_pct'],
        'Shipping': costs_model2['watertap_opex_shipping_pct'],
        'Liner replacement': costs_model2['watertap_opex_liner_replacement_pct'],
        'Dye': costs_model2['watertap_opex_dye_pct']
    }

    # Calculate actual values for each category for Model 1
    capex_values_model1 = [
        (costs_model1['watertap_capex_liner_cost'] + 
         costs_model1['watertap_capex_dike_cost'] + 
         costs_model1['watertap_capex_land_clearing_cost'] + 
         costs_model1['watertap_capex_road_cost']),  # Evaporation ponds
        costs_model1['watertap_capex_solids_handling'],  # Precipitated salts processing
        (costs_model1['watertap_capex_well_cost'] + 
         costs_model1['watertap_capex_pipe_pump_cost'] + 
         costs_model1['watertap_capex_electrical_cost']),  # Extraction wells
        costs_model1['watertap_capex_shipping_cost']  # Other (capex)
    ]

    opex_values_model1 = [
        costs_model1['watertap_opex_solids_handling'],
        costs_model1['watertap_opex_government_agreements'],
        costs_model1['watertap_opex_electricity'],
        costs_model1['watertap_opex_maintenance_labor_chemical'],
        costs_model1['watertap_opex_shipping'],
        costs_model1['watertap_opex_liner_replacement']
    ]

    # Calculate actual values for each category for Model 2
    capex_values_model2 = [
        (costs_model2['watertap_capex_liner_cost'] + 
         costs_model2['watertap_capex_dike_cost'] + 
         costs_model2['watertap_capex_land_clearing_cost'] + 
         costs_model2['watertap_capex_road_cost']),  # Evaporation ponds
        costs_model2['watertap_capex_solids_handling'],  # Precipitated salts processing
        (costs_model2['watertap_capex_well_cost'] + 
         costs_model2['watertap_capex_pipe_pump_cost'] + 
         costs_model2['watertap_capex_electrical_cost']),  # Extraction wells
        costs_model2['watertap_capex_shipping_cost']  # Other (capex)
    ]

    opex_values_model2 = [
        costs_model2['watertap_opex_solids_handling'],
        costs_model2['watertap_opex_government_agreements'],
        costs_model2['watertap_opex_electricity'],
        costs_model2['watertap_opex_maintenance_labor_chemical'],
        costs_model2['watertap_opex_shipping'],
        costs_model2['watertap_opex_liner_replacement'],
        costs_model2['watertap_opex_dye']
    ]

    # Colors for different categories using viridis color scheme
    # Capex colors: viridis blues (distinct from opex)
    capex_colors = ['#453781', '#6d5cb7', '#9787da', '#cac0f1']

    # Opex colors: viridis greens/yellows (distinct from capex)
    opex_colors = ['#287D8E', '#42a6bb', '#58c3da', '#77d8ec', '#a1e8f7', '#b9eef9', '#d4f4f9']

    # Revenue color: viridis purple (distinct from capex and opex)
    revenue_color = '#3CBB75'
    dot_color = '#DCE319'

    # Set up the plots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7, 4))
    ax1.set_frame_on(False)
    ax2.set_frame_on(False)

    # Add a common title above both plots
    fig.suptitle('Impact of enhancement dye on lithium brine costs', fontsize=16, fontweight='bold', y=0.95)

    # Width of bar
    width = 0.15
    x_model1 = 0.1
    x_model2 = 0.1

    # Create stacked bars for WaterTAP Model 1 (left plot)
    bottom = 0
    capex_bars_model1 = []
    for i, (category, value) in enumerate(zip(capex_breakdown_model1.keys(), capex_values_model1)):
        bar = ax1.bar(x_model1, value, width, bottom=bottom, label=category, color=capex_colors[i])
        capex_bars_model1.append(bar)
        bottom += value

    # Create stacked bars for operating costs (on top of capital costs)
    opex_bars_model1 = []
    for i, (category, value) in enumerate(zip(opex_breakdown_model1.keys(), opex_values_model1)):
        bar = ax1.bar(x_model1, value, width, bottom=bottom, label=category, color=opex_colors[i])
        opex_bars_model1.append(bar)
        bottom += value

    # Plot revenue as negative bar below the x-axis
    revenue_bar_model1 = ax1.bar(x_model1, -revenue_model1, width, label='Precipitated salts revenue', color=revenue_color)

    # Calculate and add levelized cost dot
    levelized_cost_model1 = total_capex_model1 + total_opex_model1 - revenue_model1
    ax1.scatter(x_model1, levelized_cost_model1, color=dot_color, s=70, label='Levelized cost of Li$^+$ brine', zorder=5)

    # Create stacked bars for WaterTAP Model 2 (right plot)
    bottom = 0
    capex_bars_model2 = []
    for i, (category, value) in enumerate(zip(capex_breakdown_model2.keys(), capex_values_model2)):
        bar = ax2.bar(x_model2, value, width, bottom=bottom, label=category, color=capex_colors[i])
        capex_bars_model2.append(bar)
        bottom += value

    # Create stacked bars for operating costs (on top of capital costs)
    opex_bars_model2 = []
    for i, (category, value) in enumerate(zip(opex_breakdown_model2.keys(), opex_values_model2)):
        bar = ax2.bar(x_model2, value, width, bottom=bottom, label=category, color=opex_colors[i])
        opex_bars_model2.append(bar)
        bottom += value

    # Plot revenue as negative bar below the x-axis
    revenue_bar_model2 = ax2.bar(x_model2, -revenue_model2, width, label='Precipitated salts revenue', color=revenue_color)

    # Calculate and add levelized cost dot
    levelized_cost_model2 = total_capex_model2 + total_opex_model2 - revenue_model2
    ax2.scatter(x_model2, levelized_cost_model2, color=dot_color, s=70, label='Levelized cost of Li$^+$ brine', zorder=5)

    # Calculate overall y-limits for both plots
    total_costs_model1 = total_capex_model1 + total_opex_model1
    total_costs_model2 = total_capex_model2 + total_opex_model2

    y_min_overall = min(-revenue_model1, -revenue_model2) * 1.2
    y_max_overall = max(total_costs_model1, total_costs_model2, levelized_cost_model1, levelized_cost_model2) * 1.1

    # Customize left plot (WaterTAP Model 1)
    ax1.set_ylabel('Cost (USD_2025/Mt Li$^+$)', fontsize=11)
    ax1.set_xticks([x_model1])
    ax1.set_xticklabels(['Without dye'], fontsize=12)
    ax1.tick_params(axis='both', labelsize=10)
    ax1.set_xlim(0, 0.5)
    ax1.set_ylim(y_min_overall, y_max_overall)
    ax1.axhline(0, color='black', linewidth=1)

    # Add levelized cost y-tick labels
    current_yticks = list(ax1.get_yticks())
    current_yticklabels = [f'${tick:.0f}' for tick in current_yticks]
    if len(current_yticks) >= 2:
        spacings = np.diff(sorted(current_yticks))
        median_spacing = np.median(spacings)
        tolerance = 0.5 * median_spacing
    else:
        tolerance = 0
    if len(current_yticks) > 0:
        diffs = [abs(t - levelized_cost_model1) for t in current_yticks]
        nearest_idx = int(np.argmin(diffs))
        if diffs[nearest_idx] <= tolerance:
            current_yticks.pop(nearest_idx)
            current_yticklabels.pop(nearest_idx)
    current_yticks.append(levelized_cost_model1)
    current_yticklabels.append(f'${levelized_cost_model1:.0f}')
    ax1.set_yticks(current_yticks)
    ax1.set_yticklabels(current_yticklabels)

    # Add legend for Model 1 plot with headers
    legend_handles = []
    legend_labels = []

    # Add capital costs header
    capex_header = Line2D([0], [0], color='none', marker='s', markersize=0, label='CAPITAL COSTS')
    legend_handles.append(capex_header)
    legend_labels.append('CAPITAL COSTS')

    # Add capital cost items
    for i, (category, value) in enumerate(zip(capex_breakdown_model1.keys(), capex_values_model1)):
        legend_handles.append(capex_bars_model1[i])
        legend_labels.append(category)

    # Add operating costs header
    opex_header = Line2D([0], [0], color='none', marker='s', markersize=0, label='OPERATING COSTS')
    legend_handles.append(opex_header)
    legend_labels.append('OPERATING COSTS')

    # Add operating cost items
    for i, (category, value) in enumerate(zip(opex_breakdown_model1.keys(), opex_values_model1)):
        legend_handles.append(opex_bars_model1[i])
        legend_labels.append(category)

    # Add other header
    other_header = Line2D([0], [0], color='none', marker='s', markersize=0, label='OTHER')
    legend_handles.append(other_header)
    legend_labels.append('OTHER')

    # Add revenue and levelized cost
    legend_handles.extend([revenue_bar_model1, ax1.collections[0]])
    legend_labels.extend(['Precipitated salts revenue', 'Levelized cost of Li$^+$ brine'])

    ax1.legend(legend_handles, legend_labels, loc='upper right', frameon=True, fancybox=True, shadow=True, fontsize=8)

    # Grid for better readability
    ax1.grid(axis='y', alpha=0.3, linestyle='--')

    # Right plot (WaterTAP Model 2)
    ax2.set_ylabel('Cost (USD_2025/Mt Li$^+$)', fontsize=11)
    ax2.set_xticks([x_model2])
    ax2.set_xticklabels(['With dye'], fontsize=12)
    ax2.tick_params(axis='both', labelsize=10)
    ax2.set_xlim(0, 0.5)
    ax2.set_ylim(y_min_overall, y_max_overall)
    ax2.axhline(0, color='black', linewidth=1)

    # Add levelized cost y-tick labels
    current_yticks = list(ax2.get_yticks())
    current_yticklabels = [f'${tick:.0f}' for tick in current_yticks]
    if len(current_yticks) >= 2:
        spacings = np.diff(sorted(current_yticks))
        median_spacing = np.median(spacings)
        tolerance = 0.5 * median_spacing
    else:
        tolerance = 0
    if len(current_yticks) > 0:
        diffs = [abs(t - levelized_cost_model2) for t in current_yticks]
        nearest_idx = int(np.argmin(diffs))
        if diffs[nearest_idx] <= tolerance:
            current_yticks.pop(nearest_idx)
            current_yticklabels.pop(nearest_idx)
    current_yticks.append(levelized_cost_model2)
    current_yticklabels.append(f'${levelized_cost_model2:.0f}')
    ax2.set_yticks(current_yticks)
    ax2.set_yticklabels(current_yticklabels)

    # Add legend for Model 2 plot with headers
    legend_handles = []
    legend_labels = []

    # Add capital costs header
    capex_header = Line2D([0], [0], color='none', marker='s', markersize=0, label='CAPITAL COSTS')
    legend_handles.append(capex_header)
    legend_labels.append('CAPITAL COSTS')

    # Add capital cost items
    for i, (category, value) in enumerate(zip(capex_breakdown_model2.keys(), capex_values_model2)):
        legend_handles.append(capex_bars_model2[i])
        legend_labels.append(category)

    # Add operating costs header
    opex_header = Line2D([0], [0], color='none', marker='s', markersize=0, label='OPERATING COSTS')
    legend_handles.append(opex_header)
    legend_labels.append('OPERATING COSTS')

    # Add operating cost items
    for i, (category, value) in enumerate(zip(opex_breakdown_model2.keys(), opex_values_model2)):
        legend_handles.append(opex_bars_model2[i])
        legend_labels.append(category)

    # Add other header
    other_header = Line2D([0], [0], color='none', marker='s', markersize=0, label='OTHER')
    legend_handles.append(other_header)
    legend_labels.append('OTHER')

    # Add revenue and levelized cost
    legend_handles.extend([revenue_bar_model2, ax2.collections[0]])
    legend_labels.extend(['Precipitated salts revenue', 'Levelized cost of Li$^+$ brine'])

    ax2.legend(legend_handles, legend_labels, loc='upper right', frameon=True, fancybox=True, shadow=True, fontsize=8)

    # Grid for better readability
    ax2.grid(axis='y', alpha=0.3, linestyle='--')

    # Adjust layout
    plt.tight_layout()

    # Draw dotted lines at levelized costs within each subplot
    ax1.axhline(levelized_cost_model1, color='black', linestyle=':', linewidth=2, alpha=0.7, zorder=1)
    ax2.axhline(levelized_cost_model2, color='black', linestyle=':', linewidth=2, alpha=0.7, zorder=1)

    return fig, (ax1, ax2)

def print_cost_breakdown(costs_model1, costs_model2):
    """Print the cost breakdown for both models.
    
    Args:
        costs_model1 (dict): Dictionary containing Model 1 cost values
        costs_model2 (dict): Dictionary containing Model 2 cost values
    """
    # WaterTAP Model 1 data
    total_capex_model1 = costs_model1['watertap_capex_total']
    total_opex_model1 = costs_model1['watertap_opex_total']
    revenue_model1 = costs_model1['watertap_revenue']
    levelized_cost_model1 = total_capex_model1 + total_opex_model1 - revenue_model1

    # WaterTAP Model 2 data
    total_capex_model2 = costs_model2['watertap_capex_total']
    total_opex_model2 = costs_model2['watertap_opex_total']
    revenue_model2 = costs_model2['watertap_revenue']
    levelized_cost_model2 = total_capex_model2 + total_opex_model2 - revenue_model2

    # Industry capex breakdown
    capex_breakdown_model1 = {
        'Evaporation ponds': (costs_model1['watertap_capex_liner_cost_pct'] + 
                             costs_model1['watertap_capex_dike_cost_pct'] + 
                             costs_model1['watertap_capex_land_clearing_cost_pct'] + 
                             costs_model1['watertap_capex_road_cost_pct']),
        'Precipitated salts processing': costs_model1['watertap_capex_solids_handling_pct'],
        'Extraction wells': (costs_model1['watertap_capex_well_cost_pct'] + 
                            costs_model1['watertap_capex_pipe_pump_cost_pct'] + 
                            costs_model1['watertap_capex_electrical_cost_pct']),
        'Other (capex)': costs_model1['watertap_capex_shipping_cost_pct']
    }

    # Industry opex breakdown
    opex_breakdown_model1 = {
        'Precipitated salts processing (opex)': costs_model1['watertap_opex_solids_handling_pct'],
        'Government agreements': costs_model1['watertap_opex_government_agreements_pct'],
        'Electricity': costs_model1['watertap_opex_electricity_pct'],
        'Maintenance-labor-chemical': costs_model1['watertap_opex_maintenance_labor_chemical_pct'],
        'Shipping': costs_model1['watertap_opex_shipping_pct'],
        'Liner replacement': costs_model1['watertap_opex_liner_replacement_pct']
    }

    # WaterTAP capex breakdown
    capex_breakdown_model2 = {
        'Evaporation ponds': (costs_model2['watertap_capex_liner_cost_pct'] + 
                             costs_model2['watertap_capex_dike_cost_pct'] + 
                             costs_model2['watertap_capex_land_clearing_cost_pct'] + 
                             costs_model2['watertap_capex_road_cost_pct']),
        'Precipitated salts processing': costs_model2['watertap_capex_solids_handling_pct'],
        'Extraction wells': (costs_model2['watertap_capex_well_cost_pct'] + 
                            costs_model2['watertap_capex_pipe_pump_cost_pct'] + 
                            costs_model2['watertap_capex_electrical_cost_pct']),
        'Other (capex)': costs_model2['watertap_capex_shipping_cost_pct']
    }

    # WaterTAP opex breakdown
    opex_breakdown_model2 = {
        'Precipitated salts processing (opex)': costs_model2['watertap_opex_solids_handling_pct'],
        'Government agreements': costs_model2['watertap_opex_government_agreements_pct'],
        'Electricity': costs_model2['watertap_opex_electricity_pct'],
        'Maintenance-labor-chemical': costs_model2['watertap_opex_maintenance_labor_chemical_pct'],
        'Shipping': costs_model2['watertap_opex_shipping_pct'],
        'Liner replacement': costs_model2['watertap_opex_liner_replacement_pct'],
        'Dye': costs_model2['watertap_opex_dye_pct']
    }

    # Calculate actual values for each category for Model 1
    capex_values_model1 = [
        (costs_model1['watertap_capex_liner_cost'] + 
         costs_model1['watertap_capex_dike_cost'] + 
         costs_model1['watertap_capex_land_clearing_cost'] + 
         costs_model1['watertap_capex_road_cost']),  # Evaporation ponds
        costs_model1['watertap_capex_solids_handling'],  # Precipitated salts processing
        (costs_model1['watertap_capex_well_cost'] + 
         costs_model1['watertap_capex_pipe_pump_cost'] + 
         costs_model1['watertap_capex_electrical_cost']),  # Extraction wells
        costs_model1['watertap_capex_shipping_cost']  # Other (capex)
    ]

    opex_values_model1 = [
        costs_model1['watertap_opex_solids_handling'],
        costs_model1['watertap_opex_government_agreements'],
        costs_model1['watertap_opex_electricity'],
        costs_model1['watertap_opex_maintenance_labor_chemical'],
        costs_model1['watertap_opex_shipping'],
        costs_model1['watertap_opex_liner_replacement']
    ]

    # Calculate actual values for each category for Model 2
    capex_values_model2 = [
        (costs_model2['watertap_capex_liner_cost'] + 
         costs_model2['watertap_capex_dike_cost'] + 
         costs_model2['watertap_capex_land_clearing_cost'] + 
         costs_model2['watertap_capex_road_cost']),  # Evaporation ponds
        costs_model2['watertap_capex_solids_handling'],  # Precipitated salts processing
        (costs_model2['watertap_capex_well_cost'] + 
         costs_model2['watertap_capex_pipe_pump_cost'] + 
         costs_model2['watertap_capex_electrical_cost']),  # Extraction wells
        costs_model2['watertap_capex_shipping_cost']  # Other (capex)
    ]

    opex_values_model2 = [
        costs_model2['watertap_opex_solids_handling'],
        costs_model2['watertap_opex_government_agreements'],
        costs_model2['watertap_opex_electricity'],
        costs_model2['watertap_opex_maintenance_labor_chemical'],
        costs_model2['watertap_opex_shipping'],
        costs_model2['watertap_opex_liner_replacement'],
        costs_model2['watertap_opex_dye']
    ]

    print(f"Inflation factor applied: 1.00")
    print(f"Annual lithium production (Q): {costs_model1['Q']:.0f} mt/year")
    print(f"WaterTAP Model 1 total LCOLi: ${costs_model1['watertap_total']:.0f}/mt Li")
    print(f"WaterTAP Model 2 total LCOLi: ${costs_model2['watertap_total']:.0f}/mt Li")
    print("="*50)

    print("\nWATERTAP MODEL 1:")
    print("Capital Costs Breakdown:")
    for category, value in zip(capex_breakdown_model1.keys(), capex_values_model1):
        print(f"  {category}: ${value:.0f} ({capex_breakdown_model1[category]*100:.1f}%)")

    print(f"\nTotal Capital Costs: ${total_capex_model1:.0f}")

    print("\nOperating Costs Breakdown:")
    for category, value in zip(opex_breakdown_model1.keys(), opex_values_model1):
        print(f"  {category}: ${value:.0f} ({opex_breakdown_model1[category]*100:.1f}%)")

    print(f"\nTotal Operating Costs: ${total_opex_model1:.0f}")
    print(f"Revenue: ${revenue_model1:.0f}")
    print(f"Levelized Cost: ${levelized_cost_model1:.0f}")

    print("\n" + "="*50)

    print("\nWATERTAP MODEL 2:")
    print("Capital Costs Breakdown:")
    for category, value in zip(capex_breakdown_model2.keys(), capex_values_model2):
        print(f"  {category}: ${value:.0f} ({capex_breakdown_model2[category]*100:.1f}%)")

    print(f"\nTotal Capital Costs: ${total_capex_model2:.0f}")

    print("\nOperating Costs Breakdown:")
    for category, value in zip(opex_breakdown_model2.keys(), opex_values_model2):
        print(f"  {category}: ${value:.0f} ({opex_breakdown_model2[category]*100:.1f}%)")

    print(f"\nTotal Operating Costs: ${total_opex_model2:.0f}")
    print(f"Revenue: ${revenue_model2:.0f}")
    print(f"Levelized Cost: ${levelized_cost_model2:.0f}")


def main():
    """Main function to run the cost analysis and create plots."""
    # Set inflation factor (1.0 for no inflation adjustment)
    inflation_factor = 1.0
    costs_model1 = calculate_lithium_costs_model1(inflation_factor)
    costs_model2 = calculate_lithium_costs_model2(inflation_factor)
    
    # Create and display the cost breakdown plot
    fig, axes = create_cost_breakdown_plot(costs_model1, costs_model2)
    plt.show()

    # Print detailed cost summary
    print_cost_breakdown(costs_model1, costs_model2)


if __name__ == "__main__":
    main()