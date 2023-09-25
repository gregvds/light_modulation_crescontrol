# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# Author: Gregoire Vandenschrick
# Date:   14/09/2023
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

# -- Imports for the generation of data_points
import math
import itertools
import operator
import datetime
import statistics
import numpy as np
from suntime import Sun
from scipy.interpolate import UnivariateSpline
from scipy import signal

# -- Imports for plots and graphs
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.widgets import Slider, RadioButtons
import pandas as pd
from matplotlib.animation import FuncAnimation

# -- Imports for communication with crescontrol
import time
import socket
import websocket
import requests
import smtplib
from email.mime.text import MIMEText

# -- Imports CONSTANTS from local settings. Be sure to complete them!
from light_modulation_settings import *

# ------------------------------------------------------------------------------
# -- Core functions ------------------------------------------------------------

def convert_human_hour_to_decimal_hour(hours_double_point_minutes_string):
    """
    This function convert a string XX:xx representing an Hour:minute into a float
    representing decimal hours
    """
    hours = int(hours_double_point_minutes_string.split(":")[0])
    minutes = float(hours_double_point_minutes_string.split(":")[1])/60
    return hours+minutes

def convert_datetime_to_decimal_hour(datetime):
    return(datetime.hour + datetime.minute/60 + datetime.second/3600)

def calculate_intensity(current_time, earliest_power_on, latest_power_off, amplitude_modulation):
    """
    Function to calculate intensity based on time of day - produce a simple cosine
    begining at earliest_power_on, ending at latest_power_off and reaching amplitude_modulation
    """
    # Calculate the current time in hours
    current_hour = convert_datetime_to_decimal_hour(current_time)
    # Calculate the fraction of the day passed
    fraction_of_day = (current_hour - earliest_power_on) / (latest_power_off - earliest_power_on)
    # Calculate the angle for the cosine curve within the interval from -π/2 to +π/2
    cosine_angle = math.pi * (fraction_of_day - 0.5)
    # Calculate a simple intensity using the positive half of the cosine curve
    # from earliest_power_on to latest_power_of
    if 0.0 <= fraction_of_day and fraction_of_day <= 1.0:
        intensity = max(0, math.cos(cosine_angle) * amplitude_modulation)
    else:
        intensity = 0.0
    return intensity

def smooth_transition_intensity(data_points_seconds, earliest_power_on, latest_power_off, transition_duration_minutes, overspill_proportion, smoothing_iteration):
    """
    Function to smooth the feet of the cosine curve at the begining and at the end
    The smoothing is obtained by a walking average weighted with a gaussian window
    smoothing operates along the transition_duration_minutes around begin and end
    this phase can be moved in or out according to begin and end time by a given proportion
    """
    earliest_power_on_seconds     = earliest_power_on * 3600
    latest_power_off_seconds      = latest_power_off * 3600
    transition_duration_seconds   = transition_duration_minutes * 60
    transition_length_in_timestep = int(transition_duration_minutes / TIME_STEP_MINUTES)

    earliest_transition_begin = earliest_power_on_seconds - transition_duration_seconds*overspill_proportion
    earliest_transition_end   = earliest_power_on_seconds + transition_duration_seconds*(1.0 - overspill_proportion)

    latest_transition_begin   = latest_power_off_seconds - transition_duration_seconds*(1.0 - overspill_proportion)
    latest_transition_end     = latest_power_off_seconds + transition_duration_seconds*overspill_proportion

    position_in_data = 0
    smoothed_data_points_seconds = []
    _, intensities = zip(*data_points_seconds)
    for (time, intensity) in data_points_seconds:
        if (earliest_transition_begin <= time and time <= earliest_transition_end)\
            or (latest_transition_begin <= time and time <= latest_transition_end):
            index_in = max(0,position_in_data-(2*transition_length_in_timestep))
            index_out = min(position_in_data+(2*transition_length_in_timestep),len(intensities)-1)
            intensities_subset = intensities[index_in:index_out+1]
            weight = signal.windows.gaussian(len(intensities_subset), 7)
            intensities_subset = itertools.starmap(operator.mul, zip(weight,intensities_subset))
            smoothed_intensity = statistics.fmean(intensities_subset)
            smoothed_data_points_seconds.append((time, smoothed_intensity))
        else:
            smoothed_data_points_seconds.append((time, intensity))
        position_in_data += 1
    while smoothing_iteration > 1:
        smoothing_iteration-=1
        smoothed_data_points_seconds = smooth_transition_intensity(smoothed_data_points_seconds,
                                                                   earliest_power_on,
                                                                   latest_power_off,
                                                                   int(transition_duration_minutes/smoothing_iteration),
                                                                   overspill_proportion,
                                                                   smoothing_iteration)
    return smoothed_data_points_seconds

def calculate_modulation_angle(current_date):
    """
    Function to compute the modulation angle according to day in the year
    """
    # Convert current_date to a datetime with time set to midnight
    current_datetime = datetime.datetime(current_date.year, current_date.month, current_date.day, 0, 0)
    # Calculate the day of the year
    day_of_year = (current_datetime - datetime.datetime(current_datetime.year, 1, 1)).days + 1
    # Calculate the angle for the sine wave modulation (peaks at the summer solstice, minimum at the winter solstice)
    modulation_angle = (2 * math.pi * (day_of_year - 173)) / 365.25
    return modulation_angle

