"""
Weather data processing and analysis utilities for evaporation pond flowsheets

This module contains functions for:
- Preprocessing weather data from different sources
- Plotting evaporation and weather data
- Statistical analysis of weather and evaporation data
- Comparing multiple weather datasets
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta


def preprocess_station34_weather_data(input_file, output_file):
    """Preprocess Station 34 weather data for evaporation pond model.
    
    Args:
        input_file: Path to raw Station 34 weather data
        output_file: Path to save processed data
        
    Returns:
        str: Path to processed output file
    """
    print(f"Preprocessing Station 34 weather data from {input_file}...")
    
    # Read the raw data
    df = pd.read_csv(input_file)
    
    # Rename columns to match expected format
    column_mapping = {
        "DATETIME [YYYY-MM-DD HH:MM]": "datetime",
        "AirTC [air temperature, °C]": "temperature",
        "RH [air humidity, %]": "relative_humidity", 
        "SlrW_1 [solar radiation flux density (up looking), w/m²]": "shortwave_radiation",
        "BP_mbar [barometric pressure, mbar]": "pressure_mbar"
    }
    
    # Select and rename relevant columns
    df_clean = df[list(column_mapping.keys())].copy()
    df_clean.columns = list(column_mapping.values())
    
    # Convert datetime to pandas datetime
    df_clean['datetime'] = pd.to_datetime(df_clean['datetime'])
    
    # Convert pressure from mbar to kPa
    df_clean['pressure'] = df_clean['pressure_mbar'] / 10.0  # mbar to kPa
    df_clean = df_clean.drop('pressure_mbar', axis=1)
    
    # Clean and validate data
    df_clean['temperature'] = np.maximum(df_clean['temperature'], 0.1)
    df_clean['relative_humidity'] = np.clip(df_clean['relative_humidity'], 0, 100)
    df_clean['shortwave_radiation'] = np.maximum(df_clean['shortwave_radiation'], 0)
    df_clean['pressure'] = np.clip(df_clean['pressure'], 50, 110)
    
    # Resample from 10-minute to hourly data
    df_clean.set_index('datetime', inplace=True)
    df_hourly = df_clean.resample('h').mean()
    df_hourly = df_hourly.ffill()
    
    # Ensure we have exactly 8760 hours
    if len(df_hourly) > 8760:
        df_hourly = df_hourly.head(8760)
    elif len(df_hourly) < 8760:
        last_row = df_hourly.iloc[-1]
        while len(df_hourly) < 8760:
            df_hourly = pd.concat([df_hourly, pd.DataFrame([last_row])], ignore_index=True)
    
    # Rename columns to match the expected format for EvaporationPond
    df_hourly.columns = ['Temperature', 'Relative Humidity', 'GHI', 'Pressure']
    
    # Add the expected header format for the EvaporationPond model
    header_lines = [
        "Station 34 Weather Data - Processed for EvaporationPond Model",
        "Data resampled to hourly intervals, units converted as needed",
        "Temperature,Relative Humidity,GHI,Pressure"
    ]
    
    # Write the processed data
    with open(output_file, 'w') as f:
        for line in header_lines:
            f.write(line + '\n')
        df_hourly.to_csv(f, index=False, header=False)
    
    print(f"Preprocessed Station 34 data saved to {output_file}")
    print(f"Data summary:")
    print(f"  - Temperature range: {df_hourly['Temperature'].min():.1f} to {df_hourly['Temperature'].max():.1f} °C")
    print(f"  - RH range: {df_hourly['Relative Humidity'].min():.1f} to {df_hourly['Relative Humidity'].max():.1f} %")
    print(f"  - Solar radiation range: {df_hourly['GHI'].min():.1f} to {df_hourly['GHI'].max():.1f} W/m²")
    print(f"  - Pressure range: {df_hourly['Pressure'].min():.1f} to {df_hourly['Pressure'].max():.1f} kPa")
    
    return output_file


def preprocess_openmeteo_weather_data(input_file, output_file):
    """Preprocess Open-Meteo weather data for evaporation pond model.
    
    Args:
        input_file: Path to raw Open-Meteo weather data
        output_file: Path to save processed data
        
    Returns:
        str: Path to processed output file
    """
    print(f"Preprocessing Open-Meteo weather data from {input_file}...")
    
    # Read the raw data - skip the first 3 lines (location info and blank line)
    df = pd.read_csv(input_file, skiprows=3)
    
    # Extract location info from filename
    filename = os.path.basename(input_file)
    location_info = filename.replace('open-meteo-', '').replace('.csv', '')
    
    # Rename columns to match expected format
    column_mapping = {
        "time": "datetime",
        "temperature_2m (°C)": "temperature",
        "relative_humidity_2m (%)": "relative_humidity", 
        "shortwave_radiation (W/m²)": "shortwave_radiation",
        "surface_pressure (hPa)": "pressure_hpa"
    }
    
    # Select and rename relevant columns
    df_clean = df[list(column_mapping.keys())].copy()
    df_clean.columns = list(column_mapping.values())
    
    # Convert datetime to pandas datetime
    df_clean['datetime'] = pd.to_datetime(df_clean['datetime'])
    
    # Convert pressure from hPa to kPa
    df_clean['pressure'] = df_clean['pressure_hpa'] / 10.0  # hPa to kPa
    df_clean = df_clean.drop('pressure_hpa', axis=1)
    
    # Clean and validate data
    df_clean['temperature'] = np.maximum(df_clean['temperature'], 0.1)
    df_clean['relative_humidity'] = np.clip(df_clean['relative_humidity'], 0, 100)
    df_clean['shortwave_radiation'] = np.maximum(df_clean['shortwave_radiation'], 0)
    df_clean['pressure'] = np.clip(df_clean['pressure'], 50, 110)
    
    # Data is already hourly, just ensure we have exactly 8760 hours
    df_clean.set_index('datetime', inplace=True)
    if len(df_clean) > 8760:
        df_clean = df_clean.head(8760)
    elif len(df_clean) < 8760:
        last_row = df_clean.iloc[-1]
        while len(df_clean) < 8760:
            df_clean = pd.concat([df_clean, pd.DataFrame([last_row])], ignore_index=True)
    
    # Rename columns to match the expected format for EvaporationPond
    df_clean.columns = ['Temperature', 'Relative Humidity', 'GHI', 'Pressure']
    
    # Add the expected header format for the EvaporationPond model
    header_lines = [
        f"Open-Meteo Weather Data - {location_info} - Processed for EvaporationPond Model",
        "Data already in hourly intervals, units converted as needed",
        "Temperature,Relative Humidity,GHI,Pressure"
    ]
    
    # Write the processed data
    with open(output_file, 'w') as f:
        for line in header_lines:
            f.write(line + '\n')
        df_clean.to_csv(f, index=False, header=False)
    
    print(f"Preprocessed Open-Meteo data saved to {output_file}")
    print(f"Data summary:")
    print(f"  - Temperature range: {df_clean['Temperature'].min():.1f} to {df_clean['Temperature'].max():.1f} °C")
    print(f"  - RH range: {df_clean['Relative Humidity'].min():.1f} to {df_clean['Relative Humidity'].max():.1f} %")
    print(f"  - Solar radiation range: {df_clean['GHI'].min():.1f} to {df_clean['GHI'].max():.1f} W/m²")
    print(f"  - Pressure range: {df_clean['Pressure'].min():.1f} to {df_clean['Pressure'].max():.1f} kPa")
    
    return output_file


def preprocess_weather_data(input_file, output_file, data_type="auto"):
    """Generic weather data preprocessing function.
    
    Args:
        input_file: Path to raw weather data file
        output_file: Path to save processed data
        data_type: Type of weather data ("auto", "station34", "openmeteo")
        
    Returns:
        str: Path to processed output file
    """
    if data_type == "auto":
        filename = os.path.basename(input_file).lower()
        if "station" in filename and "34" in filename:
            data_type = "station34"
        elif "open-meteo" in filename:
            data_type = "openmeteo"
        else:
            raise ValueError(f"Could not auto-detect data type from filename: {filename}")
    
    if data_type == "station34":
        return preprocess_station34_weather_data(input_file, output_file)
    elif data_type == "openmeteo":
        return preprocess_openmeteo_weather_data(input_file, output_file)
    else:
        raise ValueError(f"Unknown data type: {data_type}")


def plot_evaporation_and_weather_data(m, weather_name="Unknown", save_plots=True):
    """Plot evaporation rates and weather data throughout the year.
    
    Args:
        m: Pyomo model with evaporation pond
        weather_name: Name of weather dataset
        save_plots: Whether to save plots to files
    """
    print(f"\nGenerating plots for {weather_name} weather data...")
    
    # Get timeseries data from the pond model
    try:
        timeseries_data = m.fs.pond._get_timeseries_results()
    except Exception as e:
        print(f"Error getting timeseries data: {e}")
        return
    
    # Convert day of year to dates for better plotting
    start_date = datetime(2024, 1, 1)  # Assuming 2024 for plotting
    dates = [start_date + timedelta(days=int(day)) for day in timeseries_data['day_of_year']]
    
    # Create figure with subplots
    fig, axes = plt.subplots(3, 2, figsize=(15, 12))
    fig.suptitle(f'Evaporation Pond Performance - {weather_name} Weather Data', fontsize=16)
    
    # Plot 1: Evaporation rate
    axes[0, 0].plot(dates, timeseries_data['evaporation_rate'], 'b-', linewidth=1.5)
    axes[0, 0].set_ylabel('Evaporation Rate (m/s)')
    axes[0, 0].set_title('Daily Evaporation Rate')
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    axes[0, 0].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    
    # Plot 2: Mass flux of water vapor
    axes[0, 1].plot(dates, timeseries_data['mass_flux_water_vapor'], 'g-', linewidth=1.5)
    axes[0, 1].set_ylabel('Mass Flux (kg/m²/s)')
    axes[0, 1].set_title('Daily Water Vapor Mass Flux')
    axes[0, 1].grid(True, alpha=0.3)
    axes[0, 1].xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    axes[0, 1].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    
    # Plot 3: Temperature (air and water)
    axes[1, 0].plot(dates, [t-273.15 for t in timeseries_data['temperature_air']], 'r-', 
                    linewidth=1.5, label='Air Temperature')
    axes[1, 0].plot(dates, [t-273.15 for t in timeseries_data['temperature_water']], 'b-', 
                    linewidth=1.5, label='Water Temperature')
    axes[1, 0].set_ylabel('Temperature (°C)')
    axes[1, 0].set_title('Daily Temperatures')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    axes[1, 0].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    
    # Plot 4: Solar radiation
    axes[1, 1].plot(dates, timeseries_data['shortwave_radiation'], 'orange', linewidth=1.5)
    axes[1, 1].set_ylabel('Solar Radiation (MJ/day/m²)')
    axes[1, 1].set_title('Daily Solar Radiation (GHI)')
    axes[1, 1].grid(True, alpha=0.3)
    axes[1, 1].xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    axes[1, 1].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    
    # Plot 5: Relative humidity
    axes[2, 0].plot(dates, [rh*100 for rh in timeseries_data['relative_humidity']], 'purple', linewidth=1.5)
    axes[2, 0].set_ylabel('Relative Humidity (%)')
    axes[2, 0].set_title('Daily Relative Humidity')
    axes[2, 0].grid(True, alpha=0.3)
    axes[2, 0].xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    axes[2, 0].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    
    # Plot 6: Net radiation
    axes[2, 1].plot(dates, timeseries_data['net_radiation'], 'brown', linewidth=1.5)
    axes[2, 1].set_ylabel('Net Radiation (MJ/day/m²)')
    axes[2, 1].set_title('Daily Net Radiation')
    axes[2, 1].grid(True, alpha=0.3)
    axes[2, 1].xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    axes[2, 1].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    
    # Rotate x-axis labels for better readability
    for ax in axes.flat:
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    
    if save_plots:
        plot_filename = f"evaporation_pond_plots_{weather_name.lower().replace(' ', '_').replace('(', '').replace(')', '')}.png"
        plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
        print(f"Plots saved as: {plot_filename}")
    
    plt.show()


def print_weather_statistics(m, weather_name="Unknown"):
    """Print comprehensive weather and evaporation statistics.
    
    Args:
        m: Pyomo model with evaporation pond
        weather_name: Name of weather dataset
    """
    print(f"\n" + "="*60)
    print(f"WEATHER AND EVAPORATION STATISTICS - {weather_name}")
    print("="*60)
    
    try:
        timeseries_data = m.fs.pond._get_timeseries_results()
    except Exception as e:
        print(f"Error getting timeseries data: {e}")
        return
    
    # Calculate statistics
    stats = {}
    
    # Temperature statistics (convert from K to °C)
    air_temp_c = [t - 273.15 for t in timeseries_data['temperature_air']]
    water_temp_c = [t - 273.15 for t in timeseries_data['temperature_water']]
    
    stats['air_temperature'] = {
        'mean': np.mean(air_temp_c),
        'min': np.min(air_temp_c),
        'max': np.max(air_temp_c),
        'std': np.std(air_temp_c)
    }
    
    stats['water_temperature'] = {
        'mean': np.mean(water_temp_c),
        'min': np.min(water_temp_c),
        'max': np.max(water_temp_c),
        'std': np.std(water_temp_c)
    }
    
    # Relative humidity statistics (convert from fraction to %)
    rh_percent = [rh * 100 for rh in timeseries_data['relative_humidity']]
    stats['relative_humidity'] = {
        'mean': np.mean(rh_percent),
        'min': np.min(rh_percent),
        'max': np.max(rh_percent),
        'std': np.std(rh_percent)
    }
    
    # Solar radiation statistics
    stats['solar_radiation'] = {
        'mean': np.mean(timeseries_data['shortwave_radiation']),
        'min': np.min(timeseries_data['shortwave_radiation']),
        'max': np.max(timeseries_data['shortwave_radiation']),
        'std': np.std(timeseries_data['shortwave_radiation'])
    }
    
    # Evaporation rate statistics
    stats['evaporation_rate'] = {
        'mean': np.mean(timeseries_data['evaporation_rate']),
        'min': np.min(timeseries_data['evaporation_rate']),
        'max': np.max(timeseries_data['evaporation_rate']),
        'std': np.std(timeseries_data['evaporation_rate'])
    }
    
    # Mass flux statistics
    stats['mass_flux_water_vapor'] = {
        'mean': np.mean(timeseries_data['mass_flux_water_vapor']),
        'min': np.min(timeseries_data['mass_flux_water_vapor']),
        'max': np.max(timeseries_data['mass_flux_water_vapor']),
        'std': np.std(timeseries_data['mass_flux_water_vapor'])
    }
    
    # Net radiation statistics
    stats['net_radiation'] = {
        'mean': np.mean(timeseries_data['net_radiation']),
        'min': np.min(timeseries_data['net_radiation']),
        'max': np.max(timeseries_data['net_radiation']),
        'std': np.std(timeseries_data['net_radiation'])
    }
    
    # Print statistics
    print(f"{'Parameter':<25} {'Mean':<12} {'Min':<12} {'Max':<12} {'Std Dev':<12}")
    print("-" * 75)
    
    print(f"{'Air Temperature (°C)':<25} {stats['air_temperature']['mean']:<12.2f} "
          f"{stats['air_temperature']['min']:<12.2f} {stats['air_temperature']['max']:<12.2f} "
          f"{stats['air_temperature']['std']:<12.2f}")
    
    print(f"{'Water Temperature (°C)':<25} {stats['water_temperature']['mean']:<12.2f} "
          f"{stats['water_temperature']['min']:<12.2f} {stats['water_temperature']['max']:<12.2f} "
          f"{stats['water_temperature']['std']:<12.2f}")
    
    print(f"{'Relative Humidity (%)':<25} {stats['relative_humidity']['mean']:<12.2f} "
          f"{stats['relative_humidity']['min']:<12.2f} {stats['relative_humidity']['max']:<12.2f} "
          f"{stats['relative_humidity']['std']:<12.2f}")
    
    print(f"{'Solar Radiation (MJ/day/m²)':<25} {stats['solar_radiation']['mean']:<12.2f} "
          f"{stats['solar_radiation']['min']:<12.2f} {stats['solar_radiation']['max']:<12.2f} "
          f"{stats['solar_radiation']['std']:<12.2f}")
    
    print(f"{'Net Radiation (MJ/day/m²)':<25} {stats['net_radiation']['mean']:<12.2f} "
          f"{stats['net_radiation']['min']:<12.2f} {stats['net_radiation']['max']:<12.2f} "
          f"{stats['net_radiation']['std']:<12.2f}")
    
    print(f"{'Evaporation Rate (m/s)':<25} {stats['evaporation_rate']['mean']:<12.2e} "
          f"{stats['evaporation_rate']['min']:<12.2e} {stats['evaporation_rate']['max']:<12.2e} "
          f"{stats['evaporation_rate']['std']:<12.2e}")
    
    print(f"{'Mass Flux (kg/m²/s)':<25} {stats['mass_flux_water_vapor']['mean']:<12.2e} "
          f"{stats['mass_flux_water_vapor']['min']:<12.2e} {stats['mass_flux_water_vapor']['max']:<12.2e} "
          f"{stats['mass_flux_water_vapor']['std']:<12.2e}")
    
    # Annual totals
    daily_evaporation_rates_m_per_day = [rate * 24 * 3600 for rate in timeseries_data['evaporation_rate']]
    annual_evaporation_mm = np.sum(daily_evaporation_rates_m_per_day) * 1000  # mm/year
    annual_solar_radiation = np.sum(timeseries_data['shortwave_radiation'])  # MJ/m²/year
    
    print("\n" + "-" * 75)
    print(f"{'Annual Evaporation':<25} {annual_evaporation_mm:<12.1f} mm/year")
    print(f"{'Annual Solar Radiation':<25} {annual_solar_radiation:<12.0f} MJ/m²/year")
    
    print("="*60)


def compare_weather_datasets(dataset_results):
    """Compare multiple weather datasets and create a summary table"""
    print("\n" + "="*80)
    print("WEATHER DATASET COMPARISON SUMMARY")
    print("="*80)
    
    # Create comparison table
    print(f"{'Dataset':<20} {'Avg Temp':<10} {'Avg RH':<10} {'Avg Solar':<12} {'Annual Evap':<12}")
    print(f"{'':<20} {'(°C)':<10} {'(%)':<10} {'(MJ/day/m²)':<12} {'(mm/year)':<12}")
    print("-" * 80)
    
    for weather_name, timeseries_data, stats in dataset_results:
        daily_evaporation_rates_m_per_day = [rate * 24 * 3600 for rate in timeseries_data['evaporation_rate']]
        annual_evaporation_mm = np.sum(daily_evaporation_rates_m_per_day) * 1000  # mm/year
        
        avg_temp = np.mean([t - 273.15 for t in timeseries_data['temperature_air']])
        avg_rh = np.mean([rh * 100 for rh in timeseries_data['relative_humidity']])
        avg_solar = np.mean(timeseries_data['shortwave_radiation'])
        
        print(f"{weather_name:<20} {avg_temp:<10.1f} {avg_rh:<10.1f} {avg_solar:<12.1f} "
              f"{annual_evaporation_mm:<12.0f} mm")
    
    print("-" * 80)
    
    # Create comparison plots if multiple datasets
    if len(dataset_results) > 1:
        create_comparison_plots(dataset_results)


def create_comparison_plots(dataset_results):
    """Create comparison plots for multiple weather datasets (weekly averages).
    
    Args:
        dataset_results: List of tuples containing (weather_name, timeseries_data, stats)
    """
    print(f"\nCreating comparison plots for {len(dataset_results)} datasets...")
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Weather Dataset Comparison (Weekly Averages)', fontsize=16)
    
    # Weekly x-axis: 52 weeks, week start dates
    start_date = datetime(2024, 1, 1)
    week_starts = [start_date + timedelta(days=7 * i) for i in range(52)]
    
    colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown']
    
    # Helper to downsample to weekly means
    def weekly_avg(arr):
        """Calculate weekly averages from daily data.
        
        Args:
            arr: Array of daily values
            
        Returns:
            array: Weekly averaged values
        """
        arr = np.array(arr)
        n = 52
        # Truncate or pad to 364 days (52*7)
        if len(arr) > 364:
            arr = arr[:364]
        elif len(arr) < 364:
            arr = np.pad(arr, (0, 364 - len(arr)), mode='edge')
        arr = arr.reshape((52, 7))
        return arr.mean(axis=1)
    
    # Plot 1: Temperature comparison
    for i, (weather_name, timeseries_data, stats) in enumerate(dataset_results):
        air_temp_c = [t - 273.15 for t in timeseries_data['temperature_air']]
        weekly_temp = weekly_avg(air_temp_c)
        axes[0, 0].plot(week_starts, weekly_temp, color=colors[i % len(colors)], 
                       linewidth=1.5, label=weather_name)
    axes[0, 0].set_ylabel('Air Temperature (°C)')
    axes[0, 0].set_title('Weekly Air Temperature Comparison')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    axes[0, 0].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    
    # Plot 2: Evaporation rate comparison
    for i, (weather_name, timeseries_data, stats) in enumerate(dataset_results):
        weekly_evap = weekly_avg(timeseries_data['evaporation_rate'])
        axes[0, 1].plot(week_starts, weekly_evap, 
                       color=colors[i % len(colors)], linewidth=1.5, label=weather_name)
    axes[0, 1].set_ylabel('Evaporation Rate (m/s)')
    axes[0, 1].set_title('Weekly Evaporation Rate Comparison')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    axes[0, 1].xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    axes[0, 1].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    
    # Plot 3: Solar radiation comparison
    for i, (weather_name, timeseries_data, stats) in enumerate(dataset_results):
        weekly_solar = weekly_avg(timeseries_data['shortwave_radiation'])
        axes[1, 0].plot(week_starts, weekly_solar, 
                       color=colors[i % len(colors)], linewidth=1.5, label=weather_name)
    axes[1, 0].set_ylabel('Solar Radiation (MJ/day/m²)')
    axes[1, 0].set_title('Weekly Solar Radiation Comparison')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    axes[1, 0].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    
    # Plot 4: Relative humidity comparison
    for i, (weather_name, timeseries_data, stats) in enumerate(dataset_results):
        rh_percent = [rh * 100 for rh in timeseries_data['relative_humidity']]
        weekly_rh = weekly_avg(rh_percent)
        axes[1, 1].plot(week_starts, weekly_rh, color=colors[i % len(colors)], 
                       linewidth=1.5, label=weather_name)
    axes[1, 1].set_ylabel('Relative Humidity (%)')
    axes[1, 1].set_title('Weekly Relative Humidity Comparison')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    axes[1, 1].xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    axes[1, 1].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    
    # Rotate x-axis labels
    for ax in axes.flat:
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    
    # Save comparison plot
    comparison_filename = "weather_datasets_comparison.png"
    plt.savefig(comparison_filename, dpi=300, bbox_inches='tight')
    print(f"Comparison plots saved as: {comparison_filename}")
    
    plt.show()


def run_all_datasets_and_compare(this_dir):
    """Run all available weather datasets and create comparison plots and statistics"""
    print("\n" + "="*60)
    print("RUNNING ALL WEATHER DATASETS FOR COMPARISON")
    print("="*60)
    
    # Define all datasets to process (only Station 34 and Open-Meteo for comparison)
    datasets = [
        {
            "name": "Station 34",
            "raw_file": os.path.join(this_dir, "station[34]_2024-01-01_2024-12-31.csv"),
            "processed_file": os.path.join(this_dir, "station34_processed_weather.csv"),
            "data_type": "station34",
            "needs_preprocessing": True
        },
        {
            "name": "Open-Meteo (Chile)",
            "raw_file": os.path.join(this_dir, "open-meteo-23.66S68.45W2301m.csv"),
            "processed_file": os.path.join(this_dir, "openmeteo_processed_weather.csv"),
            "data_type": "openmeteo",
            "needs_preprocessing": True
        },
        {
            "name": "Test Data",
            "processed_file": os.path.join(this_dir, "evaporation_pond_test_data.csv"),
            "needs_preprocessing": False
        }
    ]
    
    dataset_results = []
    
    for i, dataset in enumerate(datasets):
        print(f"\nProcessing dataset {i+1}/{len(datasets)}: {dataset['name']}")
        print("-" * 40)
        
        # Check if files exist
        if dataset.get('needs_preprocessing', False):
            if not os.path.exists(dataset['raw_file']):
                print(f"Warning: Raw file not found: {dataset['raw_file']}")
                print("Skipping this dataset...")
                continue
                
            if not os.path.exists(dataset['processed_file']):
                print(f"Preprocessing {dataset['name']} data...")
                try:
                    preprocess_weather_data(dataset['raw_file'], dataset['processed_file'], dataset['data_type'])
                except Exception as e:
                    print(f"Error preprocessing {dataset['name']}: {e}")
                    print("Skipping this dataset...")
                    continue
        else:
            if not os.path.exists(dataset['processed_file']):
                print(f"Warning: Processed file not found: {dataset['processed_file']}")
                print("Skipping this dataset...")
                continue
        
        # Build and solve model
        try:
            # Import here to avoid circular imports
            try:
                from .claras_evap_fs import build, set_operating_conditions, initialize_system, solve
            except ImportError:
                from claras_evap_fs import build, set_operating_conditions, initialize_system, solve
            from watertap.core.util.initialization import assert_degrees_of_freedom
            from pyomo.environ import assert_optimal_termination
            
            m = build(dataset['processed_file'])
            set_operating_conditions(m)
            m.fs.pond.number_evaporation_ponds.fix(300)
            assert_degrees_of_freedom(m, 0)
            
            initialize_system(m)
            results = solve(m)
            assert_optimal_termination(results)
            
            # Get timeseries data and statistics
            timeseries_data = m.fs.pond._get_timeseries_results()
            
            # Calculate basic statistics for comparison
            air_temp_c = [t - 273.15 for t in timeseries_data['temperature_air']]
            rh_percent = [rh * 100 for rh in timeseries_data['relative_humidity']]
            
            stats = {
                'air_temperature': {
                    'mean': np.mean(air_temp_c),
                    'min': np.min(air_temp_c),
                    'max': np.max(air_temp_c),
                    'std': np.std(air_temp_c)
                },
                'relative_humidity': {
                    'mean': np.mean(rh_percent),
                    'min': np.min(rh_percent),
                    'max': np.max(rh_percent),
                    'std': np.std(rh_percent)
                },
                'solar_radiation': {
                    'mean': np.mean(timeseries_data['shortwave_radiation']),
                    'min': np.min(timeseries_data['shortwave_radiation']),
                    'max': np.max(timeseries_data['shortwave_radiation']),
                    'std': np.std(timeseries_data['shortwave_radiation'])
                },
                'evaporation_rate': {
                    'mean': np.mean(timeseries_data['evaporation_rate']),
                    'min': np.min(timeseries_data['evaporation_rate']),
                    'max': np.max(timeseries_data['evaporation_rate']),
                    'std': np.std(timeseries_data['evaporation_rate'])
                }
            }
            
            dataset_results.append((dataset['name'], timeseries_data, stats))
            
            print(f"✓ Successfully processed {dataset['name']}")
            
        except Exception as e:
            print(f"✗ Error processing {dataset['name']}: {e}")
            print("Skipping this dataset...")
            continue
    
    # Create comparison if we have at least 2 datasets
    if len(dataset_results) >= 2:
        print(f"\nSuccessfully processed {len(dataset_results)} datasets.")
        compare_weather_datasets(dataset_results)
    else:
        print(f"\nOnly {len(dataset_results)} dataset(s) processed successfully.")
        print("Need at least 2 datasets for comparison.")


def test_plotting_functionality():
    """Simple test function to demonstrate the new plotting and statistics functionality"""
    print("Testing plotting functionality...")
    
    # Create sample data for testing
    sample_data = {
        'day_of_year': list(range(365)),
        'evaporation_rate': [1e-6 + 5e-7 * np.sin(2 * np.pi * i / 365) for i in range(365)],
        'mass_flux_water_vapor': [1e-5 + 5e-6 * np.sin(2 * np.pi * i / 365) for i in range(365)],
        'temperature_air': [293.15 + 10 * np.sin(2 * np.pi * i / 365) for i in range(365)],
        'temperature_water': [298.15 + 8 * np.sin(2 * np.pi * i / 365) for i in range(365)],
        'shortwave_radiation': [15 + 10 * np.sin(2 * np.pi * i / 365) for i in range(365)],
        'relative_humidity': [0.6 + 0.2 * np.sin(2 * np.pi * i / 365) for i in range(365)],
        'net_radiation': [8 + 5 * np.sin(2 * np.pi * i / 365) for i in range(365)]
    }
    
    # Create a mock model object for testing
    class MockModel:
        def __init__(self, data):
            self.data = data
        
        def _get_timeseries_results(self):
            return self.data
    
    class MockPond:
        def __init__(self, data):
            self.data = data
        
        def _get_timeseries_results(self):
            return self.data
    
    class MockFS:
        def __init__(self, data):
            self.pond = MockPond(data)
    
    mock_m = MockModel(sample_data)
    mock_m.fs = MockFS(sample_data)
    
    # Test the plotting function
    try:
        plot_evaporation_and_weather_data(mock_m, "Test Data", save_plots=False)
        print("✓ Plotting functionality test passed!")
    except Exception as e:
        print(f"✗ Plotting functionality test failed: {e}")
    
    # Test the statistics function
    try:
        print_weather_statistics(mock_m, "Test Data")
        print("✓ Statistics functionality test passed!")
    except Exception as e:
        print(f"✗ Statistics functionality test failed: {e}")


if __name__ == "__main__":
    # Test the weather utilities
    test_plotting_functionality() 