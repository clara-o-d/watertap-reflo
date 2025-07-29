import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os


def load_and_process_data(filename):
    """Load and process the parameter sweep results"""
    df = pd.read_csv(filename)
    df.columns = df.columns.str.strip()
    
    # Remove leading '# ' from the first column name and its values
    first_col = df.columns[0]
    if isinstance(first_col, str) and first_col.startswith('# '):
        new_col = first_col.lstrip('# ').strip()
        df = df.rename(columns={first_col: new_col})
        # Also strip leading '# ' from the values in this column if they are strings
        if df[new_col].dtype == object:
            df[new_col] = df[new_col].str.lstrip('# ').str.strip()
    
    # Print available columns for debugging
    print(f"Available columns: {list(df.columns)}")
    
    return df

def oat_sensitivity(df, target_col='levelized cost of lithium (USD_2023/m^3)', input_params=None):
    if input_params is None:
        input_params = [
            'land_cost',
            'pond_liner_cost',
            'recovered_solids_revenue',
            'dye_cost',
            'shipping_cost',
        ]
    print(f"Analyzing sensitivity of '{target_col}' to {len(input_params)} input parameters (true OAT analysis - only comparing pairs where one parameter differs):")
    sensitivity_data = []
    for var in input_params:
        if var not in df.columns:
            print(f"  Warning: Parameter '{var}' not found in data columns, skipping")
            continue
        # Work with full dataframe but filter for valid data for this parameter and target
        valid_mask = df[var].notna() & df[target_col].notna()
        valid_data = df[valid_mask]
        
        if valid_data.empty:
            print(f"  Warning: No valid data for {var}, skipping")
            continue
        
        # Calculate mean values for reference point
        x_mean = valid_data[var].mean()
        y_mean = valid_data[target_col].mean()
        
        # Find valid one-at-a-time (OAT) pairs where only this parameter differs
        other_params = [p for p in input_params if p != var and p in df.columns]
        
        oat_sensitivities_increase = []
        oat_sensitivities_decrease = []
        
        # Compare each pair of data points to find valid OAT comparisons
        for i, row1 in valid_data.iterrows():
            for j, row2 in valid_data.iterrows():
                if i >= j:  # Avoid duplicate comparisons
                    continue
                
                # Check if all other parameters are identical (within reasonable tolerance)
                is_oat_pair = True
                for other_param in other_params:
                    val1, val2 = row1[other_param], row2[other_param]
                    # Use reasonable tolerance for floating point comparison (1e-8)
                    if abs(val1 - val2) > 1e-8:
                        is_oat_pair = False
                        break
                
                if is_oat_pair:
                    # Calculate sensitivity for this OAT pair in both directions
                    x1, y1 = row1[var], row1[target_col]
                    x2, y2 = row2[var], row2[target_col]
                    
                    # Calculate increase direction: from lower to higher parameter value
                    if x1 < x2:
                        # x1 -> x2 is parameter increase
                        x_low, y_low = x1, y1
                        x_high, y_high = x2, y2
                    else:
                        # x2 -> x1 is parameter increase 
                        x_low, y_low = x2, y2
                        x_high, y_high = x1, y1
                    
                    # Calculate sensitivity for parameter increase (low -> high)
                    if abs(x_low) < 1e-10:
                        pct_change_x_inc = abs(x_high - x_low)
                    else:
                        pct_change_x_inc = (x_high - x_low) / x_low * 100
                    
                    if abs(y_low) < 1e-10:
                        pct_change_y_inc = y_high - y_low
                    else:
                        pct_change_y_inc = (y_high - y_low) / y_low * 100
                    
                    if abs(pct_change_x_inc) > 0.01:  # At least 0.01% change
                        sensitivity_inc = pct_change_y_inc / pct_change_x_inc
                        if abs(sensitivity_inc) < 1000:  # Reasonable bound
                            oat_sensitivities_increase.append(sensitivity_inc)
                    
                    # Calculate sensitivity for parameter decrease (high -> low)
                    if abs(x_high) < 1e-10:
                        pct_change_x_dec = abs(x_low - x_high)
                    else:
                        pct_change_x_dec = (x_low - x_high) / x_high * 100
                    
                    if abs(y_high) < 1e-10:
                        pct_change_y_dec = y_low - y_high
                    else:
                        pct_change_y_dec = (y_low - y_high) / y_high * 100
                    
                    if abs(pct_change_x_dec) > 0.01:  # At least 0.01% change
                        sensitivity_dec = pct_change_y_dec / pct_change_x_dec
                        if abs(sensitivity_dec) < 1000:  # Reasonable bound
                            oat_sensitivities_decrease.append(sensitivity_dec)
        
        # Calculate average sensitivities for increase and decrease
        avg_increase_sensitivity = np.mean(oat_sensitivities_increase) if oat_sensitivities_increase else 0
        avg_decrease_sensitivity = np.mean(oat_sensitivities_decrease) if oat_sensitivities_decrease else 0
        
        # Calculate overall statistics
        all_oat_sensitivities = oat_sensitivities_increase + oat_sensitivities_decrease
        if not all_oat_sensitivities:
            print(f"  Warning: No valid OAT pairs found for {var} (parameter changes are coupled with other parameter changes)")
            continue
        
        avg_sensitivity = np.mean(all_oat_sensitivities)
        abs_avg_sensitivity = np.mean([abs(s) for s in all_oat_sensitivities])
        
        # Get basic statistics for reference
        x_min, x_max = valid_data[var].min(), valid_data[var].max()
        y_min, y_max = valid_data[target_col].min(), valid_data[target_col].max()
        x_median, y_median = valid_data[var].median(), valid_data[target_col].median()
        
        sensitivity_data.append({
            'variable': var,
            'avg_sensitivity': avg_sensitivity,
            'abs_avg_sensitivity': abs_avg_sensitivity,
            'avg_increase_sensitivity': avg_increase_sensitivity,
            'avg_decrease_sensitivity': avg_decrease_sensitivity,
            'num_increase_points': len(oat_sensitivities_increase),
            'num_decrease_points': len(oat_sensitivities_decrease),
            'num_point_sensitivities': len(all_oat_sensitivities),
            'x_min': x_min,
            'x_median': x_median,
            'x_max': x_max,
            'y_min': y_min,
            'y_median': y_median,
            'y_max': y_max,
            'x_mean': x_mean,
            'y_mean': y_mean,
            'valid_points': len(valid_data)
        })
        print(f"  {var}: increase sensitivity={avg_increase_sensitivity:.3f} (n={len(oat_sensitivities_increase)} OAT pairs), decrease sensitivity={avg_decrease_sensitivity:.3f} (n={len(oat_sensitivities_decrease)} OAT pairs)")
    
    # Sort by maximum absolute effect (either increase or decrease)
    sensitivity_df = pd.DataFrame(sensitivity_data)
    if not sensitivity_df.empty:
        sensitivity_df['max_abs_effect'] = sensitivity_df[['avg_increase_sensitivity', 'avg_decrease_sensitivity']].abs().max(axis=1)
        sensitivity_df = sensitivity_df.sort_values(by='max_abs_effect', ascending=False)
    return sensitivity_df

