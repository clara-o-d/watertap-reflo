"""Results comparison visualization for lithium extraction flowsheet.

Creates cost comparison plots between industry reports and WaterTAP model results.
"""

import matplotlib.pyplot as plt
import numpy as np

# Sample data - you can replace these with your actual values
categories = ['Industry report', 'WaterTAP model']

# Cost breakdown ($/kg Li or whatever units you're using)
capital_costs = np.array([590.6619, 1.2603e+03])
operating_costs = np.array([3.1585e+03, 2.5555e+03])
revenue = np.array([1.2603e+03, 1.2603e+03])
levelized_costs = np.array([3.7492e+03, 3.8158e+03])

# Colors as specified
capex_color = '#4198b5'
opex_color = '#610059' 
revenue_color = '#165d54'
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
# Plot revenue as negative bars below the x-axis
bars3 = ax.bar(x, -revenue, width, label='Revenue', color=revenue_color)

# Add dots for levelized cost (commented out per request)
ax.scatter(x, levelized_costs, color=dot_color, s=100, label='Levelized Cost', zorder=5)

# Customize the plot
ax.set_xlabel('Estimate source', fontsize=10)
ax.set_ylabel('Cost ($/Mt Li)', fontsize=10)
ax.set_title('Levelized cost of lithium: Model comparison', fontsize=11, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=10)
# Dynamic y-limits to include negative revenue and positive costs
total_costs = capital_costs + operating_costs
y_min = -np.max(revenue) * 1.2
y_max = max(np.max(total_costs), np.max(levelized_costs)) * 1.2
ax.set_ylim(y_min, y_max)
ax.axhline(0, color='black', linewidth=1)

# Add legend
ax.legend(loc='upper right', frameon=True, fancybox=True, shadow=True)

# Grid for better readability
ax.grid(axis='y', alpha=0.3, linestyle='--')

# Adjust layout
plt.tight_layout()

# Show the plot
plt.show()