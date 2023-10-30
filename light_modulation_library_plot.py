# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# Author: Gregoire Vandenschrick
# Date:   27/10/2023
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

# -- Imports for plots and graphs
#import matplotlib
#matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.widgets import Slider, RadioButtons
import pandas as pd
import matplotlib.animation as animation
from matplotlib.colors import LinearSegmentedColormap

import numpy as np
from suntime import Sun

import datetime
from pytz import timezone

import light_modulation_library_generation as lmlg
import light_modulation_settings as lmt

# --- plotting functions -------------------------------------------------------

def wavelength_to_rgb(wavelength, gamma=0.8):
    '''
    Create a color map based on the wavelength values

    taken from http://www.noah.org/wiki/Wavelength_to_RGB_in_Python
    This converts a given wavelength of light to an
    approximate RGB color value. The wavelength must be given
    in nanometers in the range from 380 nm through 750 nm
    (789 THz through 400 THz).

    Based on code by Dan Bruton
    http://www.physics.sfasu.edu/astro/color/spectra.html
    Additionally alpha value set to 0.5 outside range
    '''
    wavelength = float(wavelength)
    if wavelength >= 380 and wavelength <= 750:
        A = 1.
    else:
        A=0.5
    if wavelength < 380:
        wavelength = 380.
    if wavelength >750:
        wavelength = 750.
    if wavelength >= 380 and wavelength <= 440:
        attenuation = 0.3 + 0.7 * (wavelength - 380) / (440 - 380)
        R = ((-(wavelength - 440) / (440 - 380)) * attenuation) ** gamma
        G = 0.0
        B = (1.0 * attenuation) ** gamma
    elif wavelength >= 440 and wavelength <= 490:
        R = 0.0
        G = ((wavelength - 440) / (490 - 440)) ** gamma
        B = 1.0
    elif wavelength >= 490 and wavelength <= 510:
        R = 0.0
        G = 1.0
        B = (-(wavelength - 510) / (510 - 490)) ** gamma
    elif wavelength >= 510 and wavelength <= 580:
        R = ((wavelength - 510) / (580 - 510)) ** gamma
        G = 1.0
        B = 0.0
    elif wavelength >= 580 and wavelength <= 645:
        R = 1.0
        G = (-(wavelength - 645) / (645 - 580)) ** gamma
        B = 0.0
    elif wavelength >= 645 and wavelength <= 750:
        attenuation = 0.3 + 0.7 * (750 - wavelength) / (750 - 645)
        R = (1.0 * attenuation) ** gamma
        G = 0.0
        B = 0.0
    else:
        R = 0.0
        G = 0.0
        B = 0.0
    return (R,G,B,A)

def create_monthly_plots(day=21):
    """
    Function to create subplots for each Xth day of the month.
    Demo of capability.
    """
    maximum_voltage = 10  # Maximum voltage (adjustable, e.g., 120)
    # List of months (you can customize this if needed)
    months = range(1, 13)
    # Create subplots for each month
    fig, axs = plt.subplots(3, 4, figsize=(18, 12))
    fig.subplots_adjust(hspace=0.5)
    for month, ax in zip(months, axs.flat):
        # Create a plot for the 1st day of the current month
        desired_date = datetime.date(datetime.date.today().year, month, day)
        data_points_hours = lmlg.create_intensity_data_suntime(maximum_voltage, date=desired_date)[1]
        # Extract hours and intensities
        times_hours, intensities_hours = zip(*data_points_hours)
        # ax.plot(times_hours, intensities_hours, marker='o', linestyle='-', color='LightSkyBlue')
        ax.plot(times_hours, intensities_hours, linestyle='-', color='LightSkyBlue')

        # Set the x-axis and y-axis limits
        ax.set_xlim(4, 22)  # Replace xmin and xmax with your desired minimum and maximum for the x-axis
        ax.set_ylim(0.0, 10)  # Replace ymin and ymax with your desired minimum and maximum for the y-axis
        # Customize grid steps (tick intervals) for x and y axes
        x_ticks = np.arange(4.0, 22.01, 2)  # Define x-axis tick positions at intervals of one hour
        y_ticks = np.arange(0.0, 10.1, 0.5)  # Define y-axis tick positions at intervals of 10V
        ax.set_xticks(x_ticks)  # Set x-axis tick positions
        ax.set_yticks(y_ticks)  # Set y-axis tick positions

        ax.set_title(f'Light Intensity - {desired_date.strftime("%B")}')
        ax.set_xlabel('Time (hours)')
        ax.set_ylabel('Intensity')
        ax.grid(True)
    plt.tight_layout()
    plt.show()