def calculate_modulated_max_intensity(current_date, amplitude_modulation):
    """
    Function to calculate the modulated maximum intensity based on the current date
    """
    max_intensity_modulation_angle = calculate_modulation_angle(current_date)
    # Calculate the modulated maximum intensity
    min_intensity = 1.0 - amplitude_modulation/2.0  # Minimum intensity (scaled from 0 to 1)
    modulated_max_intensity = min_intensity + (amplitude_modulation/2.0 * math.cos(max_intensity_modulation_angle))
    return modulated_max_intensity

def calculate_modulated_earliest_power_on(current_date, earliest_power_on, power_on_time_modulation_hours):
    """
    Function to calculate the modulated earliest_power_on based on the current date
    ! Obsolete since create_intensity_data_suntime !
    """
    power_on_time_modulation_angle = calculate_modulation_angle(current_date)
    # Calculate the modulated earliest_power_on
    modulated_earliest_power_on = earliest_power_on - (power_on_time_modulation_hours * math.cos(power_on_time_modulation_angle))
    return modulated_earliest_power_on

def calculate_modulated_latest_power_off(current_date, latest_power_off, power_off_time_modulation_hours):
    """
    Function to calculate the modulated latest_power_off based on the current date
    ! Obsolete since create_intensity_data_suntime !
    """
    power_off_time_modulation_angle = calculate_modulation_angle(current_date)
    # Calculate the modulated latest_power_off
    modulated_latest_power_off = latest_power_off + (power_off_time_modulation_hours * math.cos(power_off_time_modulation_angle))
    return modulated_latest_power_off

def get_equinox_sunrise(time_zone=2):
    """
    This function gives the hour of sunrise at Equinox, used to evaluate the
    difference between it and sunrise time of the current day.
    Time is given according to timezone (default = 2).
    The 22th of March of the current year is used, rather roughly...
    """
    timezone_hours = datetime.timedelta(seconds=3600*time_zone)
    sun = Sun(LATITUDE, LONGITUDE)
    equinox_sunrise_time = sun.get_sunrise_time(date=datetime.date(datetime.date.today().year,3,22)) + timezone_hours
    #print(equinox_sunrise_time)
    return convert_datetime_to_decimal_hour(equinox_sunrise_time)

def get_equinox_sunset(time_zone=2):
    """
    This function gives the hour of sunset at Equinox, used to evaluate the
    difference between it and sunset time of the current day.
    Time is given according to timezone (default = 2).
    The 22th of March of the current year is used, rather roughly...
    """
    timezone_hours = datetime.timedelta(seconds=3600*time_zone)
    sun = Sun(LATITUDE, LONGITUDE)
    equinox_sunset_time = sun.get_sunset_time(date=datetime.date(datetime.date.today().year,3,22)) + timezone_hours
    #print(equinox_sunset_time)
    return convert_datetime_to_decimal_hour(equinox_sunset_time)

def get_summer_solstice_sunrise(time_zone=2):
    """
    This function gives the hour of Summer Solstice, used to evaluate the
    difference between it and sunrise time of the current day.
    Time is given according to timezone (default = 2).
    The 22th of June of the current year is used, rather roughly...
    """
    timezone_hours = datetime.timedelta(seconds=3600*time_zone)
    sun = Sun(LATITUDE, LONGITUDE)
    equinox_sunrise_time = sun.get_sunrise_time(date=datetime.date(datetime.date.today().year,6,22)) + timezone_hours
    #print(equinox_sunrise_time)
    return convert_datetime_to_decimal_hour(equinox_sunrise_time)

def get_summer_solstice_sunset(time_zone=2):
    """
    This function gives the hour of sunset at Summer Solstice, used to evaluate the
    difference between it and sunset time of the current day.
    Time is given according to timezone (default = 2).
    The 22th of June of the current year is used, rather roughly...
    """
    timezone_hours = datetime.timedelta(seconds=3600*time_zone)
    sun = Sun(LATITUDE, LONGITUDE)
    equinox_sunset_time = sun.get_sunset_time(date=datetime.date(datetime.date.today().year,6,22)) + timezone_hours
    #print(equinox_sunset_time)
    return convert_datetime_to_decimal_hour(equinox_sunset_time)

def get_winter_solstice_sunrise(time_zone=2):
    """
    This function gives the hour of Winter Solstice, used to evaluate the
    difference between it and sunrise time of the current day.
    Time is given according to timezone (default = 2).
    The 22th of December of the current year is used, rather roughly...
    """
    timezone_hours = datetime.timedelta(seconds=3600*time_zone)
    sun = Sun(LATITUDE, LONGITUDE)
    equinox_sunrise_time = sun.get_sunrise_time(date=datetime.date(datetime.date.today().year,12,22)) + timezone_hours
    #print(equinox_sunrise_time)
    return convert_datetime_to_decimal_hour(equinox_sunrise_time)

