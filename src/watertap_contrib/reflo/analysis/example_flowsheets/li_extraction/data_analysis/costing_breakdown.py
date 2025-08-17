"""Results comparison visualization for lithium extraction flowsheet.

Creates cost breakdown visualization for industry report data with detailed categories.
"""

import matplotlib.pyplot as plt
import numpy as np

def calculate_lithium_costs():
    """
    Calculate lithium costs based on SQM's 2020 numbers and WaterTAP's 2022 numbers.
    Translated from MATLAB code.
    """
    # SQM's 2020 numbers
    sqm_operating_total = 500000000  # USD_2020/year
    sqm_capital_watertap_factor = (27+17+13+7+(27+17+13+7)/(28+27+17+13+7)*8)/100  # fraction of SQM's capital cost covered by WaterTAP
    sqm_operating_watertap_factor = sqm_capital_watertap_factor*(.25+.18+.14+.12+.04)+.14+.04  # fraction of SQM's operating cost covered by WaterTAP
    fraction = .04/(sqm_operating_watertap_factor-.18*sqm_capital_watertap_factor)
    sqm_operating_watertap_factor_capex = .18*sqm_capital_watertap_factor/sqm_operating_watertap_factor  # fraction of SQM's operating cost (covered by WaterTAP) attributed to depreciation
    sqm_operating_watertap = sqm_operating_total * sqm_operating_watertap_factor  # SQM's operating cost covered by WaterTAP

    sqm_capital_solids_factor = (17+7+(17+7)/(28+27+17+13+7)*8)/100  # fraction of SQM's capital cost for solids handling
    sqm_operating_solids_factor = sqm_capital_watertap_factor*(.25+.18+.14+.12+.04)  # fraction of SQM's operating costs for solids handling
    sqm_operating_solids = sqm_operating_total * sqm_operating_solids_factor  # SQM's operating cost for solids handling
    sqm_revenue_solids = 209300000  # USD_2020/year

    utilization_factor = 0.98  # factor

    # Q calculation
    inlet_li_conc = 2  # g/kg
    li_recovery = 0.6  # fraction
    inlet_flow_vol = 1.461  # m^3/s (2020)
    inlet_dens = 1227  # kg/m^3
    li_outflow = inlet_li_conc * li_recovery * inlet_flow_vol * inlet_dens / 1000  # kg/s
    Q = li_outflow * 3600 * 24 * 365 / 1000  # mt/year

    # Results
    LCOLi_sqm_total = (sqm_operating_total - sqm_revenue_solids) / (utilization_factor * Q)
    LCOLi_sqm_watertap = (sqm_operating_watertap - sqm_revenue_solids) / (utilization_factor * Q)  # $/mt Li

    LCOLi_sqm_watertap_capex = sqm_operating_watertap * sqm_operating_watertap_factor_capex / (utilization_factor * Q)
    LCOLi_sqm_watertap_opex = sqm_operating_watertap * (1 - sqm_operating_watertap_factor_capex) / (utilization_factor * Q)
    LCOLi_sqm_watertap_revenue = sqm_revenue_solids / (utilization_factor * Q)

    # WaterTAP's numbers for 2022's production, translated to USD_2020. Costs should be a little higher
    crf = 0.10368970512  # capital recovery factor
    watertap_capex = 684330531
    watertap_opex = 79228708+177035130
    watertap_revenue = 177035130

    # Q calculation
    inlet_flow_vol = 1.461  # m^3/s
    li_outflow = inlet_li_conc * li_recovery * inlet_flow_vol * inlet_dens / 1000  # kg/s
    Q = li_outflow * 3600 * 24 * 365 / 1000  # mt/year

    LCOLi_watertap_total = (crf * watertap_capex + watertap_opex - watertap_revenue) / (utilization_factor * Q)  # $/mt Li
    LCOLi_watertap_capex = (crf * watertap_capex) / (utilization_factor * Q)
    LCOLi_watertap_opex = watertap_opex / (utilization_factor * Q)
    LCOLi_watertap_revenue = watertap_revenue / (utilization_factor * Q)
    
    # Raw category values for Industry report (SQM) capex (total costs in USD millions)
    # You can modify these values to change the cost breakdown
    industry_capex_evaporation_ponds_raw = 193.8  # Million USD
    industry_capex_solids_handling_raw = 172.5   # Million USD
    industry_capex_extraction_wells_raw = 93.4   # Million USD
    industry_capex_other_raw = 40.0              # Million USD
    
    # Calculate percentages for industry capex
    industry_capex_total_raw = (industry_capex_evaporation_ponds_raw + industry_capex_solids_handling_raw + 
                               industry_capex_extraction_wells_raw + industry_capex_other_raw)
    industry_capex_evaporation_ponds_pct = industry_capex_evaporation_ponds_raw / industry_capex_total_raw
    industry_capex_solids_handling_pct = industry_capex_solids_handling_raw / industry_capex_total_raw
    industry_capex_extraction_wells_pct = industry_capex_extraction_wells_raw / industry_capex_total_raw
    industry_capex_other_pct = industry_capex_other_raw / industry_capex_total_raw
    
    # Raw category values for Industry report (SQM) opex (total costs in USD millions per year)
    # You can modify these values to change the cost breakdown
    industry_opex_consumables_raw = 154.6        # Million USD/year
    industry_opex_government_agreements_raw = 124.4  # Million USD/year
    industry_opex_contractor_works_raw = 86.6    # Million USD/year
    industry_opex_employee_benefits_raw = 74.2   # Million USD/year
    industry_opex_shipping_raw = 35.6            # Million USD/year
    industry_opex_other_raw = 24.8               # Million USD/year
    
    # Calculate percentages for industry opex
    industry_opex_total_raw = (industry_opex_consumables_raw + industry_opex_government_agreements_raw + 
                              industry_opex_contractor_works_raw + industry_opex_employee_benefits_raw + 
                              industry_opex_shipping_raw + industry_opex_other_raw)
    industry_opex_consumables_pct = industry_opex_consumables_raw / industry_opex_total_raw
    industry_opex_government_agreements_pct = industry_opex_government_agreements_raw / industry_opex_total_raw
    industry_opex_contractor_works_pct = industry_opex_contractor_works_raw / industry_opex_total_raw
    industry_opex_employee_benefits_pct = industry_opex_employee_benefits_raw / industry_opex_total_raw
    industry_opex_shipping_pct = industry_opex_shipping_raw / industry_opex_total_raw
    industry_opex_other_pct = industry_opex_other_raw / industry_opex_total_raw
    
    # Raw category values for WaterTAP capex (total costs in USD millions)
    # You can modify these values to change the cost breakdown
    watertap_capex_liner_cost_raw = 233.4           # Million USD
    watertap_capex_well_cost_raw = 104.6            # Million USD
    watertap_capex_pipe_pump_cost_raw = 104.6       # Million USD
    watertap_capex_dike_cost_raw = 82.4             # Million USD
    watertap_capex_shipping_cost_raw = 49.4         # Million USD
    watertap_capex_electrical_cost_raw = 38.9       # Million USD
    watertap_capex_land_clearing_cost_raw = 14.2    # Million USD
    watertap_capex_road_cost_raw = 7.1              # Million USD
    
    # Calculate percentages for WaterTAP capex
    watertap_capex_total_raw = (watertap_capex_liner_cost_raw + watertap_capex_well_cost_raw + 
                               watertap_capex_pipe_pump_cost_raw + watertap_capex_dike_cost_raw + 
                               watertap_capex_shipping_cost_raw + watertap_capex_electrical_cost_raw + 
                               watertap_capex_land_clearing_cost_raw + watertap_capex_road_cost_raw)
    watertap_capex_liner_cost_pct = watertap_capex_liner_cost_raw / watertap_capex_total_raw
    watertap_capex_well_cost_pct = watertap_capex_well_cost_raw / watertap_capex_total_raw
    watertap_capex_pipe_pump_cost_pct = watertap_capex_pipe_pump_cost_raw / watertap_capex_total_raw
    watertap_capex_dike_cost_pct = watertap_capex_dike_cost_raw / watertap_capex_total_raw
    watertap_capex_shipping_cost_pct = watertap_capex_shipping_cost_raw / watertap_capex_total_raw
    watertap_capex_electrical_cost_pct = watertap_capex_electrical_cost_raw / watertap_capex_total_raw
    watertap_capex_land_clearing_cost_pct = watertap_capex_land_clearing_cost_raw / watertap_capex_total_raw
    watertap_capex_road_cost_pct = watertap_capex_road_cost_raw / watertap_capex_total_raw
    
    # Raw category values for WaterTAP opex (total costs in USD millions per year)
    # You can modify these values to change the cost breakdown
    watertap_opex_electricity_raw = 44.2            # Million USD/year
    watertap_opex_solids_handling_raw = 95.6        # Million USD/year
    watertap_opex_government_agreements_raw = 58.1  # Million USD/year
    watertap_opex_shipping_raw = 25.3               # Million USD/year
    watertap_opex_maintenance_labor_chemical_raw = 20.5  # Million USD/year
    watertap_opex_liner_replacement_raw = 11.7       # Million USD/year
    
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
    
    # Apply percentages to LCOLi values to get final category values
    industry_capex_total = LCOLi_sqm_watertap_capex
    industry_opex_total = LCOLi_sqm_watertap_opex
    watertap_capex_total = LCOLi_watertap_capex
    watertap_opex_total = LCOLi_watertap_opex
    
    return {
        'sqm_total': LCOLi_sqm_total,
        'sqm_watertap': LCOLi_sqm_watertap,
        'sqm_watertap_capex': LCOLi_sqm_watertap_capex,
        'sqm_watertap_opex': LCOLi_sqm_watertap_opex,
        'sqm_watertap_revenue': LCOLi_sqm_watertap_revenue,
        'watertap_total': LCOLi_watertap_total,
        'watertap_capex': LCOLi_watertap_capex,
        'watertap_opex': LCOLi_watertap_opex,
        'watertap_revenue': LCOLi_watertap_revenue,
        'Q': Q,
        # Industry capex categories (LCOLi totals and percentages)
        'industry_capex_total': industry_capex_total,
        'industry_capex_evaporation_ponds': industry_capex_total * industry_capex_evaporation_ponds_pct,
        'industry_capex_solids_handling': industry_capex_total * industry_capex_solids_handling_pct,
        'industry_capex_extraction_wells': industry_capex_total * industry_capex_extraction_wells_pct,
        'industry_capex_other': industry_capex_total * industry_capex_other_pct,
        'industry_capex_evaporation_ponds_pct': industry_capex_evaporation_ponds_pct,
        'industry_capex_solids_handling_pct': industry_capex_solids_handling_pct,
        'industry_capex_extraction_wells_pct': industry_capex_extraction_wells_pct,
        'industry_capex_other_pct': industry_capex_other_pct,
        # Industry opex categories (LCOLi totals and percentages)
        'industry_opex_total': industry_opex_total,
        'industry_opex_consumables': industry_opex_total * industry_opex_consumables_pct,
        'industry_opex_government_agreements': industry_opex_total * industry_opex_government_agreements_pct,
        'industry_opex_contractor_works': industry_opex_total * industry_opex_contractor_works_pct,
        'industry_opex_employee_benefits': industry_opex_total * industry_opex_employee_benefits_pct,
        'industry_opex_shipping': industry_opex_total * industry_opex_shipping_pct,
        'industry_opex_other': industry_opex_total * industry_opex_other_pct,
        'industry_opex_consumables_pct': industry_opex_consumables_pct,
        'industry_opex_government_agreements_pct': industry_opex_government_agreements_pct,
        'industry_opex_contractor_works_pct': industry_opex_contractor_works_pct,
        'industry_opex_employee_benefits_pct': industry_opex_employee_benefits_pct,
        'industry_opex_shipping_pct': industry_opex_shipping_pct,
        'industry_opex_other_pct': industry_opex_other_pct,
        # WaterTAP capex categories (LCOLi totals and percentages)
        'watertap_capex_total': watertap_capex_total,
        'watertap_capex_liner_cost': watertap_capex_total * watertap_capex_liner_cost_pct,
        'watertap_capex_well_cost': watertap_capex_total * watertap_capex_well_cost_pct,
        'watertap_capex_pipe_pump_cost': watertap_capex_total * watertap_capex_pipe_pump_cost_pct,
        'watertap_capex_dike_cost': watertap_capex_total * watertap_capex_dike_cost_pct,
        'watertap_capex_shipping_cost': watertap_capex_total * watertap_capex_shipping_cost_pct,
        'watertap_capex_electrical_cost': watertap_capex_total * watertap_capex_electrical_cost_pct,
        'watertap_capex_land_clearing_cost': watertap_capex_total * watertap_capex_land_clearing_cost_pct,
        'watertap_capex_road_cost': watertap_capex_total * watertap_capex_road_cost_pct,
        'watertap_capex_liner_cost_pct': watertap_capex_liner_cost_pct,
        'watertap_capex_well_cost_pct': watertap_capex_well_cost_pct,
        'watertap_capex_pipe_pump_cost_pct': watertap_capex_pipe_pump_cost_pct,
        'watertap_capex_dike_cost_pct': watertap_capex_dike_cost_pct,
        'watertap_capex_shipping_cost_pct': watertap_capex_shipping_cost_pct,
        'watertap_capex_electrical_cost_pct': watertap_capex_electrical_cost_pct,
        'watertap_capex_land_clearing_cost_pct': watertap_capex_land_clearing_cost_pct,
        'watertap_capex_road_cost_pct': watertap_capex_road_cost_pct,
        # WaterTAP opex categories (LCOLi totals and percentages)
        'watertap_opex_total': watertap_opex_total,
        'watertap_opex_electricity': watertap_opex_total * watertap_opex_electricity_pct,
        'watertap_opex_solids_handling': watertap_opex_total * watertap_opex_solids_handling_pct,
        'watertap_opex_government_agreements': watertap_opex_total * watertap_opex_government_agreements_pct,
        'watertap_opex_shipping': watertap_opex_total * watertap_opex_shipping_pct,
        'watertap_opex_maintenance_labor_chemical': watertap_opex_total * watertap_opex_maintenance_labor_chemical_pct,
        'watertap_opex_liner_replacement': watertap_opex_total * watertap_opex_liner_replacement_pct,
        'watertap_opex_electricity_pct': watertap_opex_electricity_pct,
        'watertap_opex_solids_handling_pct': watertap_opex_solids_handling_pct,
        'watertap_opex_government_agreements_pct': watertap_opex_government_agreements_pct,
        'watertap_opex_shipping_pct': watertap_opex_shipping_pct,
        'watertap_opex_maintenance_labor_chemical_pct': watertap_opex_maintenance_labor_chemical_pct,
        'watertap_opex_liner_replacement_pct': watertap_opex_liner_replacement_pct
    }

