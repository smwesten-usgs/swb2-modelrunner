import site
site.addsitedir('.')  # Always appends to end

import argparse
import calendar
from pathlib import Path
import pandas as pd
from utility_functions import read_toml_file
import matplotlib.pyplot as plt
import os
import subprocess
import logging
import rioxarray as rio
import xrspatial as xrs
import xarray as xr
import make_summary_dataset as sd
import export_functions as ef
import datetime as dt
from dask.distributed import Client, LocalCluster
from calendar import monthrange

def pause():
    programPause = input("Press the <ENTER> key to continue...")

def extract_run_information_from_filename(nc_filename):
    """
    This function will fail unless naming conventions are strictly followed. The swb output files are assumed
    to be named as follows:

    scenario_name__weather_data_name__short_time_period__swb_variable_name__time_period__spatial_coverage.nc [note double underscores]

    For example:
      ssp245__bcc_csm2-mr__2040-2059__runoff__2040-01-01_to_2059-12-31__688_by_620.nc

    The idea is to make the output of the run as self-describing as possible, so that we don't have to create lists of 
    files, lists of weather data drivers, etc. in order to have the script run on all output.
    """  
    (scenario_name, 
    weather_data_name, 
    short_time_period,
    swb_variable_name, 
    time_period, 
    spatial_coverage) = nc_filename.split('__')

    spatial_coverage = spatial_coverage.split('.')[0]
    return scenario_name, weather_data_name, short_time_period, swb_variable_name, time_period, spatial_coverage

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Fire off one SWB2 model run for each set of daily weather grid input')
    parser.add_argument("run_control_file",
                        help="run control file, in TOML format")
    parser.add_argument("output_control_file",
                        help="output control file, in TOML format")
    parser.add_argument("--make_tifs",
                        help="create tif output files for each timestep of each output netCDF file",
                        action="store_true")

    try:
        args = parser.parse_args()
    except:
        parser.print_help()
        sys.exit(0)

    run_control_filename = args.run_control_file
    output_control_filename = args.output_control_file
    make_tifs = args.make_tifs
    run_control_dict = read_toml_file(filename=run_control_filename)
    output_control_dict = read_toml_file(filename=output_control_filename)

    print(f"creating Dask cluster...")

    ## ALERT !!!! Do not use more than one thread per worker!!
    ##            Using more than one thread per worker seems to lead to
    ##            spurious HDF5 and netCDF read errors
    cluster = LocalCluster(n_workers=8, threads_per_worker=1)    # Launches a scheduler and workers locally
    client = Client(cluster) 

    # pull specific SWB2 run data from the TOML file
    top_level_dir = Path(run_control_dict['working_directories']['top_level_dir'])
    base_dir = Path.cwd().parent   # path to git repo that contains this script
    gcm_runs_dir = top_level_dir / run_control_dict['working_directories']['gcm_runs_dir']
    logfiles_dir = top_level_dir / run_control_dict['working_directories']['logfiles_dir']
    data_summary_dir = top_level_dir / run_control_dict['working_directories']['data_summary_dir']
    work_dir = top_level_dir / run_control_dict['working_directories']['swb_work_dir']

    logger = logging.getLogger(__name__)
    timestamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    logging.basicConfig(filename=Path(logfiles_dir)/f"outputrunner__{timestamp}.log", level=logging.INFO, filemode='w')
    logger.info('Begin executing Python script')

    logger.info('created simulations dataframe')

    weather_data_dir = run_control_dict['data_directories']['weather_data_dir']
    tabular_data_dir = base_dir / run_control_dict['data_directories']['swb_tabular_data_dir']
    gridded_data_dir = base_dir / run_control_dict['data_directories']['swb_gridded_data_dir']

    lu_lookup_table_name = run_control_dict['input_tables']['lu_lookup_table_name']
    irr_lookup_table_name = run_control_dict['input_tables']['irr_lookup_table_name']
    #swb_output_dir = swb_work_dir / run_control_dict['working_directories']['swb_output_dir']
    data_summary_dir = top_level_dir / run_control_dict['working_directories']['data_summary_dir']
    logger.info(f"creating directory to hold output statistics at {data_summary_dir}.")
    data_summary_dir.mkdir(parents=True, exist_ok=True)

    grid_stats_dir = top_level_dir / run_control_dict['working_directories']['grid_stats_dir']
    logger.info(f"creating directory to hold output grids at {grid_stats_dir}.")
    grid_stats_dir.mkdir(parents=True, exist_ok=True)

    tif_image_dir = top_level_dir / run_control_dict['working_directories']['tif_image_dir']
    logger.info(f"creating directory to hold output tif images at {tif_image_dir}.")
    tif_image_dir.mkdir(parents=True, exist_ok=True)

    lu_lookup_table_path = tabular_data_dir / lu_lookup_table_name
    irr_lookup_table_path= tabular_data_dir / irr_lookup_table_name
    
    # obtain list of models, scenarios, periods, for which we expect to see results
    weather_data_names = output_control_dict['scenarios_and_periods']['weather_data_names']
    scenario_names = output_control_dict['scenarios_and_periods']['scenario_names']
    time_periods = output_control_dict['scenarios_and_periods']['time_periods']
    summary_types = output_control_dict['scenarios_and_periods']['summary_types']

    # obtain list of varibles for which we want to extract summaries
    grid_vars = output_control_dict['variables']['grid_vars']

    # get information about geographic projection used in project grid
    project_crs = output_control_dict['geospatial']['project_crs']

    # define output csv paths and filenames
    monthly_sum_zonal_stats_csv_output_path = data_summary_dir / 'monthly_sum_zonal_stats.csv'
    mean_monthly_sum_zonal_stats_csv_output_path = data_summary_dir / 'mean_monthly_sum_zonal_stats.csv'
    annual_sum_zonal_stats_csv_output_path = data_summary_dir / 'annual_sum_zonal_stats.csv'
    mean_annual_sum_zonal_stats_csv_output_path = data_summary_dir / 'mean_annual_sum_zonal_stats.csv'

    # define a zone file
    zone_filename = output_control_dict['input_grids']['zone_mask_file']
    zone_path =str(Path(gridded_data_dir).resolve() / zone_filename)

    # create a file list of all swb netCDF output files beneath the current directory
    nc_filelist = list(work_dir.rglob("*.nc"))