def create_tornado_plot(sensitivity_df, target_col, title=None):
    if title is None:
        title = f"Sensitivity Analysis: {target_col}"
    if sensitivity_df.empty:
        print("No valid sensitivity data to plot")
        return None, None
    sensitivity_df['variable'] = sensitivity_df['variable'].astype(str).str.lstrip('# ').str.strip()
    sensitivity_df = sensitivity_df.sort_values(by='max_abs_effect', ascending=True)
    fig, ax = plt.subplots(figsize=(11.5, 7))
    y_pos = np.arange(len(sensitivity_df))
    
    # Create bars showing increase and decrease sensitivities on opposite sides
    bar_width = 0.35
    
    # Bars for parameter increase effects (right side, positive direction)
    bars_increase = ax.barh(
        y_pos,
        sensitivity_df['avg_increase_sensitivity'],
        height=bar_width,
        color='#3b82f6',
        alpha=0.7,
        label='Parameter increase effect'
    )
    
    # Bars for parameter decrease effects (left side, negative direction)
    bars_decrease = ax.barh(
        y_pos,
        -sensitivity_df['avg_decrease_sensitivity'],  # Make negative to show on left side
        height=bar_width,
        color='#ef4444',
        alpha=0.7,
        label='Parameter decrease effect'
    )
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(sensitivity_df['variable'], fontsize=12)
    ax.set_xlabel(f'Percent change in {target_col} per percent change in parameter', fontsize=11)
    ax.set_title(title, fontsize=12, fontweight='bold', pad=20)
    ax.axvline(x=0, color='black', linestyle='-', linewidth=0.8)
    ax.grid(True, alpha=0.3, axis='x')
    
    # Create custom legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#3b82f6', alpha=0.7, label='Parameter increase effect'),
        Patch(facecolor='#ef4444', alpha=0.7, label='Parameter decrease effect')
    ]
    
    ax.legend(handles=legend_elements, loc='lower right', fontsize=12)
    plt.tight_layout()
    return fig, ax