# Calculate costs
costs = calculate_lithium_costs()
print(f"Annual lithium production (Q): {costs['Q']:.0f} mt/year")
print(f"SQM total LCOLi: ${costs['sqm_total']:.0f}/mt Li")
print(f"SQM WaterTAP LCOLi: ${costs['sqm_watertap']:.0f}/mt Li")
print(f"WaterTAP total LCOLi: ${costs['watertap_total']:.0f}/mt Li")
print("="*50)

# Industry report data (calculated from function)
total_capex_industry = costs['industry_capex_total']
total_opex_industry = costs['industry_opex_total']
revenue_industry = costs['sqm_watertap_revenue']

# WaterTAP model data (calculated from function)
total_capex_watertap = costs['watertap_capex_total']
total_opex_watertap = costs['watertap_opex_total']
revenue_watertap = costs['watertap_revenue']

# Industry report capital cost breakdown percentages (calculated dynamically)
capex_breakdown_industry = {
    'Evaporation ponds': costs['industry_capex_evaporation_ponds_pct'],
    'Solids handling': costs['industry_capex_solids_handling_pct'],
    'Extraction wells': costs['industry_capex_extraction_wells_pct'],
    'Other (capex)': costs['industry_capex_other_pct']
}

# Industry report operating cost breakdown percentages (calculated dynamically)
opex_breakdown_industry = {
    'Consumables': costs['industry_opex_consumables_pct'],
    'Government agreements': costs['industry_opex_government_agreements_pct'],
    'Contractor works': costs['industry_opex_contractor_works_pct'],
    'Employee benefits': costs['industry_opex_employee_benefits_pct'],
    'Shipping': costs['industry_opex_shipping_pct'],
    'Other (opex)': costs['industry_opex_other_pct']
}

