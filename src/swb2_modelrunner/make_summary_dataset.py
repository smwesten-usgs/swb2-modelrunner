import site
site.addsitedir('.')  # Always appends to end

import stats_functions as sf
import time
import xarray as xr

def calculate_spatial_statistics(netcdf_filename,
                                 mask_filename,
                                 scenario_name,
                                 variable_name, 
                                 weather_data_name, 
                                 zone_char_width,
                                 summary_type,
                                 crs):

    xarray_dataset = xr.open_dataset(netcdf_filename)

    mask_dataarray = xr.open_dataarray(mask_filename).astype('int')[0,:,:]

    summary_dataset = sf.summarize_array_values(xarray_dataset=xarray_dataset,
                                                variable_name=variable_name,
                                                summary_type=summary_type,
                                                crs=crs)
    summary_dataset = summary_dataset.assign_attrs(swb_variable_name=variable_name, 
                                                     weather_data_name=weather_data_name,
                                                     scenario_name=scenario_name)

    zonal_stats = sf.calculate_zonal_statistics(xarray_dataarray=summary_dataset[variable_name],
                                                mask_dataarray=mask_dataarray,
                                                summary_type=summary_type,
                                                num_zone_chars=zone_char_width)
    zonal_stats['scenario_name'] = scenario_name
    zonal_stats['swb_variable_name'] = variable_name
    zonal_stats['weather_data_name'] = weather_data_name
    
    #xarray_dataset.close()
    #mask_dataarray.close()
    
    return summary_dataset, zonal_stats