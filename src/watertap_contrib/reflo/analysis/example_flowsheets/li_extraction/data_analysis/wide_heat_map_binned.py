import pandas as pd
import numpy as np
import numpy.ma as ma
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
        'Inlet Li+ molality', 'Inlet TDS concentration (ppt)', 'Final Li+ concentration (kg/kg)', 
        'Final TDS concentration (kg/kg)', 'LCOLi (USD/t)', 'LCOLi2CO3 (USD/t)',
        'aggregate_capital_cost (USD)', 'aggregate_fixed_operating_cost (USD/year)', 
        'aggregate_variable_operating_cost (USD/year)', 'total_capital_cost (USD)', 
        'total_operating_cost (USD/year)', 'fraction_evaporated', 'mass_inlet_h2o (kg/s)', 
        'Resultant inlet Li+ molality (mol/kg)', 'Resultant inlet TDS concentration (kg/kg)',
        'Resultant inlet Li+ mass flow (kg/s)', 'Resultant inlet TDS mass flow (kg/s)',
        'Resultant final Li+ concentration (kg/kg)', 'Resultant final TDS concentration (kg/kg)',
    ]
    
    df.columns = expected_columns
    print("Set column names:", df.columns.tolist())
    
    df_filtered = df.copy()
    
    # Use inlet concentrations directly (Li molality in mol/kg, TDS in ppt)
    df_filtered['inlet_li_molality'] = df_filtered['Inlet Li+ molality']
    df_filtered['inlet_tds_ppt'] = df_filtered['Inlet TDS concentration (ppt)']
    
    # Calculate full range from all data (including NaN values) before filtering
    full_li_min = df_filtered['inlet_li_molality'].min()
    full_li_max = df_filtered['inlet_li_molality'].max()
    full_tds_min = df_filtered['inlet_tds_ppt'].min()
    full_tds_max = min(df_filtered['inlet_tds_ppt'].max(), 300)  # Cap at 275 ppt
    
    # Convert levelized cost to thousands per metric ton
    df_filtered['levelized_cost_thousands'] = df_filtered['LCOLi2CO3 (USD/t)'] / 1000
    
    # Create binned heat map data
    num_bins = 10  # Number of bins for each axis
    
    # Create bins for Li molality and TDS concentrations using full range (including null values)
    li_bins = np.linspace(full_li_min, full_li_max, num_bins + 1)
    tds_bins = np.linspace(full_tds_min, full_tds_max, num_bins + 1)
    
    # Assign each data point to bins
    df_filtered['li_bin'] = pd.cut(df_filtered['inlet_li_molality'], bins=li_bins, labels=False, include_lowest=True)
    df_filtered['tds_bin'] = pd.cut(df_filtered['inlet_tds_ppt'], bins=tds_bins, labels=False, include_lowest=True)
    
    # Create binned pivot table
    pivot_data = df_filtered.pivot_table(
        values='levelized_cost_thousands',
        index='li_bin',
        columns='tds_bin',
        aggfunc='mean'
    )
    
    # Reindex to include all bins (0 to num_bins-1) even if empty
    all_bins = range(num_bins)
    pivot_data = pivot_data.reindex(index=all_bins, columns=all_bins)
    
    # Create bin center values for plotting
    li_centers = (li_bins[:-1] + li_bins[1:]) / 2
    tds_centers = (tds_bins[:-1] + tds_bins[1:]) / 2
    
    # Interpolate to fill missing values only for Li molalities above 0.2
    pivot_filled = pivot_data.copy()
    for idx in pivot_filled.index:
        if li_centers[idx] > 0.15:
            # Interpolate this row (across TDS values)
            pivot_filled.loc[idx] = pivot_filled.loc[idx].interpolate(method='linear', limit_direction='both')
            # Fill any remaining NaNs with forward/backward fill
            pivot_filled.loc[idx] = pivot_filled.loc[idx].ffill().bfill()
    
    # Use the filled data for plotting
    pivot_data = pivot_filled

    # Calculate baseline values for percentage calculations (using bin centers)
    baseline_li = li_centers[-1]  # Use highest bin center as baseline
    baseline_tds = tds_centers[-1]  # Use highest bin center as baseline
    # Get baseline cost from highest bin, or use max of all non-NaN values if highest bin is empty
    if pd.isna(pivot_data.iloc[-1, -1]):
        baseline_cost = pivot_data.stack().max()
    else:
        baseline_cost = pivot_data.iloc[-1, -1]
    
    # Create round, evenly spaced tick values for x-axis (TDS)
    def create_round_ticks(min_val, max_val, num_ticks=5):
        """Create exactly num_ticks evenly spaced round tick values"""
        range_val = max_val - min_val
        # Calculate nice interval
        raw_interval = range_val / (num_ticks - 1)
        # Round to nice numbers (10, 20, 50, 100, etc.)
        magnitude = 10 ** np.floor(np.log10(raw_interval))
        nice_intervals = [1, 2, 5, 10]
        normalized = raw_interval / magnitude
        nice_interval = min([x for x in nice_intervals if x >= normalized], default=10) * magnitude
        
        # Start from a round number at or below min_val
        start = np.floor(min_val / nice_interval) * nice_interval
        # Generate exactly num_ticks values
        ticks = [start + i * nice_interval for i in range(num_ticks)]
        return np.array(ticks)
    
    x_tick_positions = create_round_ticks(full_tds_min, full_tds_max, 5)
    y_tick_positions = create_round_ticks(full_li_min, full_li_max, 5)
    
    # Create the heat map
    plt.figure(figsize=(7, 6))
    
    # Create heat map using imshow (with binned data)
    # Use bin edges for extent so bin centers align with tick positions
    # Use masked array so NaN values appear as empty space
    pivot_plot = ma.masked_invalid(pivot_data.values)
    
    # Get actual data range for colorbar limits
    unique_values = pivot_data.values[~np.isnan(pivot_data.values)]
    vmin = np.min(unique_values) if len(unique_values) > 0 else None
    vmax = np.max(unique_values) if len(unique_values) > 0 else None
    
    heatmap = plt.imshow(pivot_plot, cmap='viridis', aspect='auto', 
                         extent=[tds_bins[0], tds_bins[-1], 
                                li_bins[0], li_bins[-1]],
                         origin='lower', vmin=vmin, vmax=vmax)
    
    # Add colorbar with the same styling
    cbar = plt.colorbar(heatmap, label='Levelized cost (thousands $/t Li₂CO₃)')
    cbar.ax.set_ylabel('Levelized cost (thousands $/t Li₂CO₃)', fontsize=13)
    cbar.ax.tick_params(labelsize=10)
    
    # Colorbar ticks: create evenly spaced values within data bounds
    unique_values = pivot_data.values[~np.isnan(pivot_data.values)]
    if len(unique_values) > 0:
        cbar_min = np.min(unique_values)
        cbar_max = np.max(unique_values)
        # Create 8 evenly spaced ticks
        cbar_ticks = np.linspace(cbar_min, cbar_max, 4)
        cbar.set_ticks(cbar_ticks)
        cbar.set_ticklabels([f"{t:.2g}" for t in cbar_ticks])
    
    # Create tick labels without percentages
    x_tick_labels = [f"{x:.3g}" for x in x_tick_positions]
    y_tick_labels = [f"{y:.3g}" for y in y_tick_positions]
    
    # Set ticks on one side only
    plt.xticks(x_tick_positions, x_tick_labels, rotation=0, ha='center', fontsize=11)
    plt.yticks(y_tick_positions, y_tick_labels, fontsize=11)
    
    # Set axis limits to show full range (including areas with null/empty values)
    plt.xlim(full_tds_min, full_tds_max)
    plt.ylim(full_li_min, full_li_max)
    
    # Set labels and title
    plt.xlabel('Inlet TDS concentration (ppt)', fontsize=13)
    plt.ylabel('Inlet Li$^+$ molality (mol/kg)', fontsize=13)
    plt.title('Li$^+$ brine cost estimates', fontsize=13, fontweight='bold')
    
    # Grid off for cleaner heat map
    plt.grid(False)
    
    # Define brine source ranges (Li in molality mol/kg, TDS in ppt)
    brine_ranges = {
        'Salar de Atacama': {'li_range': [0.2, 0.3], 'tds_range': [200, 350], 'color': 'magenta'},
        # 'Salar de Uyuni': {'li_range': [0.062, 0.105], 'tds_range': [145, 267], 'color': 'yellow'},
        'Salar del Hombre Muerto': {'li_range': [0.038, 0.186], 'tds_range': [272, 294], 'color': 'cyan'},
        'Produced Waters': {'li_range': [0.005, 0.12], 'tds_range': [120, 310], 'color': 'blue'},
        # 'Salton Sea': {'li_range': [0.019, 0.089], 'tds_range': [250, 350], 'color': 'green'},
        # 'Produced Water': {'li_range': [0.009, 0.076], 'tds_range': [166, 280], 'color': 'orange'},
    }
    
    # Get heat map boundaries (use full range to show entire parameter space)
    heatmap_li_min, heatmap_li_max = full_li_min, full_li_max
    heatmap_tds_min, heatmap_tds_max = full_tds_min, full_tds_max
    
    # Add colored range indicators on x and y axes for each brine source
    legend_elements = []
    for name, ranges in brine_ranges.items():
        li_min, li_max = ranges['li_range']
        tds_min, tds_max = ranges['tds_range']
        color = ranges['color']
        
        # Add colored range indicators on x-axis (TDS concentrations)
        # if tds_min <= heatmap_tds_max and tds_max >= heatmap_tds_min:
        #     # Draw colored line segment directly on x-axis
        #     tds_start = max(tds_min, heatmap_tds_min)
        #     tds_end = min(tds_max, heatmap_tds_max)
        #     if tds_start < tds_end:
        #         # Draw thick colored line on x-axis at y=0 (bottom of heat map)
        #         plt.plot([tds_start, tds_end], 
        #                 [heatmap_li_min, heatmap_li_min], 
        #                 color=color, linewidth=10, alpha=1)
        
        # Add colored range indicators on y-axis (Li+ concentrations)
        # if li_min <= heatmap_li_max and li_max >= heatmap_li_min:
        #     # Draw colored line segment directly on y-axis
        #     li_start = max(li_min, heatmap_li_min)
        #     li_end = min(li_max, heatmap_li_max)
        #     if li_start < li_end:
        #         # Draw thick colored line on y-axis at x=0 (left of heat map)
        #         plt.plot([heatmap_tds_min, heatmap_tds_min], 
        #                 [li_start, li_end], 
        #                 color=color, linewidth=10, alpha=1)
        
        # Draw dotted outline of the range rectangle on the heat map
        edge_tolerance = 0.01  # Tolerance for detecting if edge is at boundary
        
        # Top horizontal line
        if li_max >= heatmap_li_min and li_max <= heatmap_li_max:
            # Check if this is at the top edge of the graph
            if abs(li_max - heatmap_li_max) < edge_tolerance:
                tds_start = tds_bins[0]  # Extend to left edge
                tds_end = tds_bins[-1]   # Extend to right edge
            else:
                tds_start = max(tds_min, heatmap_tds_min)
                tds_end = min(tds_max, heatmap_tds_max)
            if tds_start < tds_end:
                plt.plot([tds_start, tds_end], [li_max, li_max], 
                        color=color, linestyle='--', linewidth=2, alpha=1)
        
        # Bottom horizontal line
        if li_min >= heatmap_li_min and li_min <= heatmap_li_max:
            # Check if this is at the bottom edge of the graph
            if abs(li_min - heatmap_li_min) < edge_tolerance:
                tds_start = tds_bins[0]  # Extend to left edge
                tds_end = tds_bins[-1]   # Extend to right edge
            else:
                tds_start = max(tds_min, heatmap_tds_min)
                tds_end = min(tds_max, heatmap_tds_max)
            if tds_start < tds_end:
                plt.plot([tds_start, tds_end], [li_min, li_min], 
                        color=color, linestyle='--', linewidth=2, alpha=1)
        
        # Left vertical line
        if tds_min >= heatmap_tds_min and tds_min <= heatmap_tds_max:
            # Check if this is at the left edge of the graph
            if abs(tds_min - heatmap_tds_min) < edge_tolerance:
                li_start = li_bins[0]    # Extend to bottom edge
                li_end = li_bins[-1]     # Extend to top edge
            else:
                li_start = max(li_min, heatmap_li_min)
                li_end = min(li_max, heatmap_li_max)
            if li_start < li_end:
                plt.plot([tds_min, tds_min], [li_start, li_end], 
                        color=color, linestyle='--', linewidth=2, alpha=1)
        
        # Right vertical line
        if tds_max >= heatmap_tds_min and tds_max <= heatmap_tds_max:
            # Check if this is at the right edge of the graph
            if abs(tds_max - heatmap_tds_max) < edge_tolerance:
                li_start = li_bins[0]    # Extend to bottom edge
                li_end = li_bins[-1]     # Extend to top edge
            else:
                li_start = max(li_min, heatmap_li_min)
                li_end = min(li_max, heatmap_li_max)
            if li_start < li_end:
                plt.plot([tds_max, tds_max], [li_start, li_end], 
                        color=color, linestyle='--', linewidth=2, alpha=1)
        
        # Add text label in the center of each brine source range
        if (li_min <= heatmap_li_max and li_max >= heatmap_li_min and 
            tds_min <= heatmap_tds_max and tds_max >= heatmap_tds_min):
            # Calculate center position for the label
            li_center = (max(li_min, heatmap_li_min) + min(li_max, heatmap_li_max)) / 2
            tds_center = (max(tds_min, heatmap_tds_min) + min(tds_max, heatmap_tds_max)) / 2
            
            # Handle multi-line text for Salar de Hombre Muerto
            if name == 'Salar del Hombre Muerto':
                display_text = 'Salar del\nHombre Muerto'
            else:
                display_text = name
            
            # Add text label with translucent white background for better visibility
            plt.text(tds_center, li_center, display_text, 
                    ha='center', va='center', fontsize=9, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                             edgecolor=color, linewidth=1.5, alpha=0.7))
        
        # Create legend element
        legend_elements.append(plt.Line2D([0], [0], color=color, linestyle='-', linewidth=2, label=name))
    
    # Add WaterTAP model reference point at specific coordinates
    offset_tds = 286  # TDS in ppt
    offset_li = 0.285  # Li in molality
    plt.plot(offset_tds, offset_li, 'k*', markersize=20, markeredgewidth=1.5, 
            markeredgecolor='black', markerfacecolor='white', label='WaterTAP model')
    
    # Add WaterTAP model to legend elements
    legend_elements.append(plt.Line2D([0], [0], marker='*', color='black', 
                                     markerfacecolor='white', markeredgecolor='black',
                                     markersize=8, linestyle='', label='WaterTAP model'))
    
    # Add legend
    # plt.legend(handles=legend_elements, loc='upper left', fontsize=10, bbox_to_anchor=(0.02, 0.98))
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    
    plt.show()
    
    return pivot_data

if __name__ == "__main__":
    # Parameters - UPDATE THESE VALUES
    FLOW_VOLUME = 1.0  # No longer used for conversion (kept for compatibility)
    CSV_FILE = "parameter_sweep022026_2.csv"
    
    # Create the heat map
    result_data = create_heat_map(CSV_FILE, FLOW_VOLUME)
    print("Heat map created successfully!")
    print(f"Data shape: {result_data.shape}")
    print(f"Number of valid data points: {len(result_data.dropna().values.flatten())}")