# WaterTAP model capital cost breakdown percentages (calculated dynamically)
capex_breakdown_watertap = {
    'Liner cost': costs['watertap_capex_liner_cost_pct'],
    'Well cost': costs['watertap_capex_well_cost_pct'],
    'Pipe and pump cost': costs['watertap_capex_pipe_pump_cost_pct'],
    'Dike cost': costs['watertap_capex_dike_cost_pct'],
    'Shipping cost': costs['watertap_capex_shipping_cost_pct'],
    'Electrical cost': costs['watertap_capex_electrical_cost_pct'],
    'Land clearing cost': costs['watertap_capex_land_clearing_cost_pct'],
    'Road cost': costs['watertap_capex_road_cost_pct']
}

# WaterTAP model operating cost breakdown percentages (calculated dynamically)
opex_breakdown_watertap = {
    'Electricity': costs['watertap_opex_electricity_pct'],
    'Solids handling': costs['watertap_opex_solids_handling_pct'],
    'Government agreements': costs['watertap_opex_government_agreements_pct'],
    'Shipping': costs['watertap_opex_shipping_pct'],
    'Maintenance-labor-chemical': costs['watertap_opex_maintenance_labor_chemical_pct'],
    'Liner replacement': costs['watertap_opex_liner_replacement_pct']
}