#    for summary_types in ['monthly','mean_monthly','annual','mean_annual']:
    for summary_basetype in summary_types:

        logger.info(f"Processing {summary_basetype} statistics")

            # list to hold Dask future objects
        futures = []
        output_filenames = []

            # iterate over list of netCDF output files
        for file in nc_filelist:
            ncfile_name = file.name

            ( scenario_name, 
              weather_data_name, 
              short_time_period,
              swb_variable_name, 
              time_period, 
              spatial_coverage ) = extract_run_information_from_filename(ncfile_name)

            if ((swb_variable_name in grid_vars) 
                  and (scenario_name in scenario_names)
                  and (weather_data_name in weather_data_names)):

                index = f"{scenario_name}_{swb_variable_name}"
                logger.info(f"  munging data for weather_data_name: {weather_data_name};  time period: {short_time_period}; simulation name: {scenario_name}; ==> {swb_variable_name}.")
                logger.info(f"    filename: {ncfile_name}")
                #ds = xr.open_dataset(file)

                variable_operation = 'sum'
                if (swb_variable_name=='tmin' or swb_variable_name=='tmax' or swb_variable_name=='soil_storage'):
                    variable_operation = 'mean'

                summary_type = f"{summary_basetype}_{variable_operation}"
                output_grid_name = grid_stats_dir / f"{summary_type}__{scenario_name}__{weather_data_name}__{swb_variable_name}__{time_period}__{spatial_coverage}.nc"

                future = client.submit(sd.calculate_spatial_statistics, 
                                    netcdf_filename=file, 
                                    mask_filename=zone_path, 
                                    scenario_name=scenario_name,
                                    variable_name=swb_variable_name,
                                    weather_data_name=weather_data_name,
                                    summary_type=summary_type,
                                    zone_char_width=2,
                                    crs=project_crs)
                futures.append(future)
                output_filenames.append(output_grid_name)

        futures_df = pd.DataFrame({'output_grid_name':output_filenames, 'future':futures})

        result_grids = []
        result_zonal_stats = []

        for index, row in futures_df.iterrows():

            result_grid = row['future'].result()[0]
            result_zonal_stat = row['future'].result()[1]

            result_grid.to_netcdf(row['output_grid_name'])

            if make_tifs:

                ef.export_xarray_dataset_as_series_of_tif_images(ds=result_grid,
                                                                 summary_type=summary_basetype,
                                                                 scenario_name=scenario_name,
                                                                 weather_data_name=weather_data_name,
                                                                 swb_variable_name=swb_variable_name,
                                                                 time_period=short_time_period,
                                                                 output_image_dir=tif_image_dir)

            result_grids.append(result_grid)
            result_zonal_stats.append(result_zonal_stat)

            logger.info(f"  ...finished with Dask future task: {row['future']}")

