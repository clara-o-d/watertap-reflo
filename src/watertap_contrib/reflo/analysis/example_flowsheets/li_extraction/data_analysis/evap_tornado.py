"""Tornado analysis module for evaporation pond parameter sensitivity.

Performs one-at-a-time (OAT) sensitivity analysis and creates tornado plots
to visualize parameter impacts on key outputs.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os


def load_and_process_data(filename):
    """Load and process the parameter sweep results.
    
    Args:
        filename: Path to CSV file with parameter sweep results
        
    Returns:
        DataFrame: Processed parameter sweep data
    """
    df = pd.read_csv(filename)
    df.columns = df.columns.str.strip()
    
    # Remove leading '# ' from the first column name and its values
    first_col = df.columns[0]
    if isinstance(first_col, str) and first_col.startswith('# '):
        new_col = first_col.lstrip('# ').strip()
        df = df.rename(columns={first_col: new_col})
        if df[new_col].dtype == object:
            df[new_col] = df[new_col].str.lstrip('# ').str.strip()
    
    return df


def calculate_sensitivity(x1, y1, x2, y2):
    """Calculate sensitivity between two data points.
    
    Args:
        x1, y1: First point coordinates
        x2, y2: Second point coordinates
        
    Returns:
        tuple: (sensitivity, is_valid)
    """
    if abs(x1) < 1e-10:
        pct_change_x = abs(x2 - x1)
    else:
        pct_change_x = (x2 - x1) / x1 * 100
    
    if abs(y1) < 1e-10:
        pct_change_y = y2 - y1
    else:
        pct_change_y = (y2 - y1) / y1 * 100
    
    if abs(pct_change_x) > 0.01:
        sensitivity = pct_change_y / pct_change_x
        if abs(sensitivity) < 1000:
            return sensitivity, True
    
    return 0, False


def oat_sensitivity(df, target_col='LCOLi (USD/mt)', input_params=None):
    """Perform one-at-a-time sensitivity analysis.
    
    Args:
        df: DataFrame with parameter sweep results
        target_col: Target column for sensitivity analysis
        input_params: List of input parameters to analyze
        
    Returns:
        DataFrame: Sensitivity analysis results
    """
    if input_params is None:
        input_params = [
            'Inlet Li+ concentration',
            'Soda ash dose',
            'Li Dewatering Split Fraction',
        ]
    
    print(f"Analyzing sensitivity of '{target_col}' to {len(input_params)} input parameters:")
    sensitivity_data = []
    
    for var in input_params:
        if var not in df.columns:
            print(f"  Warning: Parameter '{var}' not found in data columns, skipping")
            continue

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
                if i >= j:
                    continue
                
                # Check if all other parameters are identical (within reasonable tolerance)
                is_oat_pair = True
                for other_param in other_params:
                    val1, val2 = row1[other_param], row2[other_param]
                    if abs(val1 - val2) > 1e-8:
                        is_oat_pair = False
                        break
                
                if is_oat_pair:
                    x1, y1 = row1[var], row1[target_col]
                    x2, y2 = row2[var], row2[target_col]
                    
                    # Calculate increase direction: from lower to higher parameter value
                    if x1 < x2:
                        x_low, y_low = x1, y1
                        x_high, y_high = x2, y2
                    else:
                        x_low, y_low = x2, y2
                        x_high, y_high = x1, y1
                    
                    # Calculate sensitivity for parameter increase (low -> high)
                    sens_inc, valid_inc = calculate_sensitivity(x_low, y_low, x_high, y_high)
                    if valid_inc:
                        oat_sensitivities_increase.append(sens_inc)
                    
                    # Calculate sensitivity for parameter decrease (high -> low)
                    sens_dec, valid_dec = calculate_sensitivity(x_high, y_high, x_low, y_low)
                    if valid_dec:
                        oat_sensitivities_decrease.append(sens_dec)
        
        # Calculate average sensitivities
        avg_increase_sensitivity = np.mean(oat_sensitivities_increase) if oat_sensitivities_increase else 0
        avg_decrease_sensitivity = np.mean(oat_sensitivities_decrease) if oat_sensitivities_decrease else 0
        
        # Calculate overall statistics
        all_oat_sensitivities = oat_sensitivities_increase + oat_sensitivities_decrease
        if not all_oat_sensitivities:
            print(f"  Warning: No valid OAT pairs found for {var}")
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
    
    # Sort by maximum absolute effect
    sensitivity_df = pd.DataFrame(sensitivity_data)
    if not sensitivity_df.empty:
        sensitivity_df['max_abs_effect'] = sensitivity_df[['avg_increase_sensitivity', 'avg_decrease_sensitivity']].abs().max(axis=1)
        sensitivity_df = sensitivity_df.sort_values(by='max_abs_effect', ascending=False)
    
    return sensitivity_df


def create_tornado_plot(sensitivity_df, target_col, title=None, param_name_mapping=None):
    """Create tornado plot for sensitivity analysis results."""
    if title is None:
        title = f"Sensitivity Analysis: {target_col}"
    
    if sensitivity_df.empty:
        print("No valid sensitivity data to plot")
        return None, None
    
    sensitivity_df['variable'] = sensitivity_df['variable'].astype(str).str.lstrip('# ').str.strip()
    sensitivity_df = sensitivity_df.sort_values(by='max_abs_effect', ascending=True)
    
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.set_frame_on(False)

    y_pos = np.arange(len(sensitivity_df))
    
    # Apply custom parameter name mapping if provided
    if param_name_mapping is not None:
        sensitivity_df['display_name'] = sensitivity_df['variable'].map(param_name_mapping).fillna(sensitivity_df['variable'])
    else:
        sensitivity_df['display_name'] = sensitivity_df['variable']
    
    # Create bars showing increase and decrease sensitivities on opposite sides
    bar_width = 0.35
    
    # Determine bar styles based on relationship direction
    increase_hatch = []
    decrease_hatch = []
    
    for _, row in sensitivity_df.iterrows():
        increase_sens = row['avg_increase_sensitivity']
        
        if increase_sens >= 0:
            # Direct relationship: parameter increase leads to target increase
            increase_hatch.append('')
            decrease_hatch.append('')
        else:
            # Inverse relationship: parameter increase leads to target decrease
            increase_hatch.append('///')
            decrease_hatch.append('///')
    
    # Bars for parameter increase effects (right side, positive direction)
    ax.barh(
        y_pos,
        sensitivity_df['avg_increase_sensitivity'],
        height=bar_width,
        color='#20A387', #55C667 #20A387
        alpha=0.7,
        hatch=increase_hatch,
        label='Parameter increase effect'
    )
    
    # Bars for parameter decrease effects (left side, negative direction)
    ax.barh(
        y_pos,
        -sensitivity_df['avg_decrease_sensitivity'],
        height=bar_width,
        color='#20A387',
        alpha=0.7,
        hatch=decrease_hatch,
        label='Parameter decrease effect'
    )
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(sensitivity_df['display_name'], fontsize=16)
    ax.set_title(title, fontsize=20, fontweight='bold', pad=16)
    ax.set_xlabel(f'% change in {target_col}\nper % change in parameter', fontsize=18)
    ax.axvline(x=0, color='black', linestyle='-', linewidth=0.8)
    ax.grid(True, alpha=0.3, axis='x')
    ax.set_xlim(-0.05, 0.05)
    ax.tick_params(axis='x', labelsize=16)
    
    # Create custom legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#20A387', alpha=0.7, label='Positive'),
        Patch(facecolor='#20A387', alpha=0.7, hatch='///', label='Negative')
    ]
    
    ax.legend(handles=legend_elements, loc='lower right', fontsize=16)
    plt.tight_layout()
    return fig, ax





def main():
    """Main function to run the sensitivity analysis."""
    target_col = 'LCOLi2CO3 (USD/kg)'
    possible_files = ['processing_parameter_sweep.csv']
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
        return

    # Define the specific model inputs being swept in the current parameter sweep
    input_vars = [
        'Inlet Li+ concentration',
        'Soda ash dose',
        'Li Dewatering Split Fraction',
    ]
    
    # Confirm input/output match for each parameter
    for var in input_vars:
        resultant_var = f"Resultant {var}"
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
        print("Warning: Very few valid data points. Cannot proceed with sensitivity analysis.")
        return
    
    # Create tornado plot
    print(f"\nCreating tornado plot for: {target_col}")
    sensitivity_df = oat_sensitivity(df, target_col, input_params=input_vars)
    
    if not sensitivity_df.empty:
        # Define custom parameter name mapping for display
        param_name_mapping = {
            'Inlet Li+ concentration': 'Inlet\nLi+ concentration',
            'Soda ash dose': 'Soda ash\ndose',
            'Li Dewatering Split Fraction': 'Li\nDewatering\nSplit\nFraction',
        }
        
        fig, ax = create_tornado_plot(sensitivity_df, target_col, 
                                    title=f"Parameter sensitivity",
                                    param_name_mapping=param_name_mapping)
        if fig is not None:
            plt.savefig('tornado_plot_processing_lcoli2co3.png', dpi=300, bbox_inches='tight')
            print("Tornado plot saved as 'tornado_plot_processing_lcoli2co3.png'")
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