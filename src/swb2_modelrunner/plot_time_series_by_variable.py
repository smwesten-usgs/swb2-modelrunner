import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.font_manager as fm
import pathlib as pl
import datetime as dt
import usgs_matplotlib_tweaks as usgs

def make_time_series_plot_by_variable(zonal_stats_df, 
                                      variable_dict={},
                                      weather_driver_dict={},
                                      output_filename='plot.pdf',
                                      time_variable='year'):
    """Generate mean annual or monthly plots for each 'weather_driver' present in 'weather_driver_dict' 
       and for each 'variable_name' present in 'variable_dict'.

    Assumptions:
      * dataframe contains at least the following columns of data:
         'mean' (float): statistic generated for each zone/year combination,
         'year' (int),
         'date' (datetime64),
         'run_designation' (string): run descriptor (ex. 'historical', '2020-2040'),
         'weather_driver' (string): source of daily weather data (ex. 'PRISM', 'MIROC5'),
         'swb_variable_name' (string): swb variable name (ex. 'net_infiltration')

      * dataframe was generated such that it contains a time series of mean annual or mean monthly grids

    Args:
        zonal_stats_df (Pandas dataframe): dataframe of zonal statistics gleaned from annual or monthly gridded data
                                           It is expected that the zonal stats correspond to a series of year values or
                                           to a set of 12 mean monthly values. 
    """
    # alias for input dataframe
    df = zonal_stats_df
    
    n_variables = len(variable_dict)

    # Add month names:
    month_abbreviations = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

    fig = plt.figure(figsize=(10, n_variables*3))
    usgs.set_matplotlib_params_for_usgs_style()

    plotnum = 0
    for (variable_name, variable_details) in variable_dict.items():
        variable_description = variable_details['description']
        variable_units = variable_details['units']

        if time_variable=='month':
            ylabel_text = f"Monthly mean, {variable_units}"
        else:
            ylabel_text = f"Annual mean, {variable_units}"

        plotnum += 1
        ax = fig.add_subplot(n_variables,1,plotnum)
        for key, value in weather_driver_dict.items():
            color=value['color']
            linewidth=value['linewidth']
            linestyle=value['linestyle']
            print(f"creating plot for {variable_name}, as driven by {key}")
            subset_df = df.query(f"weather_driver=='{key}' and swb_variable_name=='{variable_name}'")
            ax.plot(subset_df[time_variable], subset_df['mean'], color=color, 
                    linewidth=linewidth, linestyle=linestyle, label=key)
        ax.set_ylabel(ylabel_text, fontsize = 14)

        if time_variable=='month':
            ax.set(xticks=[1,2,3,4,5,6,7,8,9,10,11,12])
            ax.set(xticklabels = month_abbreviations)

        # see https://stackoverflow.com/questions/4700614/how-to-put-the-legend-outside-the-plot
        # Shrink current axis by 20%
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])

        # Put a legend to the right of the current axis
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize='small')
        ax.set_title(f"{variable_description}", fontsize=12)
        
#        ax.legend()

    plt.tight_layout()
    fig.patch.set_alpha(1.0)    
    pl.Path(output_filename).resolve()            
    fig.savefig(output_filename, dpi = (250), bbox_inches='tight') 