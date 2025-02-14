import xarray as xr
import rioxarray as rio
import xrspatial as xrs
import numpy as np
import pandas as pd
import datetime as dt


def export_xarray_dataset_as_series_of_tif_images(ds,
                                            summary_type,
                                            scenario_name,
                                            weather_data_name,
                                            swb_variable_name,
                                            time_period,
                                            output_image_dir):


  match summary_type:

    case "mean_annual":
      ds[swb_variable_name].rio.to_raster(output_image_dir / 
        f"{time_period}__{summary_type}__{scenario_name}__{weather_data_name}__{swb_variable_name}.tif")
      return

    case _:
          print(f"unknown summary_type '{summary_type}'")
          #exit(1)
