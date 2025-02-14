import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.font_manager as fm
import pathlib as pl
import datetime as dt
import usgs_matplotlib_tweaks as usgs

def make_annual_plot_of_variables_by_zone(zonal_stats_df, 
                                          variable_dict={},
                                          weather_driver_dict={},
                                          output_filename='plot.pdf'):
    """Generate annual mean plot for each  'weather_driver' present in 'weather_driver_dict' 
       and for each 'variable_name' present in 'variable_dict'. X-axis is the zone id; Y-axis is the variable value.

    Assumptions:
      * dataframe contains at least the following columns of data:
         'zone' (str): a hydrologic unit code or other categorical variable to group results,
         'mean' (float): statistic generated for each zone/year combination,
         'date' (datetime64),
         'run_designation' (string): run descriptor (ex. 'historical', '2020-2040'),
         'weather_driver' (string): source of daily weather data (ex. 'PRISM', 'MIROC5'),
         'swb_variable_name' (string): swb variable name (ex. 'net_infiltration')

      * dataframe was generated such that it contains a time series of mean annual values

    Args:
        zonal_stats_df (Pandas dataframe): dataframe of zonal statistics gleaned from annual or monthly gridded data
                                           It is expected that the zonal stats correspond to a series of year values
    """
    # alias for input dataframe
    df = zonal_stats_df
    
    zones = df['zone'].unique().tolist()
        
    n_variables = len(variable_dict)

    fig = plt.figure(figsize=(10, n_variables*3))
    usgs.set_matplotlib_params_for_usgs_style()

    plotnum = 0
    for (variable_name, variable_details) in variable_dict.items():
        variable_description = variable_details['description']
        variable_units = variable_details['units']

        ylabel_text = f"Annual mean, {variable_units}"

        plotnum += 1
        ax = fig.add_subplot(n_variables,1,plotnum)
        for key, value in weather_driver_dict.items():
            color=value['color']
            linewidth=value['linewidth']
            linestyle=value['linestyle']
            print(f"creating plot for {variable_name}, as driven by {key}")
            
            subset_df = df.query(f"weather_driver=='{key}' and swb_variable_name=='{variable_name}'")

            ax.plot(subset_df['zone'], subset_df['mean'], color=color, 
                    linewidth=linewidth, linestyle=linestyle, label=key)
        ax.set_ylabel(ylabel_text, fontsize = 14)

        # see https://stackoverflow.com/questions/4700614/how-to-put-the-legend-outside-the-plot
        # Shrink current axis by 20%
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
        ax.set_xticklabels(subset_df['zone'], rotation=-44, ha='left', fontsize=10)
        
        # Put a legend to the right of the current axis
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize='small')
        ax.set_title(f"{variable_description}", fontsize=12)
        
    plt.tight_layout()
    fig.patch.set_alpha(1.0)    
    pl.Path(output_filename).resolve()            
    fig.savefig(output_filename, dpi = (250), bbox_inches='tight') 