#        result_grids = [future.result()[0] for future in futures]
#        result_zonal_stats = [future.result()[1] for future in futures]

        logger.info(f"  => completed creating summary grids (n={len(futures)}). ")
        logger.info(f"     running zonal stats. ")

        match summary_basetype:

            case 'monthly':
                monthly_sum_grids = result_grids
                monthly_sum_zonal_stats_df = result_zonal_stats[0]
                for n in range(1, len(result_zonal_stats)):
                    monthly_sum_zonal_stats_df = pd.concat([monthly_sum_zonal_stats_df, result_zonal_stats[n]])
                monthly_sum_zonal_stats_df.to_csv(monthly_sum_zonal_stats_csv_output_path,
                                                sep=",",
                                                index=False,
                                                header=True,
                                                na_rep=-999999)

            case 'mean_monthly':
                mean_monthly_sum_grids = result_grids
                mean_monthly_sum_zonal_stats_df = result_zonal_stats[0]
                for n in range(1, len(result_zonal_stats)):
                    mean_monthly_sum_zonal_stats_df = pd.concat([mean_monthly_sum_zonal_stats_df, result_zonal_stats[n]])
                mean_monthly_sum_zonal_stats_df.to_csv(mean_monthly_sum_zonal_stats_csv_output_path,
                                                    sep=",",
                                                    index=False,
                                                    header=True,
                                                    na_rep=-999999)

            case 'mean_annual':
                mean_annual_sum_grids = result_grids
                mean_annual_sum_zonal_stats_df = result_zonal_stats[0]
                for n in range(1, len(result_zonal_stats)):
                    mean_annual_sum_zonal_stats_df = pd.concat([mean_annual_sum_zonal_stats_df, result_zonal_stats[n]])
                mean_annual_sum_zonal_stats_df.to_csv(mean_annual_sum_zonal_stats_csv_output_path,
                                                    sep=",",
                                                    index=False,
                                                    header=True,
                                                    na_rep=-999999)

            case 'annual':
                annual_sum_grids = result_grids
                annual_sum_zonal_stats_df = result_zonal_stats[0]
                for n in range(1, len(result_zonal_stats)):
                    annual_sum_zonal_stats_df = pd.concat([annual_sum_zonal_stats_df, result_zonal_stats[n]])
                annual_sum_zonal_stats_df.to_csv(annual_sum_zonal_stats_csv_output_path,
                                                sep=",",
                                                index=False,
                                                header=True,
                                                na_rep=-999999)