def get_winter_solstice_sunset(time_zone=2):
    """
    This function gives the hour of sunset at Winter Solstice, used to evaluate the
    difference between it and sunset time of the current day.
    Time is given according to timezone (default = 2).
    The 22th of December of the current year is used, rather roughly...
    """
    timezone_hours = datetime.timedelta(seconds=3600*time_zone)
    sun = Sun(LATITUDE, LONGITUDE)
    equinox_sunset_time = sun.get_sunset_time(date=datetime.date(datetime.date.today().year,12,22)) + timezone_hours
    #print(equinox_sunset_time)
    return convert_datetime_to_decimal_hour(equinox_sunset_time)

def create_intensity_data_suntime(maximum_voltage, amplitude_modulation=None, mode="centered", length_proportion=1.0, date=None, smoothing=True, transition_duration_minutes=60):
    """
    Create a list of times and intensities throughout the day (packed in tuples).
    This function uses latitude and longitude to generate earliest_power_on and
    latest_power_off.
    The function has 4 modes:
    - 'centered' (default) produces a curve centered on noon during a given proportion of the duration of the current day
    - 'dawn' produces a curve from sunrise during a given proportion of the duration of the current day
    - 'dusk' produces a curve before sunset during a given proportion of the duration of the current day
    By default the length_proportion = 1.0 but takes a value between 0.0 and 1.5
    """
    # check inputs for proper content and values
    if mode not in ('centered', 'dawn', 'dusk'):
        print(f"Error: {mode} is not a recognized working mode for this function.\nPlease choose either 'centered', 'dawn' or 'dusk'.")
        return
    if not ((0.0 <= length_proportion) and (length_proportion <= 1.5)):
        print(f"Error: length_proportion {length_proportion} should be in the range 0.0-1.5.")
        return

    current_date        = date if date is not None else datetime.date.today()
    current_datetime    = datetime.datetime(current_date.year, current_date.month, current_date.day, 0, 0)  # Start at midnight
    sun                 = Sun(LATITUDE, LONGITUDE)
    earliest_power_on   = convert_datetime_to_decimal_hour(sun.get_sunrise_time(current_date) + datetime.timedelta(seconds=3600*TIMEZONE))
    latest_power_off    = convert_datetime_to_decimal_hour(sun.get_sunset_time(current_date) + datetime.timedelta(seconds=3600*TIMEZONE))
    day_length = latest_power_off - earliest_power_on
    noon = (earliest_power_on + latest_power_off)/2.0

    equinox_day_length = get_equinox_sunset()-get_equinox_sunrise()
    #print(f'Proportion of current day length vs Equinox day length: {day_length/equinox_day_length}')
    summer_solstice_day_length = get_summer_solstice_sunset() - get_summer_solstice_sunrise()
    #print(f'Proportion of current day length vs Summer Solstice day length: {day_length/summer_solstice_day_length}')
    winter_solstice_day_length = get_winter_solstice_sunset() - get_winter_solstice_sunrise()
    #print(f'Proportion of current day length vs Winter Solstice day length: {day_length/winter_solstice_day_length}')
    #print(f'Proportion of Winter Solstice day length vs Summer Solstice day length: {winter_solstice_day_length/summer_solstice_day_length}')

    # New methodology to calculate amplitude modulation based on current day length
    # compared to the longest day of the year (namely the Summer Solstice day)
    # The third root is here to pull back up a bit values (minimum = 0.73333 -> 0.90...)
    modulated_max_intensity = 1.0
    if amplitude_modulation is None: #Default case
        modulated_max_intensity = min(1.0, math.pow((day_length/summer_solstice_day_length), (1.0/3.0)))
    else:                            # Deprecated, needs the user to guess/give a amplitude of modulation...
        modulated_max_intensity = calculate_modulated_max_intensity(current_date, amplitude_modulation)

    # Modifications of begin and end of curve according to the choosen mode
    if mode == 'centered':
        # begins late and finishes early in proportion with the day duration
        # Default length_proportion=1.0 generate a normal complete curve.
        earliest_power_on    = noon - day_length * length_proportion/2.0
        latest_power_off     = noon + day_length * length_proportion/2.0
    elif mode == 'dawn':
        # finishes early in proportion with the day duration
        latest_power_off     = earliest_power_on + day_length * length_proportion
    elif mode == 'dusk':
        # begins late in proportion with the day duration
        earliest_power_on    = latest_power_off - day_length * length_proportion

    # Calculates all tuples (time_in_second, intensity) for the current day
    time_step           = datetime.timedelta(minutes=TIME_STEP_MINUTES) # Adjustable time step
    data_points_seconds = []                                            # Data points with time in seconds
    data_points_hours   = []                                            # Data points with time in hours
    max_iterations      = 24 * 60 // TIME_STEP_MINUTES                  # Maximum number of iterations (1 day)
    iterations          = 0                                             # Counter for iterations
    while iterations < max_iterations:
        intensity = calculate_intensity(current_datetime, earliest_power_on, latest_power_off, modulated_max_intensity)
        intensity = max(0,intensity)
        # Calculate time in seconds, starting from midnight of the current day
        time_in_seconds = int((current_datetime - datetime.datetime(current_date.year, current_date.month, current_date.day)).total_seconds())
        data_points_seconds.append((time_in_seconds, intensity))
        # Calculate current hour for the hours version
        current_hour = current_datetime.hour + current_datetime.minute / 60
        data_points_hours.append((current_hour, intensity))  # Store data with time in hours
        current_datetime += time_step
        iterations += 1

    # smooth begin and end of curve
    if smoothing is True:
        overspill_proportion = 0.85
        smoothing_iteration = 1
        data_points_seconds = smooth_transition_intensity(data_points_seconds, earliest_power_on, latest_power_off, transition_duration_minutes, overspill_proportion, smoothing_iteration)
    return scale_data_points_seconds(data_points_seconds, maximum_voltage), scale_data_points_seconds(data_points_hours, maximum_voltage), earliest_power_on, latest_power_off, modulated_max_intensity

