import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os


def load_and_process_data(filename):
    """Load and process the parameter sweep results"""
    df = pd.read_csv(filename)
    df.columns = df.columns.str.strip()
    
    # Print available columns for debugging
    print(f"Available columns: {list(df.columns)}")
    
    return df

def oat_sensitivity(df, target_col='pond capital cost (USD_2023)'):
    """
    One-at-a-time sensitivity analysis that handles nan values
    
    Args:
        df: DataFrame with parameter sweep results
        target_col: Column name for the target variable to analyze
    """
    # Get parameter columns (exclude output columns)
    output_cols = [target_col]
    param_cols = [col for col in df.columns if col not in output_cols]
    
    print(f"Analyzing sensitivity of '{target_col}' to {len(param_cols)} parameters:")
    for col in param_cols:
        print(f"  - {col}")
    
    sensitivity_data = []
    for var in param_cols:
        # Filter out rows with nan values for this parameter and target
        valid_mask = ~(df[var].isna() | df[target_col].isna())
        if valid_mask.sum() < 3:  # Need at least 3 valid points
            print(f"  Warning: Only {valid_mask.sum()} valid data points for {var}, skipping")
            continue
            
        x_vals = df[var].values[valid_mask]
        y_vals = df[target_col].values[valid_mask]
        
        # Find median, min, max x
        x_median = np.median(x_vals)
        x_min = np.min(x_vals)
        x_max = np.max(x_vals)
        
        # Find y at closest to median, min, max x
        y_med = y_vals[np.argmin(np.abs(x_vals - x_median))]
        y_min = y_vals[np.argmin(np.abs(x_vals - x_min))]
        y_max = y_vals[np.argmin(np.abs(x_vals - x_max))]
        
        # Calculate percentage changes
        # Increase: median -> max
        x_range_pct_inc = (x_max - x_median) / x_median * 100 if x_median != 0 else np.nan
        y_range_pct_inc = (y_max - y_med) / y_med * 100 if y_med != 0 else np.nan
        pct_per_pct_inc = y_range_pct_inc / x_range_pct_inc if x_range_pct_inc and not np.isnan(x_range_pct_inc) else np.nan
        
        # Decrease: median -> min
        x_range_pct_dec = (x_min - x_median) / x_median * 100 if x_median != 0 else np.nan
        y_range_pct_dec = (y_min - y_med) / y_med * 100 if y_med != 0 else np.nan
        pct_per_pct_dec = y_range_pct_dec / x_range_pct_dec if x_range_pct_dec and not np.isnan(x_range_pct_dec) else np.nan
        
        # Only include if we have valid sensitivity values
        if not (np.isnan(pct_per_pct_inc) and np.isnan(pct_per_pct_dec)):
            sensitivity_data.append({
                'variable': var,
                'pct_per_pct_increase': pct_per_pct_inc,
                'pct_per_pct_decrease': pct_per_pct_dec,
                'x_median': x_median,
                'x_min': x_min,
                'x_max': x_max,
                'y_median': y_med,
                'y_min': y_min,
                'y_max': y_max,
                'valid_points': valid_mask.sum()
            })
    
    return pd.DataFrame(sensitivity_data)

def create_tornado_plot(sensitivity_df, target_col, title=None):
    """Create a tornado plot showing parameter sensitivity"""
    if title is None:
        title = f"Sensitivity Analysis: {target_col}"
    
    if sensitivity_df.empty:
        print("No valid sensitivity data to plot")
        return None, None
    
    # Strip any leading '# ' or whitespace from parameter names
    sensitivity_df['variable'] = sensitivity_df['variable'].astype(str).str.lstrip('# ').str.strip()
    
    # Sort by the largest absolute effect (either direction)
    sensitivity_df = sensitivity_df.sort_values(
        by=['pct_per_pct_increase', 'pct_per_pct_decrease'],
        key=lambda x: np.abs(x),
        ascending=True
    )
    
    fig, ax = plt.subplots(figsize=(12, 8))
    y_pos = np.arange(len(sensitivity_df))

    # Plot both bars at the same y position
    bars_increase = ax.barh(
        y_pos, 
        sensitivity_df['pct_per_pct_increase'], 
        height=0.5, 
        color='#3b82f6', 
        alpha=0.7, 
        label='Increase (median→max)'
    )
    bars_decrease = ax.barh(
        y_pos, 
        -sensitivity_df['pct_per_pct_decrease'], 
        height=0.5, 
        color='#ef4444', 
        alpha=0.7, 
        label='Decrease (median→min)'
    )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(sensitivity_df['variable'], fontsize=10)
    ax.set_xlabel(f'Percent change in {target_col} per percent change in parameter', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    ax.axvline(x=0, color='black', linestyle='-', linewidth=0.8)
    ax.grid(True, alpha=0.3, axis='x')
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc='lower right')
    plt.tight_layout()
    return fig, ax

def create_data_summary_plot(df, target_col='pond capital cost (USD_2023)'):
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
    target_col = 'pond capital cost (USD_2023)'
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
    sensitivity_df = oat_sensitivity(df, target_col)
    
    if not sensitivity_df.empty:
        fig, ax = create_tornado_plot(sensitivity_df, target_col, 
                                    title=f"Evaporation Pond Sensitivity Analysis: {target_col}")
        if fig is not None:
            plt.savefig('tornado_plot_pond_capital_cost.png', dpi=300, bbox_inches='tight')
            print("Tornado plot saved as 'tornado_plot_pond_capital_cost.png'")
            plt.show()
        
        # Save sensitivity data with additional info
        sensitivity_df.to_csv('sensitivity_analysis_pond_capital_cost.csv', index=False)
        print("Sensitivity analysis results saved to 'sensitivity_analysis_pond_capital_cost.csv'")
        
        # Print summary of findings
        print(f"\nSensitivity Analysis Summary:")
        print(f"  Parameters analyzed: {len(sensitivity_df)}")
        for _, row in sensitivity_df.iterrows():
            print(f"  {row['variable']}: {row['valid_points']} valid points")
            if not np.isnan(row['pct_per_pct_increase']):
                print(f"    Increase sensitivity: {row['pct_per_pct_increase']:.3f}")
            if not np.isnan(row['pct_per_pct_decrease']):
                print(f"    Decrease sensitivity: {row['pct_per_pct_decrease']:.3f}")
    else:
        print("No valid sensitivity data calculated.")
    
    print("\nTornado plot analysis completed!")

if __name__ == "__main__":
    main()