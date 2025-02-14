import argparse
from pathlib import Path
import pandas as pd
import shutil
import logging
import datetime as dt
import os
import sys
from utility_functions import read_toml_file
import subprocess
import time

"""
This file takes a configuration file that contains varied weather data and gridded input drivers and 
creates a set of swb control files along with a working directory, logfile and output file directories. Python's Popen 
class is used to fire off a swb2 run in each of the directories it creates.

By design, each time the script is run, the old working directory is completely removed. I want to ensure that 
whatever we are looking at includes only files generated from the latest swb2 model run.
"""
# this is taken from: 
# https://stackoverflow.com/questions/431684/equivalent-of-shell-cd-command-to-change-the-working-directory/13197763#13197763
class cd:
    """Context manager for changing the current working directory"""
    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)

def read_template_file(swb_control_file_template_name):
  with open(swb_control_file_template_name) as f:
    contents = f.read()
  return contents

def write_control_file(control_file_text, control_filename):
  with open(control_filename, "w") as f:
    f.write(control_file_text)

def destroy_model_work_dir(work_dir):
  shutil.rmtree(work_dir, ignore_errors=True)

def create_model_work_dir(work_dir,
                          sub_dir,
                          output_dir,
                          logfile_dir):
  work_path = Path(work_dir) / sub_dir
  logfile_path = work_path / logfile_dir
  output_path = work_path / output_dir 
  work_path.mkdir(parents=True, exist_ok=True)
  logfile_path.mkdir(parents=True, exist_ok=True)
  output_path.mkdir(parents=True, exist_ok=True)

def create_control_file_text(template_file_text,
                             precip_file,
                             tmin_file,
                             tmax_file,
                             lu_lookup_table_name,
                             irr_lookup_table_name,
                             available_water_capacity_grid,
                             landuse_grid,
                             hydrologic_soil_group_grid,
                             irrigation_mask_grid,
                             start_date,
                             end_date,
                            ):
  """Take the swb2 template file and substitute in values that are taken
  from the TOML run control file. 

  Probably best to supply the filenames as fully qualified pathnames to
  avoid 'file-not-found' errors during model execution.

  Args:
      template_file_text (str): swb2 template file
      precip_file (str): name of daily precipitation file
      tmin_file (str): name of daily tmin file
      tmax_file (str): name of daily tmax file
      weather_data_lookup_table_name (str): name of table used to supply weather in tabular form, if any
      reference_et0_file (str): name of daily reference ET0 file
      lu_lookup_table_name (str): name of landuse lookup table
      irr_lookup_table_name (str): name of irrigation lookup table
      available_water_capacity_grid (str): name of available water capacity grid
      landuse_grid (str): name of land use grid
      hydrologic_soil_group_grid (str): name of hydrologic soil group grid
      irrigation_mask_grid (str): name of the irrigation mask grid
      start_date (str): start date for simulation (mm/dd/yyyy)
      end_date (str): end date for simulation (mm/dd/yyyy)

  Returns:
      str: text for the swb2 control file, with run-specific substitutions made
  """

  output = template_file_text.format(precipitation_filename=precip_file,
                                     tmin_filename=tmin_file,
                                     tmax_filename=tmax_file,
                                     landuse_lookup_table_name=lu_lookup_table_name,
                                     irrigation_lookup_table_name=irr_lookup_table_name,
                                     available_water_capacity_grid=available_water_capacity_grid,
                                     landuse_grid=landuse_grid,
                                     hydrologic_soil_group_grid=hydrologic_soil_group_grid,
                                     irrigation_mask_grid=irrigation_mask_grid,
                                     start_date=start_date,
                                     end_date=end_date)
  return output

if __name__ == '__main__':

  parser = argparse.ArgumentParser(description='Fire off one SWB2 model run for each set of daily weather grid input')
  parser.add_argument("run_control_file",
                      help='run control file, in TOML format')
  parser.add_argument("simulation_details_file",
                      help='simulation details file, in tab-spaced variable (*.tsv) format')
  parser.add_argument('--dry_run',
                      help='create output files and structure, but do *not* run simulations',
                      action='store_true')

  # expected dir structure should resemble this (Hovenweep example):
