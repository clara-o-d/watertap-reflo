"""Results comparison visualization for lithium extraction flowsheet.

Creates cost breakdown visualization for industry report data with viridis color and matching capex categories.
"""

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

def calculate_lithium_costs(inflation_factor=1.0):
    """
    Calculate lithium costs based on SQM's 2020 numbers and WaterTAP's 2020 numbers.
    Translated from MATLAB code.
    
    Args:
        inflation_factor (float): Factor to adjust all costs for inflation (default: 1.0 = no adjustment)
    """
    # Inflation factor to adjust all costs
    # Example: inflation_factor = 1.15 means 15% increase due to inflation
    
    # SQM's 2020 numbers
    sqm_operating_total = 500000000 * inflation_factor  # USD_2020/year
    sqm_capital_watertap_factor = (27+17+13+7+(27+17+13+7)/(28+27+17+13+7)*8)/100  # fraction of SQM's capital cost covered by WaterTAP
    sqm_operating_watertap_factor = sqm_capital_watertap_factor*(.18+.14+.12+.04)+(27+17+13+7)/(28+27+17+13+7)*.25+.14+.05+.06  # fraction of SQM's operating cost covered by WaterTAP
    sqm_operating_watertap_factor_capex = .18*sqm_capital_watertap_factor/sqm_operating_watertap_factor  # fraction of SQM's operating cost (covered by WaterTAP) attributed to depreciation
    sqm_operating_watertap = sqm_operating_total * sqm_operating_watertap_factor  # SQM's operating cost covered by WaterTAP

    sqm_capital_solids_factor = (17+7+(17+7)/(28+27+17+13+7)*8)/100  # fraction of SQM's capital cost for solids handling
    sqm_operating_solids_factor = sqm_capital_solids_factor*(.14+.12+.04) + (17+7)/(28+27+17+13+7)*.25 + .01 + .06  # fraction of SQM's operating costs for solids handling
    sqm_operating_solids = sqm_operating_total * sqm_operating_solids_factor  # SQM's operating cost for solids handling
    print(f"SQM operating cost for solids handling: {sqm_operating_solids:.2f} USD_2020/year")
    sqm_revenue_solids = 209300000 * inflation_factor  # USD_2020/year

    utilization_factor = 0.98  # factor

    # Q calculation
    inlet_li_conc = 2  # g/kg
    li_recovery = 0.6  # fraction
    inlet_flow_vol = 1461  # m^3/s (2020)
    li_outflow = inlet_li_conc * li_recovery * inlet_flow_vol / 1000  # kg/s
    print(f"Li outflow: {li_outflow:.2f} kg/s")
    Q = li_outflow * 3600 * 24 * 365 / 1000  # mt/year

    # Results
    LCOLi_sqm_total = (sqm_operating_total - sqm_revenue_solids) / (utilization_factor * Q)
    LCOLi_sqm_watertap = (sqm_operating_watertap - sqm_revenue_solids) / (utilization_factor * Q)  # $/mt Li

    LCOLi_sqm_watertap_capex = sqm_operating_watertap * sqm_operating_watertap_factor_capex / (utilization_factor * Q)
    LCOLi_sqm_watertap_opex = sqm_operating_watertap * (1 - sqm_operating_watertap_factor_capex) / (utilization_factor * Q)
    LCOLi_sqm_watertap_revenue = sqm_revenue_solids / (utilization_factor * Q)

    # WaterTAP's numbers for 2022's production, translated to USD_2020. Costs should be a little higher
    crf = 0.04  # capital recovery factor
    watertap_capex = 1235990337 * inflation_factor
    watertap_opex = (107009901+209746052) * inflation_factor
    watertap_revenue = 209746052 * inflation_factor

    # Q calculation
    inlet_flow_vol = 1461  # m^3/s
    li_outflow = inlet_li_conc * li_recovery * inlet_flow_vol / 1000  # kg/s
    Q = li_outflow * 3600 * 24 * 365 / 1000  # mt/year

    LCOLi_watertap_total = (crf * watertap_capex + watertap_opex - watertap_revenue) / (utilization_factor * Q)  # $/mt Li
    LCOLi_watertap_capex = (crf * watertap_capex) / (utilization_factor * Q)
    LCOLi_watertap_opex = watertap_opex / (utilization_factor * Q)
    LCOLi_watertap_revenue = watertap_revenue / (utilization_factor * Q)
    
    # Percentages for industry capex
    industry_capex_evaporation_ponds_pct = .27/sqm_capital_watertap_factor
    industry_capex_solids_handling_pct = (.17+.07)/sqm_capital_watertap_factor
    industry_capex_extraction_wells_pct = .13/sqm_capital_watertap_factor
    industry_capex_other_pct = ((27+17+13+7)/(28+27+17+13+7)*8)/100/sqm_capital_watertap_factor
    
    # Percentages for industry opex
    industry_opex_consumables_pct = (27+17+13+7)/(28+27+17+13+7)*.25 / (sqm_operating_watertap_factor * (1 - sqm_operating_watertap_factor_capex))
    industry_opex_government_agreements_pct = .14 / (sqm_operating_watertap_factor * (1 - sqm_operating_watertap_factor_capex))
    industry_opex_contractor_works_pct = sqm_capital_watertap_factor*.14 / (sqm_operating_watertap_factor * (1 - sqm_operating_watertap_factor_capex))
    industry_opex_employee_benefits_pct = sqm_capital_watertap_factor*.12 / (sqm_operating_watertap_factor * (1 - sqm_operating_watertap_factor_capex))
    industry_opex_shipping_pct = .11 / (sqm_operating_watertap_factor * (1 - sqm_operating_watertap_factor_capex))
    industry_opex_other_pct = sqm_capital_watertap_factor*.04 / (sqm_operating_watertap_factor * (1 - sqm_operating_watertap_factor_capex))
    
    # Raw category values for WaterTAP capex (total costs in USD millions)
    # You can modify these values to change the cost breakdown
    watertap_capex_solids_handling_raw = 552.0 * inflation_factor      # Million USD
    watertap_capex_liner_cost_raw = 233.2 * inflation_factor           # Million USD
    watertap_capex_well_cost_raw = 104.7 * inflation_factor            # Million USD
    watertap_capex_pipe_pump_cost_raw = 104.7 * inflation_factor       # Million USD
    watertap_capex_dike_cost_raw = 82.4 * inflation_factor             # Million USD
    watertap_capex_shipping_cost_raw = 49.4 * inflation_factor         # Million USD
    watertap_capex_electrical_cost_raw = 38.9 * inflation_factor       # Million USD
    watertap_capex_land_clearing_cost_raw = 14.2 * inflation_factor    # Million USD
    watertap_capex_road_cost_raw = 7.1 * inflation_factor              # Million USD
    
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
    # You can modify these values to change the cost breakdown
    watertap_opex_electricity_raw = 44.2 * inflation_factor            # Million USD/year
    watertap_opex_solids_handling_raw = 131.9 * inflation_factor        # Million USD/year
    watertap_opex_government_agreements_raw = 70.3 * inflation_factor  # Million USD/year
    watertap_opex_shipping_raw = 20.2 * inflation_factor               # Million USD/year
    watertap_opex_maintenance_labor_chemical_raw = 37.1 * inflation_factor  # Million USD/year
    watertap_opex_liner_replacement_raw = 11.7 * inflation_factor       # Million USD/year
    
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
        'watertap_capex_solids_handling': watertap_capex_total * watertap_capex_solids_handling_pct,
        'watertap_capex_liner_cost': watertap_capex_total * watertap_capex_liner_cost_pct,
        'watertap_capex_well_cost': watertap_capex_total * watertap_capex_well_cost_pct,
        'watertap_capex_pipe_pump_cost': watertap_capex_total * watertap_capex_pipe_pump_cost_pct,
        'watertap_capex_dike_cost': watertap_capex_total * watertap_capex_dike_cost_pct,
        'watertap_capex_shipping_cost': watertap_capex_total * watertap_capex_shipping_cost_pct,
        'watertap_capex_electrical_cost': watertap_capex_total * watertap_capex_electrical_cost_pct,
        'watertap_capex_land_clearing_cost': watertap_capex_total * watertap_capex_land_clearing_cost_pct,
        'watertap_capex_road_cost': watertap_capex_total * watertap_capex_road_cost_pct,
        'watertap_capex_solids_handling_pct': watertap_capex_solids_handling_pct,
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
# Set to 1.0 for no inflation adjustment
inflation_factor = 1.23  # Change this value to adjust for inflation
costs = calculate_lithium_costs(inflation_factor)
print(f"Inflation factor applied: {inflation_factor:.2f}")
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
    'Precipitated salts processing': costs['industry_capex_solids_handling_pct'],
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
# Reorganized to match industry categories
capex_breakdown_watertap = {
    'Evaporation ponds': (costs['watertap_capex_liner_cost_pct'] + 
                         costs['watertap_capex_dike_cost_pct'] + 
                         costs['watertap_capex_land_clearing_cost_pct'] + 
                         costs['watertap_capex_road_cost_pct']),
    'Precipitated salts processing': costs['watertap_capex_solids_handling_pct'],
    'Extraction wells': (costs['watertap_capex_well_cost_pct'] + 
                        costs['watertap_capex_pipe_pump_cost_pct'] + 
                        costs['watertap_capex_electrical_cost_pct']),
    'Other (capex)': costs['watertap_capex_shipping_cost_pct']
}