# Calculate actual values for each category (using calculated values from function)
capex_values_industry = [
    costs['industry_capex_evaporation_ponds'],
    costs['industry_capex_solids_handling'],
    costs['industry_capex_extraction_wells'],
    costs['industry_capex_other']
]

opex_values_industry = [
    costs['industry_opex_consumables'],
    costs['industry_opex_government_agreements'],
    costs['industry_opex_contractor_works'],
    costs['industry_opex_employee_benefits'],
    costs['industry_opex_shipping'],
    costs['industry_opex_other']
]

capex_values_watertap = [
    costs['watertap_capex_liner_cost'],
    costs['watertap_capex_well_cost'],
    costs['watertap_capex_pipe_pump_cost'],
    costs['watertap_capex_dike_cost'],
    costs['watertap_capex_shipping_cost'],
    costs['watertap_capex_electrical_cost'],
    costs['watertap_capex_land_clearing_cost'],
    costs['watertap_capex_road_cost']
]

opex_values_watertap = [
    costs['watertap_opex_electricity'],
    costs['watertap_opex_solids_handling'],
    costs['watertap_opex_government_agreements'],
    costs['watertap_opex_shipping'],
    costs['watertap_opex_maintenance_labor_chemical'],
    costs['watertap_opex_liner_replacement']
]

