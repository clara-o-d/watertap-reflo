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
    """
    Classic tornado sensitivity: for each parameter, calculate percent change in LCOLi from median→min and median→max,
    using averages at those values, and divide by the absolute percent change in parameter.
    """
    if input_params is None:
        input_params = [
            'land_cost',
            'pond_liner_cost',
            'dye_cost',
            'shipping_cost',
        ]
    print(f"Analyzing sensitivity of '{target_col}' to {len(input_params)} input parameters (classic tornado, median→min/max, abs denominator):")
    sensitivity_data = []
    for var in input_params:
        if var not in df.columns:
            print(f"  Warning: Parameter '{var}' not found in data columns, skipping")
            continue
        valid = df[[var, target_col]].dropna()
        if valid.empty:
            print(f"  Warning: No valid data for {var}, skipping")
            continue
        grouped = valid.groupby(var)[target_col].mean().reset_index()
        if len(grouped) < 2:
            print(f"  Warning: Not enough unique values for {var}, skipping")
            continue
        x_min = grouped[var].min()
        x_median = grouped[var].median()
        x_max = grouped[var].max()
        y_min = grouped.loc[grouped[var] == x_min, target_col].values[0]
        y_median = grouped.loc[grouped[var] == x_median, target_col].values[0]
        y_max = grouped.loc[grouped[var] == x_max, target_col].values[0]
        # median→min
        if x_median == 0:
            pct_change_x_min = abs(x_min - x_median)
        else:
            pct_change_x_min = abs((x_min - x_median) / x_median * 100)
        if y_median == 0:
            pct_change_y_min = y_min - y_median
        else:
            pct_change_y_min = (y_min - y_median) / y_median * 100
        sensitivity_median_min = pct_change_y_min / pct_change_x_min if pct_change_x_min != 0 else float('nan')
        # median→max
        if x_median == 0:
            pct_change_x_max = abs(x_max - x_median)
        else:
            pct_change_x_max = abs((x_max - x_median) / x_median * 100)
        if y_median == 0:
            pct_change_y_max = y_max - y_median
        else:
            pct_change_y_max = (y_max - y_median) / y_median * 100
        sensitivity_median_max = pct_change_y_max / pct_change_x_max if pct_change_x_max != 0 else float('nan')
        sensitivity_data.append({
            'variable': var,
            'sensitivity_median_min': sensitivity_median_min,
            'sensitivity_median_max': sensitivity_median_max,
            'x_min': x_min,
            'x_median': x_median,
            'x_max': x_max,
            'y_min': y_min,
            'y_median': y_median,
            'y_max': y_max,
            'valid_points': len(valid)
        })
        print(f"  {var}: median→min sensitivity={sensitivity_median_min:.3f}, median→max sensitivity={sensitivity_median_max:.3f} (classic tornado, abs denominator)")
    # Sort by the largest absolute effect (either direction)
    sensitivity_df = pd.DataFrame(sensitivity_data)
    if not sensitivity_df.empty:
        sensitivity_df['max_abs_sensitivity'] = sensitivity_df[['sensitivity_median_min', 'sensitivity_median_max']].abs().max(axis=1)
        sensitivity_df = sensitivity_df.sort_values(by='max_abs_sensitivity', ascending=False)
    return sensitivity_df

def create_tornado_plot(sensitivity_df, target_col, title=None):
    if title is None:
        title = f"Sensitivity Analysis: {target_col}"
    if sensitivity_df.empty:
        print("No valid sensitivity data to plot")
        return None, None
    sensitivity_df['variable'] = sensitivity_df['variable'].astype(str).str.lstrip('# ').str.strip()
    sensitivity_df = sensitivity_df.sort_values(by='max_abs_sensitivity', ascending=True)
    fig, ax = plt.subplots(figsize=(11.5, 7))
    y_pos = np.arange(len(sensitivity_df))
    bar_width = 0.35
    bars1 = ax.barh(
        y_pos,
        sensitivity_df['sensitivity_median_max'],
        height=bar_width,
        color='#3b82f6',
        alpha=0.7,
        label='Increase (median→max)'
    )
    bars2 = ax.barh(
        y_pos,
        sensitivity_df['sensitivity_median_min'],
        height=bar_width,
        color='#ef4444',
        alpha=0.7,
        label='Decrease (median→min)'
    )
    ax.set_yticks(y_pos)
    ax.set_yticklabels(sensitivity_df['variable'], fontsize=12)
    ax.set_xlabel(f'Percent change in {target_col} per percent change in parameter', fontsize=11)
    ax.set_title(title, fontsize=12, fontweight='bold', pad=20)
    ax.axvline(x=0, color='black', linestyle='-', linewidth=0.8)
    ax.grid(True, alpha=0.3, axis='x')
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc='lower right', fontsize=12)
    plt.tight_layout()
    return fig, ax

def create_data_summary_plot(df, target_col='levelized cost of lithium (USD_2023/m^3)'):
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
        'land_cost',
        'pond_liner_cost',
        'recovered_solids_revenue',
        'dye_cost',
        'shipping_cost',
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
                                    title=f"Costing parameter sensitivity analysis: {target_col}")
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
            print(f"  {row['variable']}: {row['valid_points']} valid points")
            if not np.isnan(row['sensitivity_median_min']):
                print(f"    Increase sensitivity (median→min): {row['sensitivity_median_min']:.3f}")
            if not np.isnan(row['sensitivity_median_max']):
                print(f"    Increase sensitivity (median→max): {row['sensitivity_median_max']:.3f}")
    else:
        print("No valid sensitivity data calculated.")
    
    print("\nTornado plot analysis completed!")

if __name__ == "__main__":
    main()