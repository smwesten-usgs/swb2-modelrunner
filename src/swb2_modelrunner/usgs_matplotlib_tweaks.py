import matplotlib as mpl
#import matplotlib.font_manager as fm

def set_matplotlib_params_for_usgs_style():

    mpl.rc('xtick.major', size=5)
    mpl.rc('ytick.major', size=5)
    mpl.rc('xtick.major', pad=5)
    mpl.rc('ytick.major', pad=5)

    mpl.rc('xtick', direction='in')
    mpl.rc('ytick', direction='in')
    mpl.rc('xtick', top=True)
    mpl.rc('ytick', right=True)

    ### Other defaults:
    mpl.rc('lines', linewidth=2, color='r')

    # Make Univers 57 Condensed the default"
    mpl.rcParams['font.sans-serif'] = "Univers 57 Condensed"
    mpl.rcParams['pdf.fonttype'] = 42  # Makes font export editable
    mpl.rcParams['ps.fonttype'] = 42
    mpl.rcParams['font.size'] = 10