def create_data_summary_plot(df, target_col='LCOLi_mass (USD/mt)'):
    """Create a summary plot showing data availability and basic statistics"""
    param_cols = [col for col in df.columns if col != target_col]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Plot 1: Data availability
    valid_counts = []
    param_names = []
    for col in param_cols:
        valid_mask = ~(df[col].isna() | df[target_col].isna())
        valid_counts.append(valid_mask.sum())
        param_names.append(col)
    
    bars = ax1.bar(range(len(param_names)), valid_counts, color='skyblue', alpha=0.7)
    ax1.set_xlabel('Parameters')
    ax1.set_ylabel('Number of Valid Data Points')
    ax1.set_title('Data Availability by Parameter')
    ax1.set_xticks(range(len(param_names)))
    ax1.set_xticklabels(param_names, rotation=45, ha='right')
    
    # Add value labels on bars
    for bar, count in zip(bars, valid_counts):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                str(count), ha='center', va='bottom')
    
    # Plot 2: Target variable distribution
    valid_target = df[target_col].dropna()
    if len(valid_target) > 0:
        ax2.hist(valid_target, bins=min(20, len(valid_target)//2), alpha=0.7, color='lightgreen')
        ax2.set_xlabel(target_col)
        ax2.set_ylabel('Frequency')
        ax2.set_title(f'Distribution of {target_col}')
        ax2.axvline(valid_target.mean(), color='red', linestyle='--', label=f'Mean: {valid_target.mean():.2e}')
        ax2.axvline(valid_target.median(), color='orange', linestyle='--', label=f'Median: {valid_target.median():.2e}')
        ax2.legend()
    else:
        ax2.text(0.5, 0.5, 'No valid data', ha='center', va='center', transform=ax2.transAxes)
        ax2.set_title(f'Distribution of {target_col}')
    
    plt.tight_layout()
    return fig, (ax1, ax2)

def main():
    target_col = 'LCOLi_mass (USD/mt)'
    possible_files = ['pond_sensitivity.csv', 'test_pond_sensitivity.csv']
    df = None
    
    for filename in possible_files:
        if os.path.exists(filename):
            print(f"Loading data from '{filename}'...")
            try:
                df = load_and_process_data(filename)
                print(f"Successfully loaded {len(df)} data points with {len(df.columns)} variables.")
                break
            except Exception as e:
                print(f"Error loading {filename}: {e}")
                continue
    
    if df is None:
        print("Error: No parameter sweep results found. Please run the parameter sweep first.")
        print("Expected files: pond_sensitivity.csv or test_pond_sensitivity.csv")
        return

    # Define the specific model inputs being swept in the current parameter sweep (exclude WACC)
    input_vars = [
        # 'inlet_li_concentration',
        # 'inlet_vapor_temperature',
        # 'evaporation_rate_adjustment_factor',
        # 'land_cost',
        # 'pond_liner_cost',
        # 'recovered_solids_revenue',
        # 'dye_cost',
        # 'shipping_cost',
        'dike_height',
        'pipeline_length',
        'utilization_factor',
    ]
    # Confirm input/output match for each parameter
    for var in input_vars:
        resultant_var = f"resultant {var}"
        if resultant_var in df.columns and var in df.columns:
            mismatch = (df[var] != df[resultant_var]) & ~(df[var].isna() | df[resultant_var].isna())
            if mismatch.any():
                print(f"WARNING: Mismatch found between '{var}' and '{resultant_var}' in {mismatch.sum()} rows.")
            else:
                print(f"OK: '{var}' matches '{resultant_var}' for all valid rows.")
        elif var in df.columns:
            print(f"OK: '{var}' found in data (no resultant variable expected).")
        else:
            print(f"WARNING: '{var}' not found in data columns.")
    
    # Check data quality
    total_points = len(df)
    valid_points = df[target_col].notna().sum()
    print(f"\nData Quality Summary:")
    print(f"  Total data points: {total_points}")
    print(f"  Valid {target_col} values: {valid_points}")
    print(f"  Success rate: {valid_points/total_points*100:.1f}%")
    
    if valid_points < 3:
        print("Warning: Very few valid data points. Creating data summary plot only.")
        fig, axes = create_data_summary_plot(df, target_col)
        plt.savefig('data_summary_plot.png', dpi=300, bbox_inches='tight')
        print("Data summary plot saved as 'data_summary_plot.png'")
        plt.show()
        return
    
    # Create data summary plot
    print(f"\nCreating data summary plot...")
    fig, axes = create_data_summary_plot(df, target_col)
    plt.savefig('data_summary_plot.png', dpi=300, bbox_inches='tight')
    print("Data summary plot saved as 'data_summary_plot.png'")
    plt.close()
    
    # Create tornado plot
    print(f"\nCreating tornado plot for: {target_col}")
    sensitivity_df = oat_sensitivity(df, target_col, input_params=input_vars)
    
    if not sensitivity_df.empty:
        fig, ax = create_tornado_plot(sensitivity_df, target_col, 
                                    title=f"Design parameter sensitivity analysis: {target_col}")
        if fig is not None:
            plt.savefig('tornado_plot_pond_lcoli.png', dpi=300, bbox_inches='tight')
            print("Tornado plot saved as 'tornado_plot_pond_lcoli.png'")
            plt.show()
        
        # Save sensitivity data with additional info
        sensitivity_df.to_csv('sensitivity_analysis_pond_lcoli.csv', index=False)
        print("Sensitivity analysis results saved to 'sensitivity_analysis_pond_lcoli.csv'")
        
        # Print summary of findings
        print(f"\nSensitivity Analysis Summary:")
        print(f"  Parameters analyzed: {len(sensitivity_df)}")
        for _, row in sensitivity_df.iterrows():
            print(f"  {row['variable']}: {row['valid_points']} valid points, {row['num_point_sensitivities']} OAT pairs")
            print(f"    Parameter increase effect: {row['avg_increase_sensitivity']:.3f} (n={row['num_increase_points']} OAT pairs)")
            print(f"    Parameter decrease effect: {row['avg_decrease_sensitivity']:.3f} (n={row['num_decrease_points']} OAT pairs)")
            print(f"    Maximum absolute effect: {row['max_abs_effect']:.3f}")
    else:
        print("No valid sensitivity data calculated.")
    
    print("\nTrue OAT sensitivity analysis completed!")

if __name__ == "__main__":
    main()