# ├───git
# │   └───mn_swb_cmip6_run_proc
# │       ├───python
# │       ├───config_files
# │       └───data_summaries
# ├───swb_input
# │   ├───gridded_data
# │   ├───tabular_data
# │   └───templates
# ├───working_disposable_directory
# │   └───gcm_runs
# │       └───gcm_name
# │           └───time_period
# │               └───SSP
# │                   ├───logfile
# │                   └───output

# NOTE that this script will completely NUKE the 'swb_runs' dir and replace it with entirely new content
# each time the script is run 

  # process command-line arguments

  try:
      args = parser.parse_args()
  except:
      parser.print_help()
      sys.exit(0)

  run_control_filename = args.run_control_file
  simulation_details_filename = args.simulation_details_file
  dry_run = args.dry_run
  control_dict = read_toml_file(filename=run_control_filename)
  simulations_df = pd.read_csv(simulation_details_filename, delimiter="\t",)

  simulations_df.start_date=pd.to_datetime(simulations_df.start_date)
  simulations_df.end_date=pd.to_datetime(simulations_df.end_date)
  simulations_df['start_year'] = simulations_df.start_date.dt.year
  simulations_df['end_year'] = simulations_df.end_date.dt.year
  simulations_df['start_day'] = simulations_df.start_date.dt.day
  simulations_df['end_day'] = simulations_df.end_date.dt.day
  simulations_df['start_month'] = simulations_df.start_date.dt.month
  simulations_df['end_month'] = simulations_df.end_date.dt.month

  # pull specific SWB2 run data from the TOML file
  top_level_dir = Path(control_dict['working_directories']['top_level_dir'])
  base_dir = Path.cwd().parent   # path to git repo that contains this script
  gcm_runs_dir = top_level_dir / control_dict['working_directories']['gcm_runs_dir']
  logfiles_dir = top_level_dir / control_dict['working_directories']['logfiles_dir']
  work_dir = top_level_dir / control_dict['working_directories']['swb_work_dir']

  logger = logging.getLogger(__name__)
  timestamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")
  logging.basicConfig(filename=Path(logfiles_dir)/f"modelrunner__{timestamp}.log", level=logging.INFO, filemode='w')
  logger.info('Begin executing Python script')

  logger.info('created simulations dataframe')

  # pull specific SWB2 run data from the TOML file
  base_dir = Path.cwd().parent   # path to git repo that contains this script
  gcm_runs_dir = top_level_dir / control_dict['working_directories']['gcm_runs_dir']
  work_dir = top_level_dir / control_dict['working_directories']['swb_work_dir']

  weather_data_dir = control_dict['data_directories']['weather_data_dir']
  tabular_data_dir = base_dir / control_dict['data_directories']['swb_tabular_data_dir']
  gridded_data_dir = base_dir / control_dict['data_directories']['swb_gridded_data_dir']
  templates_dir = base_dir / control_dict['data_directories']['swb_templates_dir']
  cleanup_work_dir = control_dict['auto_cleanup']['cleanup_work_dir']

  lu_lookup_table_name = control_dict['input_tables']['lu_lookup_table_name']
  irr_lookup_table_name = control_dict['input_tables']['irr_lookup_table_name']
  # available_water_capacity_grid = control_dict['input_grids']['available_water_capacity_grid']
  # landuse_grid = control_dict['input_grids']['landuse_grid']
  # hydrologic_soil_group_grid = control_dict['input_grids']['hydrologic_soil_group_grid']
  # irrigation_mask_grid = control_dict['input_grids']['irrigation_mask_grid']

  # clean up pathnames...
  lu_lookup_table_path = tabular_data_dir / lu_lookup_table_name
  irr_lookup_table_path= tabular_data_dir / irr_lookup_table_name
  # available_water_capacity_grid_path = gridded_data_dir / available_water_capacity_grid
  # landuse_grid_path = gridded_data_dir / landuse_grid
  # hydrologic_soil_group_grid_path = gridded_data_dir / hydrologic_soil_group_grid
  # irrigation_mask_grid_path = gridded_data_dir / irrigation_mask_grid