# WaterTAP model operating cost breakdown percentages (calculated dynamically)
opex_breakdown_watertap = {
    'Precipitated salts processing\n(opex)': costs['watertap_opex_solids_handling_pct'],
    'Government agreements': costs['watertap_opex_government_agreements_pct'],
    'Electricity': costs['watertap_opex_electricity_pct'],
    'Maintenance-labor-chemical': costs['watertap_opex_maintenance_labor_chemical_pct'],
    'Shipping': costs['watertap_opex_shipping_pct'],
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
    (costs['watertap_capex_liner_cost'] + 
     costs['watertap_capex_dike_cost'] + 
     costs['watertap_capex_land_clearing_cost'] + 
     costs['watertap_capex_road_cost']),  # Evaporation ponds
    costs['watertap_capex_solids_handling'],  # Precipitated salts processing
    (costs['watertap_capex_well_cost'] + 
     costs['watertap_capex_pipe_pump_cost'] + 
     costs['watertap_capex_electrical_cost']),  # Extraction wells
    costs['watertap_capex_shipping_cost']  # Other (capex)
]

opex_values_watertap = [
    costs['watertap_opex_solids_handling'],
    costs['watertap_opex_government_agreements'],
    costs['watertap_opex_electricity'],
    costs['watertap_opex_maintenance_labor_chemical'],
    costs['watertap_opex_shipping'],
    costs['watertap_opex_liner_replacement']
]