def plot_data_on_ax(data_points_seconds, ax, title="", timing=0.01):
    """

    """
    (times, intensities) = zip(*data_points_seconds)
    ax.clear()  # Clear the previous plot
    ax.plot(times, intensities, marker='+', linestyle='-', color='r', label='Original Data')
    # Set the x-axis and y-axis limits
    plt.xlim(0, 86400)  # Replace xmin and xmax with your desired minimum and maximum for the x-axis
    plt.ylim(0.0, 10)  # Replace ymin and ymax with your desired minimum and maximum for the y-axis
    x_ticks = np.arange(0, 86401, 3600)  # Define x-axis tick positions at intervals of one hour
    y_ticks = np.arange(0.0, 10.1, 0.5)  # Define y-axis tick positions at intervals of 10V
    plt.xticks(x_ticks)  # Set x-axis tick positions
    plt.yticks(y_ticks)  # Set y-axis tick positions
    plt.xticks(rotation=90)
    ax.set_xlabel('Time (seconds since midnight)')
    ax.set_ylabel('Intensity')
    ax.set_title(title)
    #ax.legend()
    ax.grid(True)
    plt.pause(timing)

def create_plot(schedule_dic, color_dic, date=None, timing=5.0, save_path=None):
    """
    Function to plot several schedules
    Demo of capability and debug/confirmation of schedules generated
    """
    maximum_intensity = 500
    #plt.ion()
    fig, ax = plt.subplots(figsize=(11, 6))
    fig.set_facecolor("dimgrey")
    ax.set_facecolor("dimgrey")
    #fig = plt.figure(figsize=(10, 6))
    sum_intensities = [(0.0,0.0)]
    for label, (schedule, json, driver_maximum_intensity, serie, parallel) in schedule_dic.items():
        number_of_modules = serie*parallel
        photon_schedule = [(time, number_of_modules*lmlg.get_photon_flux_for_i(json, lmlg.get_i_from_u_and_maximum_driver_intensity(v_value, driver_maximum_intensity))) for (time, v_value) in schedule]
        # The simple sum does not work because the time coords are not synchronous.
        # One does need an interp_sum function here
        #sum_intensities = sum_data_points_seconds(sum_intensities, photon_schedule, max_intensity=10000.0)
        # Unpack the time and intensity values
        times, intensities = zip(*photon_schedule)
        # Create a plot and add lines
        ax.plot(times, intensities, label=label, marker='o', linestyle='-', color=color_dic[label])
    #times, intensities = zip(*sum_intensities)
    #maximum_intensity = (math.ceil(max(intensities)*10))/10
    #ax.plot(times, intensities, label='total', marker='o', linestyle='--', color='lightgray')

    current_date        = date if date is not None else datetime.date.today()
    sun                 = Sun(lmt.LATITUDE, lmt.LONGITUDE)
    sunrise_time_Seconds   = 3600 * lmlg.convert_datetime_to_decimal_hour(sun.get_sunrise_time(current_date) + datetime.timedelta(seconds=3600*lmt.TIMEZONE))
    sunset_time_seconds    = 3600 * lmlg.convert_datetime_to_decimal_hour(sun.get_sunset_time(current_date) + datetime.timedelta(seconds=3600*lmt.TIMEZONE))
    solstice_sum_sunrise   = 3600 * lmlg.get_summer_solstice_sunrise()
    solstice_sum_sunset    = 3600 * lmlg.get_summer_solstice_sunset()
    solstice_win_sunrise   = 3600 * lmlg.get_winter_solstice_sunrise()
    solstice_win_sunset    = 3600 * lmlg.get_winter_solstice_sunset()

    sunrise_sunset_ys = (0, maximum_intensity)
    ax.plot((solstice_sum_sunrise, solstice_sum_sunrise), sunrise_sunset_ys, label='Summer Solstice Sunrise', linestyle=':', color='gold')
    ax.plot((sunrise_time_Seconds, sunrise_time_Seconds), sunrise_sunset_ys, label=f'Current Sunrise ({lmlg.convert_decimal_hour_to_human_hour(sunrise_time_Seconds/3600)})', linestyle='--', color='goldenrod')
    ax.plot((solstice_win_sunrise, solstice_win_sunrise), sunrise_sunset_ys, label='Winter Solstice Sunrise', linestyle=':', color='darkgoldenrod')
    ax.plot((solstice_sum_sunset, solstice_sum_sunset), sunrise_sunset_ys, label='Summer Solstice Sunset', linestyle=':', color='lightcoral')
    ax.plot((sunset_time_seconds, sunset_time_seconds), sunrise_sunset_ys, label=f'Current Sunset ({lmlg.convert_decimal_hour_to_human_hour(sunset_time_seconds/3600)})', linestyle='--', color='indianred')
    ax.plot((solstice_win_sunset, solstice_win_sunset), sunrise_sunset_ys, label='Winter Solstice Sunset', linestyle=':', color='firebrick')
    # Set the x-axis and y-axis limits
    plt.xlim(0, 86400)  # Replace xmin and xmax with your desired minimum and maximum for the x-axis
    plt.ylim(0.0, maximum_intensity)  # Replace ymin and ymax with your desired minimum and maximum for the y-axis

    # Create a function to update the vertical line
    def update_vertical_line(num, line, ax, legend):
        #legend = ax.legend()
        #legend.remove()
        current_time = datetime.datetime.now(timezone('Europe/Brussels'))  # Replace 'Your_Timezone' with your desired timezone
        current_time_seconds = (current_time - current_time.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()
        line.set_xdata([current_time_seconds, current_time_seconds])
        line.set_label(f'Current Time ({current_time.strftime("%H:%M:%S")})')

        legend = ax.legend()
        return line,

    # Create the vertical line
    current_time_line, = ax.plot([0, 0], [0, maximum_intensity], label='Current Time ()', linestyle='--', color='white')

    # Set the x-axis and y-axis limits (same as in your code)
    plt.xlim(0, 86400)
    plt.ylim(0.0, maximum_intensity)

    # Customize grid steps (tick intervals) for x and y axes
    x_ticks = np.arange(0, 86401, 3600)  # Define x-axis tick positions at intervals of one hour
    y_ticks = np.arange(0.0, maximum_intensity+ 0.1, maximum_intensity/10)  # Define y-axis tick positions at intervals of 10V
    plt.xticks(x_ticks)  # Set x-axis tick positions
    plt.yticks(y_ticks)  # Set y-axis tick positions
    plt.xticks(rotation=90)

    # Set labels and title
    ax.set_xlabel('Time (seconds)')
    ax.set_ylabel('Photon intensity')
    ax.set_title(f'Intensity Comparison - {current_date:%d %b %Y}')
    ax.grid(True)
    # Add a legend
    legend = ax.legend()
    # Create an animation to update the vertical line every 10 seconds
    ani = animation.FuncAnimation(fig, update_vertical_line, fargs=(current_time_line, ax, legend),
                                  interval=10, blit=True, cache_frame_data=False)

    # Add top x-axis with hour labels
    top_ax = ax.twiny()
    top_ax.set_xlim(ax.get_xlim())
    top_ticks = np.arange(0, 86401, 3600)
    top_tick_labels = [f'{hour:02d}h' for hour in range(25)]
    top_ax.set_xticks(top_ticks)
    top_ax.set_xticklabels(top_tick_labels, rotation=90, horizontalalignment='center')
    top_ax.spines['top'].set_position(('outward', 0))
    top_ax.set_xlabel('Time (hours)')

    if save_path:
        fig.savefig(save_path)
    plt.show()

def animate_daily_spectrum(schedule_dic, time_step=60, save_path=None):
    """
    This function plots a spectrum diagram animated by the schedules defined for a day.
    if a save_path is received, it saves an mp4 video of it.
    A complete cumulated spectrum is plotted, along with two more lines to discriminate
    the contribution of the two first schedules.
    This function is currently tailored to receive 4 schedules, for FLUXengines 3500K, 5000k, APEXengines 385nm and 660nm.
    It plots vertical lines for 385 and 660nm. This should be adapted for other modules list.
    """
    schedules = [[schedule, lmlg.get_photon_spectrum(json), maximum_driver_intensity, serie, parallel, json] for schedule_name, (schedule, json, maximum_driver_intensity, serie, parallel) in schedule_dic.items()]

    # Define the time range of the day in seconds
    start_time = 21600
    end_time   = 79200

    # Defines the maximum of intensity for the spectrum
    max_intensity = 1000

    # Create a figure and axis for the plot
    fig, ax = plt.subplots(figsize=(10, 6))

    clim=(300,780)
    norm = plt.Normalize(*clim)
    wl = np.arange(clim[0],clim[1]+1,2)
    colorlist = list(zip(norm(wl),[wavelength_to_rgb(w) for w in wl]))
    spectralmap = LinearSegmentedColormap.from_list("spectrum", colorlist)

    wavelengths=range(clim[0], clim[1]+1,1)
    y = np.linspace(0, max_intensity, 100)
    X,Y = np.meshgrid(wavelengths, y)
    extent=(np.min(wavelengths), np.max(wavelengths), np.min(y), np.max(y))

    # Function to update the plot for each time of the day
    def update_plot(time_in_seconds):
        ax.clear()
        spectra_list                       = []
        spectra_list_no_660_no_385         = []
        spectra_list_no_660_no_385_no_5000 = []
        for i in range(len(schedules)):
            schedule = schedules[i][0]
            spectrum = schedules[i][1]
            maximum_driver_intensity = schedules[i][2]
            serie = schedules[i][3]
            parallel = schedules[i][4]
            modules = serie * parallel
            jsonDic = schedules[i][5]
            intensity = lmlg.get_i_from_schedule(schedule, time_in_seconds, maximum_driver_intensity/parallel)  # intensity in Amper
            optical_power_for_i = lmlg.get_optical_power_for_i(jsonDic, intensity)
            spectra_list.append(lmlg.get_spectrum_for_modules(spectrum, optical_power_for_i, modules))
            if i < 2:
                spectra_list_no_660_no_385.append(lmlg.get_spectrum_for_modules(spectrum,optical_power_for_i, modules))
                if i < 1:
                    spectra_list_no_660_no_385_no_5000.append(lmlg.get_spectrum_for_modules(spectrum,optical_power_for_i, modules))
        spectra_sum                       = lmlg.get_spectra_sum(spectra_list)
        spectra_sum_no_660_no_385         = lmlg.get_spectra_sum(spectra_list_no_660_no_385)
        spectra_sum_no_660_no_385_no_5000 = lmlg.get_spectra_sum(spectra_list_no_660_no_385_no_5000)
        wavelength, intensity                                             = zip(*spectra_sum)
        wavelength_no_660_no_385, intensity_no_660_no_385                 = zip(*spectra_sum_no_660_no_385)
        wavelength_no_660_no_385_no_5000, intensity_no_660_no_385_no_5000 = zip(*spectra_sum_no_660_no_385_no_5000)

        # Plot spectrum
        ax.plot(wavelength, intensity, linestyle='-', color='darkgray')
        ax.plot(wavelength_no_660_no_385, intensity_no_660_no_385, linestyle=':', linewidth=1, color='darkgray')
        ax.plot(wavelength_no_660_no_385_no_5000, intensity_no_660_no_385_no_5000, linestyle='--', linewidth=1.25, color='darkgray')

        # show color spectrum below spectrum
        plt.imshow(X, clim=clim,  extent=extent, cmap=spectralmap, aspect='auto')

        # Hides color spectrum above spectrum
        ax.fill_between(wavelength, intensity, max_intensity, color='w')

        ax.plot((385, 385), (0.0, max_intensity), linestyle='--', linewidth=1, color='lightgray')
        ax.plot((660, 660), (0.0, max_intensity), linestyle='--', linewidth=1, color='lightgray')

        ax.set_xlim(clim[0],clim[1])
        ax.set_ylim(0.0, max_intensity)
        ax.set_xlabel('Wavelength (nm)')
        ax.set_ylabel('Intensity (µmol/s.nm)')
        ax.set_title(f'Spectrum Intensity - {lmlg.convert_seconds_to_human_hour(time_in_seconds)}')
        ax.grid(True)

    # Create the animation
    anim = animation.FuncAnimation(fig, update_plot, frames=range(start_time, end_time+1, time_step), interval=100, cache_frame_data=False, repeat=False)
    if save_path:
        anim.save(save_path, writer="ffmpeg", fps=10)  # Save the animation to a file
    # Display the animated plot
    plt.show()

def animate_yearly_schedule(maximum_voltage, save_path=None):
    """
    Generates an animated graph of a plain intensity curve along the year.
    Demo of capability.
    """
    # Define the date range for a year (adjust as needed)
    start_date = datetime.date(datetime.date.today().year, 1, 1)
    end_date = datetime.date(datetime.date.today().year, 12, 31)
    #delta = datetime.timedelta(days=1)

    # Create a figure and axis for the plot
    fig, ax = plt.subplots(figsize=(10, 6))

    # Function to update the plot for each day
    def update_plot(date):
        ax.clear()
        data_points_seconds, data_points_hours = lmlg.create_intensity_data_suntime(maximum_voltage, date=date)[0:2]
        times_seconds, intensities_seconds = zip(*data_points_seconds)
        ax.plot(times_seconds, intensities_seconds, linestyle='-', color='LightSkyBlue')
        ax.set_xlim(14400, 79200)  # Customize x-axis limits
        ax.set_ylim(0.0, 10)  # Customize y-axis limits
        ax.set_xlabel('Time (seconds)')
        ax.set_ylabel('Intensity')
        ax.set_title(f'Light Intensity - {date.strftime("%B %d, %Y")}')
        ax.grid(True)

    # Create the animation
    anim = animation.FuncAnimation(fig, update_plot, frames=pd.date_range(start_date, end_date), interval=100, cache_frame_data=False)
    if save_path:
        anim.save(save_path, writer='pillow', fps=10)  # Save the animation to a file
    plt.show()

def create_yearly_schedule_3d_plot(maximum_voltage):
    """
    Generates a 3D surface plot of intensity over the course of a year.
    Demo of capability.
    """
    # Define the date range for a year (adjust as needed)
    start_date = datetime.date(datetime.date.today().year, 1, 1)
    end_date = datetime.date(datetime.date.today().year, 12, 31)

    # Create a figure for the 3D plot
    fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
    fig.subplots_adjust(top=1.1, bottom=-.1, left=-.1, right=1.1)

    # Define the range of seconds in a day and days in a year
    seconds_in_day = 86400
    days_in_year = (end_date - start_date).days + 1

    # Create arrays for X, Y, and Z
    x = np.linspace(0, seconds_in_day, 100)  # Seconds in a day
    y = np.arange(0, days_in_year)  # Days of the year
    X, Y = np.meshgrid(x, y)
    Z = np.zeros_like(X)

    # Function to calculate intensity for a given day and time
    def calculate_intensity(day, time):
        data_points_seconds, _ = lmlg.create_intensity_data_suntime(maximum_voltage, date=start_date + datetime.timedelta(days=day))[0:2]
        times_seconds, intensities_seconds = zip(*data_points_seconds)
        return np.interp(time, times_seconds, intensities_seconds, left=0.0, right=0.0)

    # Populate Z with intensity values
    for i in range(days_in_year):
        for j in range(100):
            Z[i, j] = calculate_intensity(i, x[j])

    # Create the 3D surface plot
    ax.plot_surface(X, Y, Z, cmap='viridis', alpha=0.4, zorder=15)

    # Add iso-intensity contours at specific levels (0, 2, 4, 6, 8, and 10)
    contour_levels = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    for level in contour_levels:
        contour = ax.contour(X, Y, Z, levels=[level], colors='red', linewidths=1)
        ax.clabel(contour, [level], fmt=f'Intensity {level}', inline=True, fontsize=10, colors='red', alpha=0.9, zorder=10)

    # Get the current date and time
    current_date = datetime.date.today()
    current_time = datetime.datetime.now().time()

    # Find the day index for the current date
    current_day_index = (current_date - start_date).days

    # Find the current time in seconds
    current_time_seconds = current_time.hour * 3600 + current_time.minute * 60 + current_time.second

    # Create a 3D line for the current day
    current_day_x = x
    current_day_y = np.full_like(x, current_day_index)
    current_day_z = np.array([calculate_intensity(current_day_index, t) for t in x])

    # Create a point at the current hour
    current_hour_x = np.full(2, current_time_seconds)
    current_hour_y = [current_day_index, current_day_index]
    current_hour_z = [0, calculate_intensity(current_day_index, current_time_seconds)]

    # Plot the current day line
    ax.plot(current_day_x, current_day_y, current_day_z, color='orange', linewidth=2, alpha=1, zorder=5)

    # Plot the current hour point
    ax.scatter(current_hour_x, current_hour_y, current_hour_z, color='darkorange', s=30, alpha=1, zorder=1)

    # Define the ticks for the 1st of each month
    month_ticks = []
    month_labels = []
    for month in range(1, 13):
        first_of_month = datetime.date(current_date.year, month, 1)
        day_index = (first_of_month - start_date).days
        month_ticks.append(day_index)  # Convert to seconds
        month_labels.append(first_of_month.strftime('%b %d'))  # Format as "Month Day"
   # Set the X-axis ticks at the 1st of each month
    ax.set_yticks(month_ticks)

    # Set the X-axis tick labels
    ax.set_yticklabels(month_labels, ha='left')

    ax.set_xlabel('Hours in a Day')
    ax.set_ylabel('Days of the Year')
    ax.set_zlabel('Intensity (Volt)')
    # Limit the X-axis to the range of 0 to 86400 seconds (0 to 1 day)
    ax.set_xlim(0, seconds_in_day)
    # Limit the Y-axis to the range of 0 to 365 days (the entire year)
    ax.set_ylim(0, days_in_year)
    ax.set_zlim(-0.1, 10.1)

    # Set the X-axis ticks at every 7200 seconds (2 hour)
    interval = 7200
    ax.set_xticks(np.arange(0, seconds_in_day + 1, interval))

    # Set the X-axis tick labels (formatted as HH:mm)
    ax.set_xticklabels([f'{i // 3600:02d}:{(i % 3600) // 60:02d}' for i in np.arange(0, seconds_in_day + 1, interval)])

   # Set the title and show the plot
    plt.title('Intensity Over the Year')
    plt.show()

# ------------------------------------------------------------------------------