# Colors for different categories
capex_colors_industry = ['#3d7aa0', '#4198b5', '#5ba3c2', '#7ab8d1']
opex_colors_industry = ['#610059', '#7a1a6b', '#93347d', '#ac4e8f', '#c568a1', '#de82b3']

capex_colors_watertap = ['#3d7aa0', '#4198b5', '#5ba3c2', '#7ab8d1', '#9acde0', '#bce2f0', '#d6f0f9', '#e6f7fc']
opex_colors_watertap = ['#610059', '#7a1a6b', '#93347d', '#ac4e8f', '#c568a1', '#de82b3']

revenue_color = '#165d54'
dot_color = '#279989'

# Set up the plots
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
ax1.set_frame_on(False)
ax2.set_frame_on(False)

# Width of bar
width = 0.20
x_industry = 0.15
x_watertap = 0.15

# Create stacked bars for industry report (left plot)
bottom = 0
capex_bars_industry = []
for i, (category, value) in enumerate(zip(capex_breakdown_industry.keys(), capex_values_industry)):
    bar = ax1.bar(x_industry, value, width, bottom=bottom, label=category, color=capex_colors_industry[i])
    capex_bars_industry.append(bar)
    bottom += value

# Create stacked bars for operating costs (on top of capital costs)
opex_bars_industry = []
for i, (category, value) in enumerate(zip(opex_breakdown_industry.keys(), opex_values_industry)):
    bar = ax1.bar(x_industry, value, width, bottom=bottom, label=category, color=opex_colors_industry[i])
    opex_bars_industry.append(bar)
    bottom += value

# Plot revenue as negative bar below the x-axis
revenue_bar_industry = ax1.bar(x_industry, -revenue_industry, width, label='Solids revenue', color=revenue_color)

# Calculate and add levelized cost dot
levelized_cost_industry = total_capex_industry + total_opex_industry - revenue_industry
ax1.scatter(x_industry, levelized_cost_industry, color=dot_color, s=100, label='Levelized cost', zorder=5)

# Create stacked bars for WaterTAP model (right plot)
bottom = 0
capex_bars_watertap = []
for i, (category, value) in enumerate(zip(capex_breakdown_watertap.keys(), capex_values_watertap)):
    bar = ax2.bar(x_watertap, value, width, bottom=bottom, label=category, color=capex_colors_watertap[i])
    capex_bars_watertap.append(bar)
    bottom += value

# Create stacked bars for operating costs (on top of capital costs)
opex_bars_watertap = []
for i, (category, value) in enumerate(zip(opex_breakdown_watertap.keys(), opex_values_watertap)):
    bar = ax2.bar(x_watertap, value, width, bottom=bottom, label=category, color=opex_colors_watertap[i])
    opex_bars_watertap.append(bar)
    bottom += value