# Colors for different categories using viridis color scheme
# Capex colors: viridis blues (distinct from opex)
capex_colors_industry = ['#453781', '#6d5cb7', '#9787da', '#cac0f1']
capex_colors_watertap = ['#453781', '#6d5cb7', '#9787da', '#cac0f1']

# Opex colors: viridis greens/yellows (distinct from capex)
opex_colors_industry = ['#287D8E', '#42a6bb', '#58c3da', '#77d8ec', '#a1e8f7', '#b9eef9']
opex_colors_watertap = ['#287D8E', '#42a6bb', '#58c3da', '#77d8ec', '#a1e8f7', '#b9eef9']

# Revenue color: viridis purple (distinct from capex and opex)
revenue_color = '#3CBB75'
dot_color = '#DCE319'

# Set up the plots
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7, 4))
ax1.set_frame_on(False)
ax2.set_frame_on(False)

# Add a common title above both plots
fig.suptitle('Lithium Brine Cost Breakdown Comparison', fontsize=16, fontweight='bold', y=0.95)

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
revenue_bar_industry = ax1.bar(x_industry, -revenue_industry, width, label='Precipitated salts revenue', color=revenue_color)

# Calculate and add levelized cost dot
levelized_cost_industry = total_capex_industry + total_opex_industry - revenue_industry
ax1.scatter(x_industry, levelized_cost_industry, color=dot_color, s=70, label='Levelized cost of Li brine', zorder=5)

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
revenue_bar_watertap = ax2.bar(x_watertap, -revenue_watertap, width, label='Precipitated salts revenue', color=revenue_color)

# Calculate and add levelized cost dot
levelized_cost_watertap = total_capex_watertap + total_opex_watertap - revenue_watertap
ax2.scatter(x_watertap, levelized_cost_watertap, color=dot_color, s=70, label='Levelized cost of Li brine', zorder=5)

# Customize the plots
# Left plot (Industry report)
ax1.set_ylabel('Cost (USD_2025/Mt Li)', fontsize=11)
ax1.set_xticks([x_industry])
ax1.set_xticklabels(['Industry report'], fontsize=12)
ax1.tick_params(axis='both', labelsize=10)
ax1.set_xlim(0, 0.5)  # Set x-axis limits for industry plot

# Calculate overall y-limits for both plots
total_costs_industry = total_capex_industry + total_opex_industry
total_costs_watertap = total_capex_watertap + total_opex_watertap

y_min_overall = min(-revenue_industry, -revenue_watertap) * 1.2
y_max_overall = max(total_costs_industry, total_costs_watertap, levelized_cost_industry, levelized_cost_watertap) * 1.1

# Set same y-limits for both plots
ax1.set_ylim(y_min_overall, y_max_overall)
ax1.axhline(0, color='black', linewidth=1)