def create_intensity_data(earliest_power_on,
                          latest_power_off,
                          power_on_time_modulation_hours,
                          power_off_time_modulation_hours,
                          transition_duration_minutes,
                          amplitude_modulation,
                          maximum_voltage,
                          date=None):
    """
    Create a list of times and intensities throughout the day (packed in tuples).
    !! This methodology is obsolete, please use create_intensity_data_suntime !!
    """
    current_date        = date if date is not None else datetime.date.today()
    current_datetime    = datetime.datetime(current_date.year, current_date.month, current_date.day, 0, 0)  # Start at midnight
    time_step           = datetime.timedelta(minutes=TIME_STEP_MINUTES)  # Adjustable time step
    data_points_seconds = []  # Data points with time in seconds
    data_points_hours   = []  # Data points with time in hours
    max_iterations      = 24 * 60 // TIME_STEP_MINUTES  # Maximum number of iterations (1 day)
    iterations          = 0  # Counter for iterations
    earliest_power_on   = calculate_modulated_earliest_power_on(current_date, earliest_power_on, power_on_time_modulation_hours)
    latest_power_off    = calculate_modulated_latest_power_off(current_date, latest_power_off, power_off_time_modulation_hours)
    modulated_max_intensity = calculate_modulated_max_intensity(current_date, amplitude_modulation)
    while iterations < max_iterations:
        intensity = calculate_intensity(current_datetime, earliest_power_on, latest_power_off, modulated_max_intensity)
        intensity = max(0,intensity)
        # Calculate time in seconds, starting from midnight of the current day
        time_in_seconds = int((current_datetime - datetime.datetime(current_date.year, current_date.month, current_date.day)).total_seconds())
        data_points_seconds.append((time_in_seconds, intensity))
        # Calculate current hour for the hours version
        current_hour = current_datetime.hour + current_datetime.minute / 60
        data_points_hours.append((current_hour, intensity))  # Store data with time in hours
        current_datetime += time_step
        iterations += 1
    overspill_proportion = 0.85
    smoothing_iteration = 1
    data_points_seconds = smooth_transition_intensity(data_points_seconds, earliest_power_on, latest_power_off, transition_duration_minutes, overspill_proportion, smoothing_iteration)
    return scale_data_points_seconds(data_points_seconds, maximum_voltage), scale_data_points_seconds(data_points_hours, maximum_voltage), earliest_power_on, latest_power_off, modulated_max_intensity

# -- Functions more directly linked to produce data_points for crescontrol -----

def scale_data_points_seconds(data_points_seconds, scale_factor):
    """
    This function multiply all the intensity of the data_points_seconds by the scale factor
    """
    data_points_seconds = [(time, intensity*scale_factor) for time, intensity in data_points_seconds]
    return data_points_seconds

def parallelize_data_points_seconds(data_points_seconds_1, data_points_seconds_2):
    """
    This function pads both data_points_seconds with zero intensity values for
    all the time present in one but not in the other
    ! Assuming data_points_seconds_1 and padded_data_points_seconds_2 have the same time intervals
    """
    times_1 = set(time for time, _ in data_points_seconds_1)
    times_2 = set(time for time, _ in data_points_seconds_2)
    # Find the missing times that are in data_points_seconds_1 but not in data_points_seconds_2
    missing_times_in_2 = times_1 - times_2
    missing_times_in_1 = times_2 - times_1
    # Pad data_points_seconds with missing times and zero intensity
    padded_data_points_seconds_1 = data_points_seconds_1 + [(time, 0.0) for time in missing_times_in_1]
    padded_data_points_seconds_2 = data_points_seconds_2 + [(time, 0.0) for time in missing_times_in_2]

    return sorted(padded_data_points_seconds_1), sorted(padded_data_points_seconds_2)

def sum_data_points_seconds(data_points_seconds_1, data_points_seconds_2, min_intensity=0.0, max_intensity=10.0):
    """
    This function allows to add one schedule to another, assuring the result will
    not pass out of range min/max and that the sum will be conducted timewize.
    ! Assuming data_points_seconds_1 and padded_data_points_seconds_2 have the same time intervals
    """
    (padded_data_points_seconds_1,
    padded_data_points_seconds_2) = parallelize_data_points_seconds(data_points_seconds_1,
                                                                    data_points_seconds_2)
    sum = [(time1, max(min(intensity1+intensity2,max_intensity),min_intensity))
            for time1, intensity1 in padded_data_points_seconds_1
            for time2, intensity2 in padded_data_points_seconds_2
            if time1 == time2]
    return sum

