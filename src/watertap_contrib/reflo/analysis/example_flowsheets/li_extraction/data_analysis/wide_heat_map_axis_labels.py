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
        'Resultant inlet Li+ concentration', 'Resultant inlet TDS concentration',
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
    
    # Convert levelized cost to thousands per metric ton
    df_filtered['levelized_cost_thousands'] = df_filtered['LCOLi (USD/mt)'] / 1000
    
    # Create binned heat map data
    num_bins = 10  # Number of bins for each axis
    
    # Create bins for Li+ and TDS concentrations
    li_bins = np.linspace(df_filtered['inlet_li_conc'].min(), df_filtered['inlet_li_conc'].max(), num_bins + 1)
    tds_bins = np.linspace(df_filtered['inlet_tds_conc'].min(), df_filtered['inlet_tds_conc'].max(), num_bins + 1)
    
    # Assign each data point to bins
    df_filtered['li_bin'] = pd.cut(df_filtered['inlet_li_conc'], bins=li_bins, labels=False, include_lowest=True)
    df_filtered['tds_bin'] = pd.cut(df_filtered['inlet_tds_conc'], bins=tds_bins, labels=False, include_lowest=True)
    
    # Create binned pivot table
    pivot_data = df_filtered.pivot_table(
        values='levelized_cost_thousands',
        index='li_bin',
        columns='tds_bin',
        aggfunc='mean'
    )
    
    # Create bin center values for plotting
    li_centers = (li_bins[:-1] + li_bins[1:]) / 2
    tds_centers = (tds_bins[:-1] + tds_bins[1:]) / 2
    
    # Interpolate to fill missing values in the binned grid
    pivot_filled = (
        pivot_data
            .interpolate(method='linear', axis=1, limit_direction='both')
            .interpolate(method='linear', axis=0, limit_direction='both')
            .ffill(axis=1).bfill(axis=1)
            .ffill(axis=0).bfill(axis=0)
    )
    if pivot_filled.isna().any().any():
        pivot_filled = pivot_filled.fillna(pivot_filled.stack().mean())

    # Calculate baseline values for percentage calculations (using bin centers)
    baseline_li = li_centers[-1]  # Use highest bin center as baseline
    baseline_tds = tds_centers[-1]  # Use highest bin center as baseline
    baseline_cost = pivot_data.iloc[-1, -1]  # Use highest bin value as baseline
    
    # Create percentage variation labels for x-axis (TDS concentrations)
    x_labels = []
    for col in tds_centers:
        if abs(col - baseline_tds) < 0.01:  # Use small tolerance for float comparison
            x_labels.append(f"{col:.2f}\n(0%)")
        else:
            pct_change = ((col - baseline_tds) / baseline_tds) * 100
            sign = "+" if pct_change > 0 else ""
            x_labels.append(f"{col:.2f}\n({sign}{pct_change:.0f}%)")
    
    # Create percentage variation labels for y-axis (Li+ concentrations)
    y_labels = []
    for idx in li_centers:
        if abs(idx - baseline_li) < 0.01:  # Use small tolerance for float comparison
            y_labels.append(f"{idx:.4f}\n(0%)")
        else:
            pct_change = ((idx - baseline_li) / baseline_li) * 100
            sign = "+" if pct_change > 0 else ""
            y_labels.append(f"{idx:.4f}\n({sign}{pct_change:.0f}%)")
    
    # Create the heat map
    plt.figure(figsize=(10, 8))
    
    # Create heat map using imshow (with binned data)
    heatmap = plt.imshow(pivot_data.values, cmap='viridis', aspect='auto', 
                         extent=[tds_centers.min(), tds_centers.max(), 
                                li_centers.min(), li_centers.max()],
                         origin='lower', vmin=baseline_cost)
    
    # Add colorbar with the same styling
    cbar = plt.colorbar(heatmap, label='Levelized cost (thousands $/t Li⁺)')
    cbar.ax.set_ylabel('Levelized cost (thousands $/t Li⁺)', fontsize=14)
    cbar.ax.tick_params(labelsize=12)
    
    # Colorbar ticks: start at base case (0% at bottom)
    vmax = np.nanmax(pivot_data.values)
    num_ticks = 6
    cbar_ticks = np.linspace(baseline_cost, vmax, num=num_ticks)
    cbar.set_ticks(cbar_ticks)
    cbar.set_ticklabels([
        f"{t:.1f}\n(0%)" if i == 0 else f"{t:.1f}\n(+{((t-baseline_cost)/baseline_cost)*100:.0f}%)"
        for i, t in enumerate(cbar_ticks)
    ])
    
    # Set custom x and y tick labels with percentage variations (evenly spaced ticks)
    max_ticks = 6
    
    # Create evenly spaced tick positions across the full range using bin centers
    x_tick_positions = np.linspace(tds_centers.min(), tds_centers.max(), num=max_ticks)
    y_tick_positions = np.linspace(li_centers.min(), li_centers.max(), num=max_ticks)
    
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
    
    plt.xticks(x_tick_positions, x_tick_labels, rotation=45, ha='right', fontsize=12)
    plt.yticks(y_tick_positions, y_tick_labels, fontsize=12)
    
    # Set labels and title
    plt.xlabel('Inlet TDS concentration (g/L)', fontsize=14)
    plt.ylabel('Inlet Li$^+$ concentration (g/L)', fontsize=14)
    plt.title('Li$^+$ brine levelized cost estimates and % change', fontsize=16, fontweight='bold')
    
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
    
    # Get heat map boundaries
    heatmap_li_min, heatmap_li_max = li_centers.min(), li_centers.max()
    heatmap_tds_min, heatmap_tds_max = tds_centers.min(), tds_centers.max()
    
    # Add colored range indicators on x and y axes for each brine source
    legend_elements = []
    for name, ranges in brine_ranges.items():
        li_min, li_max = ranges['li_range']
        tds_min, tds_max = ranges['tds_range']
        color = ranges['color']
        
        # Add colored range indicators on x-axis (TDS concentrations)
        if tds_min <= heatmap_tds_max and tds_max >= heatmap_tds_min:
            # Draw colored line segment directly on x-axis
            tds_start = max(tds_min, heatmap_tds_min)
            tds_end = min(tds_max, heatmap_tds_max)
            if tds_start < tds_end:
                # Draw thick colored line on x-axis at y=0 (bottom of heat map)
                plt.plot([tds_start, tds_end], 
                        [heatmap_li_min, heatmap_li_min], 
                        color=color, linewidth=10, alpha=1)
        
        # Add colored range indicators on y-axis (Li+ concentrations)
        if li_min <= heatmap_li_max and li_max >= heatmap_li_min:
            # Draw colored line segment directly on y-axis
            li_start = max(li_min, heatmap_li_min)
            li_end = min(li_max, heatmap_li_max)
            if li_start < li_end:
                # Draw thick colored line on y-axis at x=0 (left of heat map)
                plt.plot([heatmap_tds_min, heatmap_tds_min], 
                        [li_start, li_end], 
                        color=color, linewidth=10, alpha=1)
        
        # Draw dotted outline of the range rectangle on the heat map
        # Top horizontal line - only if it intersects with heat map
        if li_max >= heatmap_li_min and li_max <= heatmap_li_max:
            tds_start = max(tds_min, heatmap_tds_min)
            tds_end = min(tds_max, heatmap_tds_max)
            if tds_start < tds_end:
                plt.plot([tds_start, tds_end], [li_max, li_max], 
                        color=color, linestyle='--', linewidth=3, alpha=1)
        
        # Bottom horizontal line - only if it intersects with heat map
        if li_min >= heatmap_li_min and li_min <= heatmap_li_max:
            tds_start = max(tds_min, heatmap_tds_min)
            tds_end = min(tds_max, heatmap_tds_max)
            if tds_start < tds_end:
                plt.plot([tds_start, tds_end], [li_min, li_min], 
                        color=color, linestyle='--', linewidth=3, alpha=1)
        
        # Left vertical line - only if it intersects with heat map
        if tds_min >= heatmap_tds_min and tds_min <= heatmap_tds_max:
            li_start = max(li_min, heatmap_li_min)
            li_end = min(li_max, heatmap_li_max)
            if li_start < li_end:
                plt.plot([tds_min, tds_min], [li_start, li_end], 
                        color=color, linestyle='--', linewidth=3, alpha=1)
        
        # Right vertical line - only if it intersects with heat map
        if tds_max >= heatmap_tds_min and tds_max <= heatmap_tds_max:
            li_start = max(li_min, heatmap_li_min)
            li_end = min(li_max, heatmap_li_max)
            if li_start < li_end:
                plt.plot([tds_max, tds_max], [li_start, li_end], 
                        color=color, linestyle='--', linewidth=3, alpha=1)
        
        # Add text label in the center of each brine source range
        if (li_min <= heatmap_li_max and li_max >= heatmap_li_min and 
            tds_min <= heatmap_tds_max and tds_max >= heatmap_tds_min):
            # Calculate center position for the label
            li_center = (max(li_min, heatmap_li_min) + min(li_max, heatmap_li_max)) / 2
            tds_center = (max(tds_min, heatmap_tds_min) + min(tds_max, heatmap_tds_max)) / 2
            
            # Handle multi-line text for Salar de Hombre Muerto
            if name == 'Salar de Hombre Muerto':
                display_text = 'Salar de\nHombre Muerto'
            else:
                display_text = name
            
        
            # Add text label with translucent white background for better visibility
            plt.text(tds_center, li_center, display_text, 
                    ha='center', va='center', fontsize=12, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                             edgecolor=color, linewidth=2, alpha=0.7))
        
        # Create legend element
        legend_elements.append(plt.Line2D([0], [0], color=color, linestyle='-', linewidth=3, label=name))
    
    # Add WaterTAP model reference point at maximum concentrations (slightly offset)
    offset_tds = baseline_tds - ((heatmap_tds_max - heatmap_tds_min) * 0.01)  # Move left by 2% of TDS range
    offset_li = baseline_li - ((heatmap_li_max - heatmap_li_min) * 0.01)      # Move down by 2% of Li range
    plt.plot(offset_tds, offset_li, 'k*', markersize=30, markeredgewidth=2, 
             markeredgecolor='black', markerfacecolor='white', label='WaterTAP model')
    
    # Add WaterTAP model to legend elements
    legend_elements.append(plt.Line2D([0], [0], marker='*', color='black', 
                                     markerfacecolor='white', markeredgecolor='black',
                                     markersize=8, linestyle='', label='WaterTAP model'))
    
    # Add legend
    # plt.legend(handles=legend_elements, loc='upper left', fontsize=12, bbox_to_anchor=(0.02, 0.98))
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    
    plt.show()
    
    return pivot_filled

if __name__ == "__main__":
    # Parameters - UPDATE THESE VALUES
    FLOW_VOLUME = 1.280  # Flow volume for mass fraction conversion
    CSV_FILE = "watertap-reflo/src/parameter_sweep1.csv"
    
    # Create the heat map
    result_data = create_heat_map(CSV_FILE, FLOW_VOLUME)
    print("Heat map created successfully!")
    print(f"Data shape: {result_data.shape}")
    print(f"Number of valid data points: {len(result_data.dropna().values.flatten())}")
