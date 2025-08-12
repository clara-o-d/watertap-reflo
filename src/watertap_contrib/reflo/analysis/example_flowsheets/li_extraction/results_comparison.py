"""Results comparison visualization for lithium extraction flowsheet.

Creates cost comparison plots between industry reports and WaterTAP model results.
"""

import matplotlib.pyplot as plt
import numpy as np

# Sample data - you can replace these with your actual values
categories = ['Industry report', 'WaterTAP model']

# Cost breakdown ($/kg Li or whatever units you're using)
capital_costs = [758.322067781, 634.898952789] 
operating_costs = [1438.82774121, 1471.85739134] 
levelized_costs = [2197.14980899, 2106.75634413] 

# Colors as specified
capex_color = '#4198b5'
opex_color = '#610059' 
dot_color = '#279989'

# Set up the plot
fig, ax = plt.subplots(figsize=(4.25, 5))

# Width of bars
width = 0.25
# Bring bars closer together by further reducing spacing between category centers
x = np.arange(len(categories)) * 0.4

# Create stacked bars
bars1 = ax.bar(x, capital_costs, width, label='Capital Cost', color=capex_color)
bars2 = ax.bar(x, operating_costs, width, bottom=capital_costs, label='Operating Cost', color=opex_color)

# Add dots for levelized cost (commented out per request)
# ax.scatter(x, levelized_costs, color=dot_color, s=100, label='Levelized Cost', zorder=5)

# Customize the plot
ax.set_xlabel('Estimate source', fontsize=10)
ax.set_ylabel('Cost ($/Mt Li)', fontsize=10)
ax.set_title('Levelized cost of lithium: Model comparison', fontsize=11, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=10)
ax.set_ylim(0, 3000)

# Add legend
ax.legend(loc='upper right', frameon=True, fancybox=True, shadow=True)

# Removed direct value labels on bars and dots per request

# Grid for better readability
ax.grid(axis='y', alpha=0.3, linestyle='--')

# Adjust layout
plt.tight_layout()

# Show the plot
plt.show()