def substract_data_points_seconds(data_points_seconds_1, data_points_seconds_2, min_intensity=0.0, max_intensity=10.0):
    """
    this function substracts one schedule from another, creating a new one.
    Playing with the width and height of two schedules, one can achieve schedule
    for dawn and dusk moments.
    Create sets of times from data_points_seconds_1 and data_points_seconds_2
    ! Assuming data_points_seconds_1 and padded_data_points_seconds_2 have the same time intervals
    """
    (padded_data_points_seconds_1,
    padded_data_points_seconds_2) = parallelize_data_points_seconds(data_points_seconds_1,
                                                                    data_points_seconds_2)
    common_times = set(time for time, _ in padded_data_points_seconds_1) & set(time for time, _ in padded_data_points_seconds_2)
    result = [(time, max(intensity1 - intensity2, min_intensity))
              for time, intensity1 in data_points_seconds_1
              for time2, intensity2 in padded_data_points_seconds_2
              if time == time2 and time in common_times]
    return result

def gate_data_points_seconds(data_points_seconds, lower_gate=1, upper_gate=10):
    """
    Gate the intensity values between lower_gate and upper_gate
    """
    gated_data_points_seconds = []
    for (time, intensity) in data_points_seconds:
        if intensity <= 0.01:
            gated_data_points_seconds.append((time, intensity))
        elif intensity <= lower_gate:
            gated_data_points_seconds.append((time,lower_gate))
        elif lower_gate < intensity < upper_gate:
            gated_data_points_seconds.append((time, intensity))
        else:
            gated_data_points_seconds.append((time, upper_gate))
    return gated_data_points_seconds

def simplify_data_points_seconds(data_points_seconds, desired_num_points=32, ax=None):
    """
    this trims down the number of points in the schedule to 32 by default (and max allowed by CresControl)
    Convert data_points_seconds to a NumPy array for easier manipulation
    """
    data_points_seconds = np.array(data_points_seconds)
    # Sort data_points_seconds by time
    data_points_seconds = data_points_seconds[data_points_seconds[:, 0].argsort()]
    # Extract times and intensities
    times = data_points_seconds[:, 0]
    intensities = data_points_seconds[:, 1]
    # Use spline interpolation to fit the curve and extract the desired number of points
    spline = UnivariateSpline(times, intensities, k=5, s=0)
    fit_times = np.linspace(times.min(), times.max(), desired_num_points)
    fit_intensities = spline(fit_times)
    if ax:
        ax.clear()  # Clear the previous plot
        ax.plot(times, intensities, marker='o', linestyle='-', color='b', label='Original Data')
        ax.plot(fit_times, fit_intensities, marker='x', linestyle='-', color='r', label='Fitted Curve')
        ax.set_xlabel('Time (seconds since midnight)')
        ax.set_ylabel('Intensity')
        ax.set_title('Fitted Intensity Curve')
        ax.legend()
        ax.grid(True)
        plt.pause(0.01)  # Pause briefly to update the plot
    # The fit_times and fit_intensities arrays now contain the desired number of
    # points that best fit the curve.
    data_points_intensities = list(zip(fit_times, fit_intensities))
    # ensures that no negative values were introduced by the spline computation
    return data_points_intensities

def clean_intermediate_zeros_from_data_points_seconds(data_points_seconds):
    """
    suppress all the data points 0.0 contiguous to two other 0.0 values to minimize
    useless points. This can trim down the length of the schedule to less than the
    maximum number of points allowed by CresControl.
    !! See function clean_intermediate_flats_from_data_points_seconds that also
    cleans up unnecessary points aligned of whatever constant values !!
    """
    filtered_result  = []
    left_intensity = data_points_seconds[0][1]  # Initialize the left intensity
    right_intensity   = data_points_seconds[2][1]  # Initialize the right intensity
    position = 1
    max_position = len(data_points_seconds)-1
    # Iterate through the result, skipping central zero intensities
    for time, intensity in data_points_seconds[1:-1]:
        if (left_intensity < 0.01 and intensity < 0.01 and right_intensity < 0.01)\
           or (time < 10800 or time > 75600):
            left_intensity = intensity
            position +=1
            right_intensity = data_points_seconds[min(position+1,max_position)][1]
            # drop zero intensity between two zero intensities
            continue
        filtered_result.append((time, intensity))
        left_intensity = intensity
        position +=1
        right_intensity = data_points_seconds[min(position+1,max_position)][1]
    return filtered_result

def clean_intermediate_flats_from_data_points_seconds(data_points_seconds):
    """
    suppress all the intermediate data values defining flats periods to minimize
    useless points. This can trim down the length of the schedule to less than the
    maximum number of points allowed by CresControl, hence the incremental reduction
    implemented in clean_and_simplify_to_desired_points().
    """
    filtered_result  = []
    left_intensity = data_points_seconds[0][1]  # Initialize the left intensity
    right_intensity   = data_points_seconds[2][1]  # Initialize the right intensity
    position = 1
    max_position = len(data_points_seconds)-1
    # Iterate through the result, skipping central zero intensities
    for time, intensity in data_points_seconds[1:-1]:
        if (abs(left_intensity-intensity) < 0.01) and (abs(intensity-right_intensity) < 0.01)\
           or (time < 10800 or time > 75600):
            left_intensity = intensity
            position +=1
            right_intensity = data_points_seconds[min(position+1,max_position)][1]
            # drop zero intensity between two zero intensities
            continue
        filtered_result.append((time, intensity))
        left_intensity = intensity
        position +=1
        right_intensity = data_points_seconds[min(position+1,max_position)][1]
    return filtered_result

