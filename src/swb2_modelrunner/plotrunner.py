import site
site.addsitedir('.')  # Always appends to end
import argparse
import matplotlib.pyplot as plt
import plot_time_series_by_variable as pv
import plot_annual_mean_variables_by_zone as pz
from pathlib import Path
import pandas as pd
import numpy as np
import logging
import pathlib as pl
import datetime as dt
import os
from datetime import datetime
from collections import defaultdict

from utility_functions import read_toml_file

parser = argparse.ArgumentParser(description='Munge through zonal stats output and create plots')
parser.add_argument("run_control_file",
                    help='run control file, in TOML format')
parser.add_argument("output_control_file",
                    help="output control file, in TOML format")

try:
    args = parser.parse_args()
except:
    parser.print_help()
    sys.exit(0)

run_control_filename = args.run_control_file
output_control_filename = args.output_control_file

run_control_dict = read_toml_file(filename=run_control_filename)
output_control_dict = read_toml_file(filename=output_control_filename)

weather_driver_dict = output_control_dict['variables']['weather_driver_dict']
variable_dict = output_control_dict['variables']['variable_dict']

# simulations_df = pd.read_csv(simulation_details_filename, delimiter="\t",)

# simulations_df.start_date=pd.to_datetime(simulations_df.start_date)
# simulations_df.end_date=pd.to_datetime(simulations_df.end_date)
# simulations_df['start_year'] = simulations_df.start_date.dt.year
# simulations_df['end_year'] = simulations_df.end_date.dt.year
# simulations_df['start_day'] = simulations_df.start_date.dt.day
# simulations_df['end_day'] = simulations_df.end_date.dt.day
# simulations_df['start_month'] = simulations_df.start_date.dt.month
# simulations_df['end_month'] = simulations_df.end_date.dt.month

# pull specific SWB2 run data from the TOML file
top_level_dir = Path(run_control_dict['working_directories']['top_level_dir'])
base_dir = Path.cwd().parent   # path to git repo that contains this script
gcm_runs_dir = top_level_dir / run_control_dict['working_directories']['gcm_runs_dir']
logfiles_dir = top_level_dir / run_control_dict['working_directories']['logfiles_dir']
data_summary_dir = top_level_dir / run_control_dict['working_directories']['data_summary_dir']
work_dir = top_level_dir / run_control_dict['working_directories']['swb_work_dir']

# obtain list of models, scenarios, periods, for which we expect to see results
weather_data_names = output_control_dict['scenarios_and_periods']['weather_data_names']
scenario_names = output_control_dict['scenarios_and_periods']['scenario_names']
time_periods = output_control_dict['scenarios_and_periods']['time_periods']

# obtain list of varibles for which we want to extract summaries
grid_vars = output_control_dict['variables']['grid_vars']
data_summary_dir = top_level_dir / run_control_dict['working_directories']['data_summary_dir']

logger = logging.getLogger(__name__)
timestamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")
logging.basicConfig(filename=Path(logfiles_dir)/f"outputrunner__{timestamp}.log", level=logging.INFO, filemode='w')
logger.info('Begin executing Python script')

logger.info('created simulations dataframe')

weather_data_dir = run_control_dict['data_directories']['weather_data_dir']
tabular_data_dir = base_dir / run_control_dict['data_directories']['swb_tabular_data_dir']
gridded_data_dir = base_dir / run_control_dict['data_directories']['swb_gridded_data_dir']

#lu_lookup_table_name = run_control_dict['input_tables']['lu_lookup_table_name']
#irr_lookup_table_name = run_control_dict['input_tables']['irr_lookup_table_name']

plot_dir = top_level_dir / run_control_dict['working_directories']['plot_dir']
logger.info(f"creating directory to hold plots at {plot_dir}.")
plot_dir.mkdir(parents=True, exist_ok=True)

annual_sum_types = output_control_dict['output_data_types']['annual_sum_types']
mean_monthly_types = output_control_dict['output_data_types']['mean_monthly_types']
mean_annual_types = output_control_dict['output_data_types']['mean_annual_types']

mean_annual_sum_zonal_stats_path = data_summary_dir / 'mean_annual_sum_zonal_stats.csv'
mean_annual_sum_zonal_stats_df = pd.read_csv(mean_annual_sum_zonal_stats_path, header=0, sep=',',
                                            dtype=annual_sum_types )
mean_annual_sum_zonal_stats_df.reset_index(drop=True, inplace=True)

mean_monthly_sum_zonal_stats_path = data_summary_dir / 'mean_monthly_sum_zonal_stats.csv'
mean_monthly_sum_zonal_stats_df = pd.read_csv(mean_monthly_sum_zonal_stats_path, header=0, sep=',',
                                              dtype=mean_monthly_types)
mean_monthly_sum_zonal_stats_df.reset_index(drop=True, inplace=True)

annual_sum_zonal_stats_path = data_summary_dir / 'annual_sum_zonal_stats.csv'
annual_sum_zonal_stats_df = pd.read_csv(annual_sum_zonal_stats_path, header=0, sep=',',
                                             dtype=mean_annual_types )
annual_sum_zonal_stats_df.reset_index(drop=True, inplace=True)

zones = annual_sum_zonal_stats_df['zone'].unique()

for zone in zones:
  logging.info(f"==> creating plots for zone: {zone}")
  zone_df  = annual_sum_zonal_stats_df.query(f"zone=='{zone}'")
  zone_monthly_df = mean_monthly_sum_zonal_stats_df.query(f"zone=='{zone}'")
  zone_mean_annual_df = mean_annual_sum_zonal_stats_df.query(f"zone=='{zone}'")

  annual_sum_plot_filename = plot_dir / f"annual_sum_plot_{zone}.pdf"
  pv.make_time_series_plot_by_variable(zonal_stats_df=zone_df,
                                       variable_dict=variable_dict,
                                       weather_driver_dict=weather_driver_dict,
                                       output_filename=annual_sum_plot_filename)

  mean_monthly_plot_filename = plot_dir / f"mean_monthly_plot_{zone}.pdf"
  pv.make_time_series_plot_by_variable(zonal_stats_df=zone_monthly_df,
                                       variable_dict=variable_dict,
                                       weather_driver_dict=weather_driver_dict,
                                       output_filename=mean_monthly_plot_filename,
                                       time_variable='month')
  
pz.make_annual_plot_of_variables_by_zone(zonal_stats_df=mean_annual_sum_zonal_stats_df, 
                                         variable_dict=variable_dict,
                                         weather_driver_dict=weather_driver_dict,
                                         output_filename='mean_annual_variables_by_zone.pdf')