# Plot revenue as negative bar below the x-axis
revenue_bar_watertap = ax2.bar(x_watertap, -revenue_watertap, width, label='Solids revenue', color=revenue_color)

# Calculate and add levelized cost dot
levelized_cost_watertap = total_capex_watertap + total_opex_watertap - revenue_watertap
ax2.scatter(x_watertap, levelized_cost_watertap, color=dot_color, s=100, label='Levelized cost', zorder=5)

# Customize the plots
# Left plot (Industry report)
ax1.set_ylabel('Cost (USD_2020/Mt Li)', fontsize=11)
ax1.set_title('Industry Report', fontsize=11, fontweight='bold')
ax1.set_xticks([x_industry])
ax1.set_xticklabels(['Industry report'], fontsize=11)
ax1.set_xlim(0, 0.5)  # Set x-axis limits for industry plot

# Calculate overall y-limits for both plots
total_costs_industry = total_capex_industry + total_opex_industry
total_costs_watertap = total_capex_watertap + total_opex_watertap

y_min_overall = min(-revenue_industry, -revenue_watertap) * 1.2
y_max_overall = max(total_costs_industry, total_costs_watertap, levelized_cost_industry, levelized_cost_watertap) * 1.1

# Set same y-limits for both plots
ax1.set_ylim(y_min_overall, y_max_overall)
ax1.axhline(0, color='black', linewidth=1)

# Add legend for industry plot
ax1.set_ylabel('Cost (USD_2020/Mt Li)', fontsize=11)
ax1.legend(loc='upper right', frameon=True, fancybox=True, shadow=True, fontsize=9)

# Grid for better readability
ax1.grid(axis='y', alpha=0.3, linestyle='--')

# Right plot (WaterTAP model)
ax2.set_ylabel('Cost (USD_2020/Mt Li)', fontsize=11)
ax2.set_title('WaterTAP Model', fontsize=11, fontweight='bold')
ax2.set_xticks([x_watertap])
ax2.set_xticklabels(['WaterTAP model'], fontsize=11)
ax2.set_xlim(0, 0.5)  # Set x-axis limits for WaterTAP plot

# Use same y-limits for consistency
ax2.set_ylim(y_min_overall, y_max_overall)
ax2.axhline(0, color='black', linewidth=1)

# Add legend for WaterTAP plot
ax2.legend(loc='upper right', frameon=True, fancybox=True, shadow=True, fontsize=9)

# Grid for better readability
ax2.grid(axis='y', alpha=0.3, linestyle='--')

# Adjust layout
plt.tight_layout()

# Show the plot
plt.show()

# Print calculated values
print("INDUSTRY REPORT:")
print("Capital Costs Breakdown:")
for category, value in zip(capex_breakdown_industry.keys(), capex_values_industry):
    print(f"  {category}: ${value:.0f} ({capex_breakdown_industry[category]*100:.1f}%)")

print(f"\nTotal Capital Costs: ${total_capex_industry:.0f}")

print("\nOperating Costs Breakdown:")
for category, value in zip(opex_breakdown.keys(), opex_values):
    print(f"  {category}: ${value:.0f} ({list(opex_breakdown.values())[list(opex_breakdown.keys()).index(category)]*100:.1f}%)")

print(f"\nTotal Operating Costs: ${total_opex_industry:.0f}")
print(f"Revenue: ${revenue_industry:.0f}")
print(f"Levelized Cost: ${levelized_cost_industry:.0f}")

print("\n" + "="*50)

print("\nWATERTAP MODEL:")
print("Capital Costs Breakdown:")
for category, value in zip(capex_breakdown_watertap.keys(), capex_values_watertap):
    print(f"  {category}: ${value:.0f} ({capex_breakdown_watertap[category]*100:.1f}%)")

print(f"\nTotal Capital Costs: ${total_capex_watertap:.0f}")

print("\nOperating Costs Breakdown:")
for category, value in zip(opex_breakdown_watertap.keys(), opex_values_watertap):
    print(f"  {category}: ${value:.0f} ({opex_breakdown_watertap[category]*100:.1f}%)")

print(f"\nTotal Operating Costs: ${total_opex_watertap:.0f}")
print(f"Revenue: ${revenue_watertap:.0f}")
print(f"Levelized Cost: ${levelized_cost_watertap:.0f}")