def clean_and_simplify_to_desired_points(data_points_seconds, desired_num_points = 32, plot = False):
    """
    The function combines both precent ones, trying to save a maximum of information
    while trimming down the schedule to 32 points such as allowed by the Crescontrol
    Because the suppression of intermediate zeros drops points, if applied directly
    on a trimmed down to 32 points, schedules contain always less than 32 points.
    here we decrease incrementally the number of points in schedule, drop unnecessary
    zeros and repeat the operation until the result contain 32 points after zeros
    dropping.
    """
    number_of_data_points = len(data_points_seconds)
    potential_data_points_seconds = data_points_seconds
    if plot:
        fig, ax = plt.subplots()  # Create the initial plot
    else:
        ax = None
    while len(potential_data_points_seconds) > desired_num_points:
        number_of_data_points -=1
        potential_data_points_seconds = clean_intermediate_flats_from_data_points_seconds(
            simplify_data_points_seconds(data_points_seconds, desired_num_points=number_of_data_points, ax=ax))
    if plot:
        plt.show()
    return potential_data_points_seconds

def convert_data_points_to_string(data_points_seconds, decimal_places = 2):
    """
    Function to output proper string from data_points_seconds
    """
    # Create a string representation with brackets
    data_string = "[" + ",".join([f"[{int(time)},{min(max(0.00,intensity),10.00):.{decimal_places}f}]" for time, intensity in data_points_seconds]) + "]"
    return data_string

def stringify_schedules_in_dic(schedule_dic):
    """
    Stringify all schedules in dictionary
    """
    stringified_schedules_dic = {}
    for (key, (schedule, out_name)) in schedule_dic.items():
        stringified_schedules_dic[key] = (convert_data_points_to_string(schedule), out_name)
    return stringified_schedules_dic


# --- Communication Functions

def round_thousands_second_time_delta(time_taken):
    return f'{float(time_taken):02.3f}'

def format_time_modulation_delta(time1, time2, format):
    """
    This function handles the sign of time difference expressed using the given
    format.
    """
    if ((time1-time2)>= 0) and (((time1*60)%60)-((time2*60)%60) >= 0):
        formatted_time_delta = format % (time1-time2,
                 ((time1*60)%60)-((time2*60)%60))
        formatted_time_delta = " " + formatted_time_delta
    else:
        formatted_time_delta = format % (abs(time1-time2),
                 abs(((time1*60)%60)-((time2*60)%60)))
        formatted_time_delta = "-" + formatted_time_delta
    return formatted_time_delta

def clean_up_crescontrol_response(response):
    """
    Tidy up the response from CresControl.
    split around ::, takes the second part, and suppress chars ", {, and }.
    """
    return response.split("::")[1].replace('"',' ').replace('{','').replace('}','')

def execute_command(query, clean_answer=True):
    """
    sends a query to CresControl through websockets,
    gets the response,
    measure the delay it took between send and receive
    and return cleaned response and delay
    """
    start = time.time()
    ws = websocket.create_connection(f'ws://{CRESCONTROL_IP}:81',timeout=1000)
    ws.send(query)
    response=ws.recv()
    ws.close()
    end = time.time()
    time_taken = end - start
    if clean_answer:
        response = clean_up_crescontrol_response(response)
    return response, time_taken

def execute_command_and_report(query, output="", total_time=0):
    """
    Wrapping function of above function and add reporting/time to given args
    """
    output += f"Query: {query}\n"
    response, time_taken = execute_command(query)
    total_time += time_taken
    output += f'Response (in {round_thousands_second_time_delta(time_taken)} secs.): {response}\n'
    return output, total_time

def test_crescontrol_online():
    status = False
    output = f'Testing if CresControl on ws://{CRESCONTROL_IP}:81 is accessible:\n'
    output, time_taken = execute_command_and_report('system:cpu-id', output)
    if CRESCONTROL_CPU_ID in output and time_taken < 1000:
        output += f'Crescontrol online :-)\n\n'
        status =  True
    else:
        output += f'Unable to reach {CRESCONTROL_URL} with CPU ID {CRESCONTROL_CPU_ID} :-(: {response}\n\n'
        status =  False
    return output, status

def set_crescontrol_timezone(timezone):
    """
    Set the timezone of the CresControl so as it is coherent and adapted with
    the suntime of your place and does not changes according to summer daylight
    saving time, which the sun does not follow :-).
    """
    output = f'Set CresControl set timezone = {timezone}:\n'
    (response, time_taken) = execute_command_and_report(f'time:timezone={timezone}', output)
    return response, time_taken

def get_crescontrol_led_verbosity():
    output = f'Get CresControl led verbosity:\n'
    (output, time_taken) = execute_command_and_report(f'led:verbosity', output=output)
    return output, time_taken

def set_crescontrol_led_verbosity(level):
    """
    3 : Full
    2 : only warnings
    1 : only errors
    0 : Off
    """
    if value in (0,1,2,3):
        output = f'Set CresControl led verbosity:\n'
        (output, time_taken) = execute_command_and_report(f'led:verbosity={level}', output=output)
        return output, time_taken
    else:
        return f'Faulty value. Must be between 0 and 3 included', 0,0