# DANGER -- I have this script set up to NUKE the working directory; this is by design. I don't
#           want old crufty stuff mixed in with the new model runs.
  if cleanup_work_dir:
    logger.info(f"destroyed directory: {work_dir}")
    destroy_model_work_dir(work_dir)

process_dict = {}

# iterate over the entries in the run table; fire off a separate instance of swb2 for each

simulations_df['simulation_name']=''

for index, row in simulations_df.iterrows():

  simulations_df.loc[index, 'simulation_name'] = f"{row.scenario_name}__{row.weather_data_basename}__{row.start_year}-{row.end_year}"
  create_model_work_dir(work_dir=work_dir,
                        sub_dir=simulations_df.loc[index, 'simulation_name'],
                        logfile_dir='logfile',
                        output_dir='output')  

  logger.info(f"creating dir and files for {simulations_df.loc[index, 'simulation_name']}")

  # read in the contents of the appropriate SWB2 control file TEMPLATE
  swb_control_file_template_text = read_template_file(templates_dir / Path(row.template_file))

  start_date_txt = f"{row.start_month:02}/{row.start_day:02}/{row.start_year}"
  end_date_txt = f"{row.end_month:02}/{row.end_day:02}/{row.end_year}"

  swb_control_file_text = create_control_file_text(
                             template_file_text = swb_control_file_template_text,
                             precip_file = Path(weather_data_dir) / row.weather_data_dir / row.precip_file,
                             tmin_file = Path(weather_data_dir) / row.weather_data_dir / row.tmin_file,
                             tmax_file = Path(weather_data_dir) / row.weather_data_dir / row.tmax_file,
                             lu_lookup_table_name = lu_lookup_table_path,
                             irr_lookup_table_name = irr_lookup_table_path,
                             available_water_capacity_grid = gridded_data_dir / Path(row.available_water_capacity_grid),
                             landuse_grid = gridded_data_dir / Path(row.landuse_grid),
                             hydrologic_soil_group_grid = gridded_data_dir / Path(row.hydrologic_soil_group_grid),
                             irrigation_mask_grid = gridded_data_dir / Path(row.irrigation_mask_grid),
                             start_date=start_date_txt,
                             end_date=end_date_txt,
                           )

  swb_run_dir = str(Path(work_dir) / simulations_df.loc[index, 'simulation_name'])
  control_file_name = f"{simulations_df.loc[index, 'simulation_name']}__control_file.ctl" 
  control_file_path = Path(swb_run_dir) / control_file_name

  write_control_file(swb_control_file_text, 
                     control_file_path,
                    )
  
  output_prefix = f"--output_prefix={simulations_df.loc[index, 'simulation_name']}__"
  #swb_binary =  row.swb_executable
  swb_binary = 'swb2'
  swb_arg_text = [swb_binary, "--output_dir=output", output_prefix, "--logfile_dir=logfile",
                  output_prefix, control_file_name]

#  if not dry_run:
  with cd(swb_run_dir):
    p = subprocess.Popen(swb_arg_text, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    logger.info(f"running swb for {simulations_df.loc[index, 'simulation_name']}")
    logger.info(f"   location of swb run: {swb_run_dir}")
    logger.info(f"   swb command line: '{swb_arg_text}'")
    process_dict[index] = p
    time.sleep(3)

logger.info(f"waiting for simulations to finish...")
exit_codes = [p.wait() for p in process_dict.values()]

logger.info(f"swb finished? exit codes: {exit_codes}")

logger.info("End of Python script.")