# Add levelized cost as y-tick label and avoid overlap with nearest default tick
current_yticks = list(ax1.get_yticks())
current_yticklabels = [f'${tick:.0f}' for tick in current_yticks]
if len(current_yticks) >= 2:
    spacings = np.diff(sorted(current_yticks))
    median_spacing = np.median(spacings)
    tolerance = 0.5 * median_spacing
else:
    tolerance = 0
if len(current_yticks) > 0:
    diffs = [abs(t - levelized_cost_industry) for t in current_yticks]
    nearest_idx = int(np.argmin(diffs))
    if diffs[nearest_idx] <= tolerance:
        current_yticks.pop(nearest_idx)
        current_yticklabels.pop(nearest_idx)
current_yticks.append(levelized_cost_industry)
current_yticklabels.append(f'${levelized_cost_industry:.0f}')
ax1.set_yticks(current_yticks)
ax1.set_yticklabels(current_yticklabels)

# Add legend for industry plot
ax1.set_ylabel('Cost (USD_2025/Mt Li)', fontsize=11)
ax1.legend(loc='upper right', frameon=True, fancybox=True, shadow=True, fontsize=8)

# Grid for better readability
ax1.grid(axis='y', alpha=0.3, linestyle='--')

# Right plot (WaterTAP model)
ax2.set_ylabel('Cost (USD_2025/Mt Li)', fontsize=11)
ax2.set_xticks([x_watertap])
ax2.set_xticklabels(['WaterTAP model'], fontsize=12)
ax2.tick_params(axis='both', labelsize=10)
ax2.set_xlim(0, 0.5)  # Set x-axis limits for WaterTAP plot

# Use same y-limits for consistency
ax2.set_ylim(y_min_overall, y_max_overall)
ax2.axhline(0, color='black', linewidth=1)

# Add levelized cost as y-tick label and avoid overlap with nearest default tick
current_yticks = list(ax2.get_yticks())
current_yticklabels = [f'${tick:.0f}' for tick in current_yticks]
if len(current_yticks) >= 2:
    spacings = np.diff(sorted(current_yticks))
    median_spacing = np.median(spacings)
    tolerance = 0.5 * median_spacing
else:
    tolerance = 0
if len(current_yticks) > 0:
    diffs = [abs(t - levelized_cost_watertap) for t in current_yticks]
    nearest_idx = int(np.argmin(diffs))
    if diffs[nearest_idx] <= tolerance:
        current_yticks.pop(nearest_idx)
        current_yticklabels.pop(nearest_idx)
current_yticks.append(levelized_cost_watertap)
current_yticklabels.append(f'${levelized_cost_watertap:.0f}')
ax2.set_yticks(current_yticks)
ax2.set_yticklabels(current_yticklabels)

# Add legend for WaterTAP plot
ax2.legend(loc='upper right', frameon=True, fancybox=True, shadow=True, fontsize=8)

# Grid for better readability
ax2.grid(axis='y', alpha=0.3, linestyle='--')

# Adjust layout
plt.tight_layout()

# Draw figure-wide dotted lines at levelized costs across both subplots
ax1_pos = ax1.get_position()
ax2_pos = ax2.get_position()
x_start = min(ax1_pos.x0, ax2_pos.x0)
x_end = max(ax1_pos.x1, ax2_pos.x1)

# Transform data y to figure y coordinate
y_fig_industry = fig.transFigure.inverted().transform(ax1.transData.transform((0, levelized_cost_industry)))[1]
y_fig_watertap = fig.transFigure.inverted().transform(ax2.transData.transform((0, levelized_cost_watertap)))[1]

fig.lines.append(Line2D([x_start, x_end], [y_fig_industry, y_fig_industry], transform=fig.transFigure,
                        color='black', linestyle=':', linewidth=2, alpha=0.7, zorder=10))
fig.lines.append(Line2D([x_start, x_end], [y_fig_watertap, y_fig_watertap], transform=fig.transFigure,
                        color='black', linestyle=':', linewidth=2, alpha=0.7, zorder=10))

# Show the plot
plt.show()

# Print calculated values
print("INDUSTRY REPORT:")
print("Capital Costs Breakdown:")
for category, value in zip(capex_breakdown_industry.keys(), capex_values_industry):
    print(f"  {category}: ${value:.0f} ({capex_breakdown_industry[category]*100:.1f}%)")

print(f"\nTotal Capital Costs: ${total_capex_industry:.0f}")

print("\nOperating Costs Breakdown:")
for category, value in zip(opex_breakdown_industry.keys(), opex_values_industry):
    print(f"  {category}: ${value:.0f} ({list(opex_breakdown_industry.values())[list(opex_breakdown_industry.keys()).index(category)]*100:.1f}%)")

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