def get_crescontrol_websocket_remote_allow_connection():
    output = f'Get CresControl websocket remote allow connection:\n'
    (output, time_taken) = execute_command_and_report(f'websocket:remote:allow-connection', output=output)
    return output, time_taken

def set_crescontrol_websocket_remote_allow_connection(value):
    """
    0 : False
    1 : True
    """
    if value in (0,1):
        output = f'Set CresControl websocket remote allow connection to {value}:\n'
        (output, time_taken) = execute_command_and_report(f'websocket:remote:allow-connection={value}', output=output)
        return output, time_taken
    else:
        return f'Faulty value. Must be 0 or 1', 0.0

def get_crescontrol_time():
    output = f'Crescontrol time:\n'
    (output, time_taken) = execute_command_and_report('time:daytime', output=output)
    return output

def create_schedule_if_not_exists(schedule_name, output="", total_time=0):
    """
    This function creates a schedule with the given name
    """
    status = False
    output += f'Creating schedule {schedule_name} if not existant:\n'
    # Check if schedule exists already, if not, creates it.
    (output,_) = execute_command_and_report(f'schedule:get-name("{schedule_name}")',                                output=output)
    if '"error":"a schedule with this name does not exist"' not in output:
        output += f'Schedule {schedule_name} already exists :-).\n\n'
        return output, True
    else:
        output += f'Creating schedule {schedule_name} :-).\n'
        (output,total_time) = execute_command_and_report(f'schedule:add("{schedule_name}")',                        output=output, total_time=total_time)
        (output,total_time) = execute_command_and_report(f'schedule:set-daily("{schedule_name}")',                  output=output, total_time=total_time)
        # Check if the request was successful (status code 200)
        if total_time < 2000:
            # Print the response content (the HTML of the webpage in this case)
            status =  True
            output += f'{schedule_name} successfully created in {round_thousands_second_time_delta(total_time)} secs :-).\n\n'
        else:
            status =  False
            output += f'Failed to create {schedule_name} :-(.\n\n'
        return output, status

def send_schedules_to_crescontrol(schedule_dic):
    """
    This function sends all the schedules defined in the dictionary given.
    keys of dic are the schedule names, content is a tuple containing the schedule
    and the out name it has to modulate.
    """
    status = True
    output = ''
    for schedule_name, (schedule, out_port) in schedule_dic.items():
        total_time = 0
        output += f'Sending schedule data for schedule {schedule_name} to modulate {out_port}:\n'

        (output,total_time) = create_schedule_if_not_exists(schedule_name,                                          output=output, total_time=total_time)
        (output,total_time) = execute_command_and_report(f'schedule:set-enabled("{schedule_name}",0)',              output=output, total_time=total_time)
        (output,total_time) = execute_command_and_report(f'schedule:set-parameter("{schedule_name}","{out_port}:voltage")', output=output, total_time=total_time)
        (output,total_time) = execute_command_and_report(f'schedule:set-timetable("{schedule_name}","{schedule}")', output=output, total_time=total_time)
        (output,total_time) = execute_command_and_report(f'schedule:set-resolution("{schedule_name}",0.05,0.02)',   output=output, total_time=total_time)
        (output,total_time) = execute_command_and_report(f'schedule:set-enabled("{schedule_name}",1)',              output=output, total_time=total_time)
        (output,total_time) = execute_command_and_report(f'schedule:save("{schedule_name}")',                       output=output, total_time=total_time)

        # Check if the request was successful
        if total_time < 8000:
            output += f'{schedule_name} successfully updated in {round_thousands_second_time_delta(total_time)} secs :-).\n\n'
            status = status and True
        else:
            output += f'Failed to update {schedule_name} :-(.\n\n'
            status = status and False
        time.sleep(PAUSE_BETWEEN_QUERIES)
    return output, status

def printAndLog(myLine, myFile):
    '''
    Print something and writes it also to given log file
    '''
    print(myLine)
    myFile.write(myLine+'\n')

