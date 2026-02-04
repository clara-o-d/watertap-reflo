import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

def create_heat_map(csv_file_path, flow_volume):
    """
    Create a heat map from wide sensitivity analysis data.
    
    Parameters:
    -----------
    csv_file_path : str
        Path to the CSV file containing the data
    flow_volume : float
        Flow volume for converting concentrations to mass fractions
    """
    
    # Read the CSV file, skip the comment line and manually set column names
    df = pd.read_csv(csv_file_path, skiprows=1)
    
    # Set the correct column names manually
    expected_columns = [
        'Inlet Li+ concentration', 'Inlet TDS concentration', 'Final Li+ concentration', 
        'Final TDS concentration', 'LCOLi (USD/mt)', 'aggregate_capital_cost (USD)',
        'aggregate_fixed_operating_cost (USD/year)', 'aggregate_variable_operating_cost (USD/year)',
        'total_capital_cost (USD)', 'total_operating_cost (USD/year)', 'fraction_evaporated',
        'mass_inlet_h2o (kg/s)', 'Resultant inlet Li+ concentration', 'Resultant inlet TDS concentration',
        'Resultant final Li+ concentration', 'Resultant final TDS concentration',
    ]
    
    df.columns = expected_columns
    print("Set column names:", df.columns.tolist())
    
    # Filter for only rows with final Li+ concentration = 2.0e-02 and final TDS concentration = 2.0e-01
    # df_filtered = df[
    #     (df['Final Li+ concentration'] == 2.0e-02) & 
    #     (df['Final TDS concentration'] == 2.0e-01)
    # ].copy()
    df_filtered = df.copy()
    
    # Filter inlet TDS concentrations up to 3.967778e+02
    # df_filtered = df_filtered[df_filtered['Inlet TDS concentration'] < 3.967778e+02].copy()
    
    # Remove rows with NaN values in LCOLi
    # df_filtered = df_filtered.dropna(subset=['LCOLi (USD/mt)'])
    
    # Calculate inlet concentrations in g/L (avoid rounding to preserve distinct levels)
    df_filtered['inlet_li_conc'] = (df_filtered['Inlet Li+ concentration'] / (flow_volume))
    df_filtered['inlet_tds_conc'] = (df_filtered['Inlet TDS concentration'] / (flow_volume))
    
    # Calculate full range from all data (including NaN values) before filtering
    full_li_min = df_filtered['inlet_li_conc'].min()
    full_li_max = df_filtered['inlet_li_conc'].max()
    full_tds_min = df_filtered['inlet_tds_conc'].min()
    full_tds_max = df_filtered['inlet_tds_conc'].max()
    
    # Convert levelized cost to thousands per metric ton
    df_filtered['levelized_cost_thousands'] = df_filtered['LCOLi (USD/mt)'] / 1000
    
    # Remove rows with NaN values in levelized cost
    df_filtered = df_filtered.dropna(subset=['levelized_cost_thousands'])
    
    # Calculate baseline values for percentage calculations (using maximum values)
    baseline_li = df_filtered['inlet_li_conc'].max()
    baseline_tds = df_filtered['inlet_tds_conc'].max()
    baseline_mask = (df_filtered['inlet_li_conc'] == baseline_li) & (df_filtered['inlet_tds_conc'] == baseline_tds)
    baseline_cost_data = df_filtered[baseline_mask]['levelized_cost_thousands']
    if len(baseline_cost_data) == 0:
        baseline_cost = df_filtered['levelized_cost_thousands'].max()
    else:
        baseline_cost = baseline_cost_data.iloc[0]
    
    # Create the scatter plot with raw data
    plt.figure(figsize=(7, 6))
    
    # Create scatter plot with raw data points colored by levelized cost
    scatter = plt.scatter(df_filtered['inlet_tds_conc'], df_filtered['inlet_li_conc'], 
                         c=df_filtered['levelized_cost_thousands'], 
                         cmap='viridis', s=30, alpha=0.7, vmin=baseline_cost)
    
    # Add colorbar with the same styling
    cbar = plt.colorbar(scatter, label='Levelized cost (thousands $/t Li⁺)')
    cbar.ax.set_ylabel('Levelized cost (thousands $/t Li⁺)', fontsize=13)
    cbar.ax.tick_params(labelsize=11)
    
    # Colorbar ticks: start at base case (0% at bottom)
    vmax = df_filtered['levelized_cost_thousands'].max()
    num_ticks = 6
    cbar_ticks = np.linspace(baseline_cost, vmax, num=num_ticks)
    cbar.set_ticks(cbar_ticks)
    cbar.set_ticklabels([
        f"{t:.1f}\n(0%)" if i == 0 else f"{t:.1f}\n(+{((t-baseline_cost)/baseline_cost)*100:.0f}%)"
        for i, t in enumerate(cbar_ticks)
    ])
    
    # Set custom x and y tick labels with percentage variations (evenly spaced ticks)
    max_ticks = 6
    
    # Create evenly spaced tick positions across the full range (including null values)
    x_tick_positions = np.linspace(full_tds_min, full_tds_max, num=max_ticks)
    y_tick_positions = np.linspace(full_li_min, full_li_max, num=max_ticks)
    
    # Create tick labels for these evenly spaced positions
    x_tick_labels = []
    y_tick_labels = []
    
    for x_pos in x_tick_positions:
        if abs(x_pos - baseline_tds) < 0.01:  # Use small tolerance for float comparison
            x_tick_labels.append(f"{x_pos:.2f}\n(0%)")
        else:
            pct_change = ((x_pos - baseline_tds) / baseline_tds) * 100
            sign = "+" if pct_change > 0 else ""
            x_tick_labels.append(f"{x_pos:.2f}\n({sign}{pct_change:.0f}%)")
    
    for y_pos in y_tick_positions:
        if abs(y_pos - baseline_li) < 0.01:  # Use small tolerance for float comparison
            y_tick_labels.append(f"{y_pos:.4f}\n(0%)")
        else:
            pct_change = ((y_pos - baseline_li) / baseline_li) * 100
            sign = "+" if pct_change > 0 else ""
            y_tick_labels.append(f"{y_pos:.4f}\n({sign}{pct_change:.0f}%)")
    
    plt.xticks(x_tick_positions, x_tick_labels, rotation=45, ha='right', fontsize=11)
    plt.yticks(y_tick_positions, y_tick_labels, fontsize=11)
    
    # Set axis limits to show full range (including areas with null/empty values)
    plt.xlim(full_tds_min, full_tds_max)
    plt.ylim(full_li_min, full_li_max)
    
    # Set labels and title
    plt.xlabel('Inlet TDS concentration (g/L)', fontsize=13)
    plt.ylabel('Inlet Li$^+$ concentration (g/L)', fontsize=13)
    plt.title('Li$^+$ brine cost estimates and % change', fontsize=13, fontweight='bold')
    
    # Grid off for cleaner heat map
    plt.grid(False)
    
    # Define brine source ranges
    brine_ranges = {
        'Salar de Atacama': {'li_range': [1.4, 5.0], 'tds_range': [300, 400], 'color': 'magenta'},
        'Salar de Hombre Muerto': {'li_range': [0.69, 1.05], 'tds_range': [166.1, 200], 'color': 'cyan'},
        'Salar de Uyuni': {'li_range': [1.1, 1.35], 'tds_range': [250, 290], 'color': 'yellow'},
        'Produced waters': {'li_range': [0.3959, 0.5], 'tds_range': [166.1, 245], 'color': 'orange'},
        # 'Geothermal': {'li_range': [0.3959, 0.5], 'tds_range': [166.1, 300], 'color': 'red'}
    }
    
    # Get data boundaries (use full range to show entire parameter space)
    heatmap_li_min, heatmap_li_max = full_li_min, full_li_max
    heatmap_tds_min, heatmap_tds_max = full_tds_min, full_tds_max
    
    # # Add colored range indicators on x and y axes for each brine source
    # legend_elements = []
    # for name, ranges in brine_ranges.items():
    #     li_min, li_max = ranges['li_range']
    #     tds_min, tds_max = ranges['tds_range']
    #     color = ranges['color']
        
    #     # Add colored range indicators on x-axis (TDS concentrations)
    #     if tds_min <= heatmap_tds_max and tds_max >= heatmap_tds_min:
    #         # Draw colored line segment directly on x-axis
    #         tds_start = max(tds_min, heatmap_tds_min)
    #         tds_end = min(tds_max, heatmap_tds_max)
    #         if tds_start < tds_end:
    #             # Draw thick colored line on x-axis at y=0 (bottom of heat map)
    #             plt.plot([tds_start, tds_end], 
    #                     [heatmap_li_min, heatmap_li_min], 
    #                     color=color, linewidth=10, alpha=1)
        
    #     # Add colored range indicators on y-axis (Li+ concentrations)
    #     if li_min <= heatmap_li_max and li_max >= heatmap_li_min:
    #         # Draw colored line segment directly on y-axis
    #         li_start = max(li_min, heatmap_li_min)
    #         li_end = min(li_max, heatmap_li_max)
    #         if li_start < li_end:
    #             # Draw thick colored line on y-axis at x=0 (left of heat map)
    #             plt.plot([heatmap_tds_min, heatmap_tds_min], 
    #                     [li_start, li_end], 
    #                     color=color, linewidth=10, alpha=1)
        
    #     # Draw dotted outline of the range rectangle on the heat map
    #     # Top horizontal line - only if it intersects with heat map
    #     if li_max >= heatmap_li_min and li_max <= heatmap_li_max:
    #         tds_start = max(tds_min, heatmap_tds_min)
    #         tds_end = min(tds_max, heatmap_tds_max)
    #         if tds_start < tds_end:
    #             plt.plot([tds_start, tds_end], [li_max, li_max], 
    #                     color=color, linestyle='--', linewidth=3, alpha=1)
        
    #     # Bottom horizontal line - only if it intersects with heat map
    #     if li_min >= heatmap_li_min and li_min <= heatmap_li_max:
    #         tds_start = max(tds_min, heatmap_tds_min)
    #         tds_end = min(tds_max, heatmap_tds_max)
    #         if tds_start < tds_end:
    #             plt.plot([tds_start, tds_end], [li_min, li_min], 
    #                     color=color, linestyle='--', linewidth=3, alpha=1)
        
    #     # Left vertical line - only if it intersects with heat map
    #     if tds_min >= heatmap_tds_min and tds_min <= heatmap_tds_max:
    #         li_start = max(li_min, heatmap_li_min)
    #         li_end = min(li_max, heatmap_li_max)
    #         if li_start < li_end:
    #             plt.plot([tds_min, tds_min], [li_start, li_end], 
    #                     color=color, linestyle='--', linewidth=3, alpha=1)
        
    #     # Right vertical line - only if it intersects with heat map
    #     if tds_max >= heatmap_tds_min and tds_max <= heatmap_tds_max:
    #         li_start = max(li_min, heatmap_li_min)
    #         li_end = min(li_max, heatmap_li_max)
    #         if li_start < li_end:
    #             plt.plot([tds_max, tds_max], [li_start, li_end], 
    #                     color=color, linestyle='--', linewidth=3, alpha=1)
        
    #     # Add text label in the center of each brine source range
    #     if (li_min <= heatmap_li_max and li_max >= heatmap_li_min and 
    #         tds_min <= heatmap_tds_max and tds_max >= heatmap_tds_min):
    #         # Calculate center position for the label
    #         li_center = (max(li_min, heatmap_li_min) + min(li_max, heatmap_li_max)) / 2
    #         tds_center = (max(tds_min, heatmap_tds_min) + min(tds_max, heatmap_tds_max)) / 2
            
    #         # Handle multi-line text for Salar de Hombre Muerto
    #         if name == 'Salar de Hombre Muerto':
    #             display_text = 'Salar de\nHombre Muerto'
    #         else:
    #             display_text = name
            
        
    #         # Add text label with translucent white background for better visibility
    #         plt.text(tds_center, li_center, display_text, 
    #                 ha='center', va='center', fontsize=12, fontweight='bold',
    #                 bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
    #                          edgecolor=color, linewidth=2, alpha=0.7))
        
    #     # Create legend element
    #     legend_elements.append(plt.Line2D([0], [0], color=color, linestyle='-', linewidth=3, label=name))
    
    # Add WaterTAP model reference point at maximum concentrations (slightly offset)
    offset_tds = baseline_tds - ((heatmap_tds_max - heatmap_tds_min) * 0.01)  # Move left by 2% of TDS range
    offset_li = baseline_li - ((heatmap_li_max - heatmap_li_min) * 0.01)      # Move down by 2% of Li range
    plt.plot(offset_tds, offset_li, 'k*', markersize=20, markeredgewidth=1.5, 
             markeredgecolor='black', markerfacecolor='white', label='WaterTAP model')
    
    # # Add WaterTAP model to legend elements
    # legend_elements.append(plt.Line2D([0], [0], marker='*', color='black', 
    #                                  markerfacecolor='white', markeredgecolor='black',
    #                                  markersize=8, linestyle='', label='WaterTAP model'))
    
    # Add legend
    # plt.legend(handles=legend_elements, loc='upper left', fontsize=12, bbox_to_anchor=(0.02, 0.98))
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    
    plt.show()
    
    return df_filtered

if __name__ == "__main__":
    # Parameters - UPDATE THESE VALUES
    FLOW_VOLUME = 1.280  # Flow volume for mass fraction conversion
    CSV_FILE = "parameter_sweep020426_1.csv"
    
    # Create the heat map
    result_data = create_heat_map(CSV_FILE, FLOW_VOLUME)
    print("Heat map created successfully!")
    print(f"Number of data points: {len(result_data)}")
    print(f"Number of valid data points: {len(result_data.dropna(subset=['levelized_cost_thousands']))}")