def get_local_ip():
    return [l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1],
                        [[(s.connect(('8.8.8.8', 53)),
                           s.getsockname()[0],
                           s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]

def send_mail(email_message):
    """
    Create an email message and sends it
    """
    email_message = MIMEText(email_message)
    email_message['Subject'] = "Generation of schedules script and CresControl Responses"
    email_message['From'] = SENDER_EMAIL
    email_message['Reply-to'] = SENDER_EMAIL
    email_message['To'] = RECEIVER_EMAIL
    # Connect to the SMTP server and send the email
    with smtplib.SMTP(SMTP_SERVER, 587) as server:  # Replace with your SMTP server details
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, email_message.as_string())


# --- Supplementary functions, for debug, plotting and so on -------------------

# Function to create subplots for each Xth day of the month
def create_monthly_plots(day = 21):
    """
    ! Should be adapted to use new function create_intensity_data_suntime !
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
        data_points_seconds, data_points_hours = create_intensity_data_suntime(maximum_voltage, date=desired_date)
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
        #ax.set_xticklabels(rotation=90)

        ax.set_title(f'Light Intensity - {desired_date.strftime("%B")}')
        ax.set_xlabel('Time (hours)')
        ax.set_ylabel('Intensity')
        ax.grid(True)
    plt.tight_layout()
    plt.show()

# Function to generate an animated plot of a year day by day
def animate_yearly_schedule(maximum_voltage, save_path=None):
    """
    Generates an animated graph of a plain intensity curve along the year.
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
        data_points_seconds, data_points_hours = create_intensity_data_suntime(maximum_voltage, date=date)[0:2]
        times_seconds, intensities_seconds = zip(*data_points_seconds)
        ax.plot(times_seconds, intensities_seconds, linestyle='-', color='LightSkyBlue')
        ax.set_xlim(14400, 79200)  # Customize x-axis limits
        ax.set_ylim(0.0, 10)  # Customize y-axis limits
        ax.set_xlabel('Time (seconds)')
        ax.set_ylabel('Intensity')
        ax.set_title(f'Light Intensity - {date.strftime("%B %d, %Y")}')
        ax.grid(True)

    # Create the animation
    anim = FuncAnimation(fig, update_plot, frames=pd.date_range(start_date, end_date), interval=100)
    if save_path:
        anim.save(save_path, writer='pillow', fps=10)  # Save the animation to a file
    plt.show()  # Display the animated plot

def create_yearly_schedule_3d_plot(maximum_voltage):
    """
    Generates a 3D surface plot of intensity over the course of a year.
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
        data_points_seconds, _ = create_intensity_data_suntime(maximum_voltage, date=start_date + datetime.timedelta(days=day))[0:2]
        times_seconds, intensities_seconds = zip(*data_points_seconds)
        return np.interp(time, times_seconds, intensities_seconds, left=0.0, right=0.0)

    # Populate Z with intensity values
    for i in range(days_in_year):
        for j in range(100):
            Z[i, j] = calculate_intensity(i, x[j])

    # Create the 3D surface plot
    ax.plot_surface(X, Y, Z, cmap='viridis', alpha=0.8)

    # Add iso-intensity contours at specific levels (0, 2, 4, 6, 8, and 10)
    contour_levels = [0, 2, 4, 6, 8, 10]
    for level in contour_levels:
        contour = ax.contour(X, Y, Z, levels=[level], colors='red', linewidths=1)
        ax.clabel(contour, [level], fmt=f'Intensity {level}', inline=True, fontsize=10, colors='red')

    ax.set_xlabel('Seconds in a Day')
    ax.set_ylabel('Days of the Year')
    ax.set_zlabel('Intensity (Volt)')

    # Limit the X-axis to the range of 0 to 86400 seconds (0 to 1 day)
    ax.set_xlim(0, seconds_in_day)

    # Limit the Y-axis to the range of 0 to 365 days (the entire year)
    ax.set_ylim(0, days_in_year)

    # Set the X-axis ticks at every 7200 seconds (2 hour)
    interval = 7200
    ax.set_xticks(np.arange(0, seconds_in_day + 1, interval))

    # Set the X-axis tick labels (formatted as HH:mm)
    ax.set_xticklabels([f'{i // 3600:02d}:{(i % 3600) // 60:02d}' for i in np.arange(0, seconds_in_day + 1, interval)])

   # Set the title and show the plot
    plt.title('Intensity Over the Year')
    plt.show()

def create_triple_plot(data_points_intensity1, data_points_intensity2, data_points_intensity3):
    """
    Function to plot three data_points_intensities
    """
    # You can define labels for each dataset
    label1 = "3500K"
    label2 = "5000K"
    label3 = "385nm"
    # Unpack the time and intensity values for each dataset
    #print(data_points_intensity1)
    times1, intensities1 = zip(*data_points_intensity1)
    times2, intensities2 = zip(*data_points_intensity2)
    times3, intensities3 = zip(*data_points_intensity3)
    # Create a plot and add lines for each dataset
    plt.figure(figsize=(10, 6))
    plt.plot(times1, intensities1, label=label1, marker='o', linestyle='-', color='LightSalmon')
    plt.plot(times2, intensities2, label=label2, marker='o', linestyle='-', color='SkyBlue')
    plt.plot(times3, intensities3, label=label3, marker='o', linestyle='-', color='DarkSlateBlue')
    # Set the x-axis and y-axis limits
    plt.xlim(0, 86400)  # Replace xmin and xmax with your desired minimum and maximum for the x-axis
    plt.ylim(0.0, 10)  # Replace ymin and ymax with your desired minimum and maximum for the y-axis
    # Customize grid steps (tick intervals) for x and y axes
    x_ticks = np.arange(0, 86401, 3600)  # Define x-axis tick positions at intervals of one hour
    y_ticks = np.arange(0.0, 10.1, 0.5)  # Define y-axis tick positions at intervals of 10V
    plt.xticks(x_ticks)  # Set x-axis tick positions
    plt.yticks(y_ticks)  # Set y-axis tick positions
    plt.xticks(rotation=90)
    # Set labels and title
    plt.xlabel('Time (seconds)')
    plt.ylabel('Intensity (Volts)')
    plt.title('Intensity Comparison')
    plt.grid(True)
    # Add a legend
    plt.legend()
    # Show the plot
    plt.show()


# ------------------------------------------------------------------------------
