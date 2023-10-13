# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# Author: Gregoire Vandenschrick
# Date:   14/09/2023
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

# -- Imports for the generation of data_points
import os
import logging
import math
import itertools
import operator
import datetime
import statistics
import numpy as np
from suntime import Sun
from scipy.interpolate import UnivariateSpline
from scipy import signal
from scipy.interpolate import interp1d
from scipy.integrate import trapz, simps, quad

# -- Imports for plots and graphs
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.widgets import Slider, RadioButtons
import pandas as pd
import matplotlib.animation as animation
from matplotlib.colors import LinearSegmentedColormap

# -- Imports for communication with crescontrol
import time
from pytz import timezone
import socket
import websocket
import requests
import json
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

def convert_decimal_hour_to_human_hour(hours_decimal):
    """
    This function takes a float decimal hour argument and formats it into
    HHhmm.
    """
    return "%02dh%02d" % (hours_decimal, (hours_decimal*60)%60)

def convert_seconds_to_human_hour(time_seconds):
    """
    """
    return "%02dh%02d" % (time_seconds/3600, ((time_seconds%3600))/60)

def convert_datetime_to_decimal_hour(datetime):
    return(datetime.hour + datetime.minute/60 + datetime.second/3600)

def calculate_intensity(current_time, earliest_power_on, latest_power_off, amplitude_modulation, maximum_broadness=4, transition_duration_minutes=None):
    """
    New methodology to draw the curve of the schedule, based on
    cos(π/2 * sin(fraction_of_day (-π/2 to +π/2))^maximum_broadness
    """
    # Calculate the current time in hours
    current_hour = convert_datetime_to_decimal_hour(current_time)
    earliest_power_on -= transition_duration_minutes/60.0
    latest_power_off += transition_duration_minutes/60.0

    # Calculate the fraction of the day passed
    fraction_of_day = (current_hour - earliest_power_on) / (latest_power_off - earliest_power_on)
    # Calculate the angle for the cosine curve within the interval from -π/2 to +π/2
    cosine_angle = math.pi * (fraction_of_day - 0.5)
    # Calculate a simple intensity using the positive half of the cosine curve
    # from earliest_power_on to latest_power_of
    if 0.0 <= fraction_of_day and fraction_of_day <= 1.0:
        intensity = max(0, math.cos((math.pi/2)*(math.sin(cosine_angle)**maximum_broadness)))
    else:
        intensity = 0.0
    return intensity * amplitude_modulation

def calculate_intensity_2(current_time, earliest_power_on, latest_power_off, amplitude_modulation, maximum_broadness=4, transition_duration_minutes=None):
    """
    New methodology to draw the curve of the schedule, based on
    1 - cos(π/2 * cos(a * fraction_of_day)^b)^c
    fraction_of_day being inside (-π/2 to +π/2)
    a being (1/(b + e))^(1/4*d)
    b being d/3
    c being b^d
    d being maximum_broadness
    e being (-2.05/39.0625)*(d-2)*(d-15)
    """
    # Calculate the current time in hours
    current_hour = convert_datetime_to_decimal_hour(current_time)
    earliest_power_on -= transition_duration_minutes/60.0
    latest_power_off += transition_duration_minutes/60.0

    # Calculate the fraction of the day passed
    fraction_of_day = (current_hour - earliest_power_on) / (latest_power_off - earliest_power_on)
    # Calculate the angle for the cosine curve within the interval from -π/2 to +π/2
    cosine_angle = math.pi * (fraction_of_day - 0.5)
    b = maximum_broadness/3.0
    c = b**maximum_broadness
    e = (-2.05/39.0625)*(maximum_broadness-2)*(maximum_broadness-15)
    a = (1/(b + e))**(1/4*maximum_broadness)
    # Calculate a simple intensity using the positive half of the cosine curve
    # from earliest_power_on to latest_power_of
    if 0.0 < fraction_of_day and fraction_of_day < 1.0:
        intensity = max(0, 1-(math.cos((math.pi/2)*(math.cos(a*cosine_angle)**b))**c))
    else:
        intensity = 0.0
    return intensity * amplitude_modulation

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
    return convert_datetime_to_decimal_hour(equinox_sunset_time)

def mod_on_off_times(earliest_power_on, latest_power_off, mode='centered', length_proportion=1.0, shift_proportion=0.0):
    """
    Moves the times of power_on and power_off according to mode.
    The attribute length_proportion is use to shrink or expand a centered curve
    or is used to define the relative length of a dawn/dusk curve relative to
    current day length.
    shift_proportion is used to advance (negative values) or delay (positive values)
    The times of power ON/OFF by a proportion of current day length.
    """
    new_earliest_power_on = earliest_power_on
    new_latest_power_off  = latest_power_off
    day_length            = latest_power_off - earliest_power_on
    noon                  = (earliest_power_on + latest_power_off)/2.0
    shift                 = day_length * shift_proportion
    # Modifications of begin and end of curve according to the choosen mode
    if mode == 'centered':
        # begins late and finishes early in proportion with the day duration
        # Default length_proportion=1.0 generate a normal complete curve.
        new_earliest_power_on    = (noon - day_length * length_proportion/2.0) + shift
        new_latest_power_off     = (noon + day_length * length_proportion/2.0) + shift
    elif mode == 'dawn':
        # finishes early in proportion with the day duration
        new_earliest_power_on    += shift
        new_latest_power_off     = (earliest_power_on + day_length * length_proportion)
    elif mode == 'dusk':
        # begins late in proportion with the day duration
        new_latest_power_off     += shift
        new_earliest_power_on    = (latest_power_off - day_length * length_proportion)
    logging.debug(f'\
 Displacement of ON/OFF times according to mode {mode},\n\
                              length proportion of {length_proportion}\n\
                           and shift proportion of {shift_proportion}.\n\
    Original day length: {convert_decimal_hour_to_human_hour(day_length)}.\n\
    Midday time:         {convert_decimal_hour_to_human_hour(noon)}.\n\
    Original on time     {convert_decimal_hour_to_human_hour(earliest_power_on)}\n\
                moved to {convert_decimal_hour_to_human_hour(new_earliest_power_on)}.\n\
    Original off time    {convert_decimal_hour_to_human_hour(latest_power_off)}\n\
                moved to {convert_decimal_hour_to_human_hour(new_latest_power_off)}.')
    return new_earliest_power_on, new_latest_power_off

def get_modulated_max_intensity(current_date, earliest_power_on, latest_power_off):
    """
    New methodology to calculate amplitude modulation based on current day length
    compared to the longest day of the year (namely the Summer Solstice day)
    The third root is here to pull back up a bit values (minimum = 0.73333 -> 0.90...)
    """
    day_length = latest_power_off - earliest_power_on
    summer_solstice_day_length = get_summer_solstice_sunset() - get_summer_solstice_sunrise()
    winter_solstice_day_length = get_winter_solstice_sunset() - get_winter_solstice_sunrise()
    # This goes from 0 at the winter solstice to 1 at the summer solstice
    reduction_proportion = (day_length - winter_solstice_day_length) / (summer_solstice_day_length - winter_solstice_day_length)
    logging.debug(f'reduction proportion of maximum intensity: {reduction_proportion}')
    amplitude_modulation = 0.9
    modulated_max_intensity = amplitude_modulation + (1.0 - amplitude_modulation) * reduction_proportion
    logging.debug(f'Modulated maximum intensity: {modulated_max_intensity}')
    return modulated_max_intensity

def calculate_Schedule(current_date, earliest_power_on, latest_power_off, modulated_max_intensity, maximum_broadness=None, transition_duration_minutes=0):
    """
    """
    # Calculates all tuples (time_in_second, intensity) for the current day
    current_datetime    = datetime.datetime(current_date.year, current_date.month, current_date.day, 0, 0)  # Start at midnight
    time_step           = datetime.timedelta(minutes=TIME_STEP_MINUTES) # Adjustable time step
    data_points_seconds = []                                            # Data points with time in seconds
    data_points_hours   = []                                            # Data points with time in hours
    max_iterations      = 24 * 60 // TIME_STEP_MINUTES                  # Maximum number of iterations (1 day)
    iterations          = 0                                             # Counter for iterations
    while iterations < max_iterations:
        intensity=0
        intensity = calculate_intensity(current_datetime, earliest_power_on, latest_power_off, modulated_max_intensity, maximum_broadness=maximum_broadness, transition_duration_minutes=transition_duration_minutes)
        intensity = max(0,intensity)
        # Calculate time in seconds, starting from midnight of the current day
        time_in_seconds = int((current_datetime - datetime.datetime(current_date.year, current_date.month, current_date.day)).total_seconds())
        data_points_seconds.append((time_in_seconds, intensity))
        # Calculate current hour for the hours version
        current_hour = current_datetime.hour + current_datetime.minute / 60
        data_points_hours.append((current_hour, intensity))  # Store data with time in hours
        current_datetime += time_step
        iterations += 1
    return data_points_seconds, data_points_hours

def create_intensity_data_suntime(maximum_voltage, mode="centered", length_proportion=1.0, shift_proportion=0.0, date=None, maximum_broadness=4, transition_duration_minutes=0, plot=False):
    """
    Create a list of times and intensities throughout the day (packed in tuples).
    This function uses latitude and longitude to generate earliest_power_on and
    latest_power_off.
    The function has 4 modes:
    - 'centered' (default) produces a curve centered on noon during a given proportion of the duration of the current day
    - 'dawn' produces a curve from sunrise during a given proportion of the duration of the current day
    - 'dusk' produces a curve before sunset during a given proportion of the duration of the current day
    By default the length_proportion = 1.0 but can take a value between 0.0 and 1.5 in order to shrink inside
    or extend beyond daylight normal duration.
    """
    # check inputs for proper content and values
    if mode not in ('centered', 'dawn', 'dusk'):
        logging.error(f"Error: {mode} is not a recognized working mode for this function.\nPlease choose either 'centered', 'dawn' or 'dusk'.")
        return
    if not ((0.0 <= length_proportion) and (length_proportion <= 1.5)):
        logging.error(f"Error: length_proportion {length_proportion} should be in the range 0.0-1.5.")
        return
    current_date        = date if date is not None else datetime.date.today()

    # Calculates power ON/OFF times and maximum intensity for the day
    sun                 = Sun(LATITUDE, LONGITUDE)
    earliest_power_on   = convert_datetime_to_decimal_hour(sun.get_sunrise_time(current_date) + datetime.timedelta(seconds=3600*TIMEZONE))
    latest_power_off    = convert_datetime_to_decimal_hour(sun.get_sunset_time(current_date) + datetime.timedelta(seconds=3600*TIMEZONE))
    modulated_max_intensity = get_modulated_max_intensity(current_date, earliest_power_on, latest_power_off)

    # moves power ON and OFF times according to the mode and the length proportion
    (earliest_power_on, latest_power_off) = mod_on_off_times(earliest_power_on, latest_power_off, mode=mode, length_proportion=length_proportion, shift_proportion=shift_proportion)

    # generates schedule for the current day with its power ON/OFF times, max intensity and curve_mode
    (data_points_seconds, data_points_hours) = calculate_Schedule(current_date, earliest_power_on, latest_power_off, modulated_max_intensity, maximum_broadness=maximum_broadness, transition_duration_minutes=transition_duration_minutes)

    # returns scaled schedules for the voltage required and a few more infos for reporting
    return scale_data_points_seconds(data_points_seconds, maximum_voltage, plot=plot), scale_data_points_seconds(data_points_hours, maximum_voltage), earliest_power_on, latest_power_off, modulated_max_intensity


# -- Functions more directly linked to produce data_points for crescontrol -----

def scale_data_points_seconds(data_points_seconds, scale_factor, plot=False):
    """
    This function multiply all the intensity of the data_points_seconds by the scale factor
    """
    if plot:
        fig, ax = plt.subplots()  # Create the initial plot
        plot_data_on_ax(data_points_seconds, ax, title="Data points before scaling", timing=2)
    else:
        ax = None
    scaled_data_points_seconds = [(time, intensity*scale_factor) for time, intensity in data_points_seconds]
    if ax:
        plot_data_on_ax(scaled_data_points_seconds, ax, title="Data points after scaling", timing=2)
        plt.close(fig)
    return scaled_data_points_seconds

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

def gate_data_points_seconds(data_points_seconds, treshold=0.01, lower_gate=1, upper_gate=None, plot=False):
    """
    Gate the intensity values between lower_gate and upper_gate.
    Intensity values below treshold are zeroed.
    """
    # We first retrieve the maximum intensity of the schedule
    if plot:
        fig, ax = plt.subplots()  # Create the initial plot
        plot_data_on_ax(data_points_seconds, ax, title="Data points before gated", timing=2)
    else:
        ax = None
    max_intensity = 0
    for (time, intensity) in data_points_seconds:
        max_intensity = max(max_intensity, intensity)
    # If no upper_gate is given, maximum intensity should be kept so
    if upper_gate is None:
        upper_gate = max_intensity
    # Now we can scale the intensity values that are bigger than threshold
    # between the lower_gate and upper_gate
    gated_data_points_seconds = []
    gating_factor = (upper_gate-lower_gate)/(max_intensity-treshold)
    for (time, intensity) in data_points_seconds:
        if intensity <= treshold:
            gated_data_points_seconds.append((time, 0.0))
        else:
            gated_intensity = lower_gate + ((intensity-treshold)*gating_factor)
            gated_data_points_seconds.append((time, gated_intensity))
    if ax is not None:
        plot_data_on_ax(gated_data_points_seconds, ax, title="Data points after gated", timing=2)
        plt.close(fig=fig)
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
    # The fit_times and fit_intensities arrays now contain the desired number of
    # points that best fit the curve.
    data_points_intensities = list(zip(fit_times, fit_intensities))
    # ensures that no negative values were introduced by the spline computation
    data_points_intensities = gate_data_points_seconds(data_points_intensities, lower_gate=0)
    if ax:
        plot_data_on_ax(data_points_intensities, ax)
    return data_points_intensities

def clean_intermediate_zeros_from_data_points_seconds(data_points_seconds, treshold=0.01, ax=None):
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
        if (left_intensity < treshold and intensity < treshold and right_intensity < treshold)\
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
    if ax:
        plot_data_on_ax(filtered_result, ax)
    return filtered_result

def clean_intermediate_flats_from_data_points_seconds(data_points_seconds, treshold=0.001, ax=None):
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
        if (abs(left_intensity-intensity) < treshold) and (abs(intensity-right_intensity) < treshold)\
           or (time < 10800 or time > 82800):
            left_intensity = intensity
            position +=1
            right_intensity = data_points_seconds[min(position+1,max_position)][1]
            # drop zero intensity between two zero intensities
            continue
        filtered_result.append((time, intensity))
        left_intensity = intensity
        position +=1
        right_intensity = data_points_seconds[min(position+1,max_position)][1]
    if ax:
        plot_data_on_ax(filtered_result, ax, title="Reduction of number of data points")
        (times, intensities) = zip(*filtered_result)
    return filtered_result

def clean_and_simplify_to_desired_points(data_points_seconds, desired_num_points=32, plot=False):
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
            simplify_data_points_seconds(data_points_seconds, desired_num_points=number_of_data_points), ax=ax)
    if plot:
        time.sleep(2.0)
        plt.close(fig=fig)
    return potential_data_points_seconds

def convert_data_points_to_string(data_points_seconds, decimal_places=2, minimum_intensity=0.00, maximum_intensity=10.0):
    """
    Function to output proper string from data_points_seconds
    """
    # Create a string representation with brackets
    data_string = "[" + ",".join([f"[{(time):.{decimal_places}f},{min(max(minimum_intensity,intensity),maximum_intensity):.{decimal_places}f}]" for time, intensity in data_points_seconds]) + "]"
    return data_string

def stringify_schedules_in_dic(schedule_dic):
    """
    Stringify all schedules in dictionary
    """
    stringified_schedules_dic = {}
    for (key, (schedule, out_name, meta)) in schedule_dic.items():
        stringified_schedules_dic[key] = (convert_data_points_to_string(schedule), out_name, meta)
    return stringified_schedules_dic


# --- Functions for communication with the CresControl -------------------------

def round_thousands_second_time_delta(time_taken):
    """
    """
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

def execute_command_and_report(query, clean_answer=True):
    """
    Wrapping function of above function and add reporting/time to given args
    """
    response, time_taken = execute_command(query, clean_answer=clean_answer)
    logging.debug(f'\
   -> Query:                      {query}\n\
      <- Response (in {round_thousands_second_time_delta(time_taken)} secs.): {response}')
    return response

def test_crescontrol_online():
    logging.info(f'Testing if CresControl on ws://{CRESCONTROL_IP}:81 is accessible:')
    output = execute_command_and_report('system:cpu-id')
    status = CRESCONTROL_CPU_ID in output
    if status:
        logging.info(f'Crescontrol online :-)\n')
    else:
        logging.warning(f'Unable to reach {CRESCONTROL_URL} with CPU ID {CRESCONTROL_CPU_ID} :-(: {response}\n')
    return status

def get_crescontrol_time():
    """
    """
    logging.info(f'Crescontrol time:')
    output = execute_command_and_report('time:daytime')
    return output

def set_crescontrol_timezone(timezone):
    """
    Set the timezone of the CresControl so as it is coherent and adapted with
    the suntime of your place and does not changes according to summer daylight
    saving time, which the sun does not follow :-).
    """
    logging.info(f'Set CresControl set timezone = {timezone}:')
    response = execute_command_and_report(f'time:timezone={timezone}')
    return response

def get_crescontrol_led_verbosity():
    """
    """
    logging.info(f'Get CresControl led verbosity:')
    output = execute_command_and_report(f'led:verbosity')
    return output

def set_crescontrol_led_verbosity(level):
    """
    3 : Full
    2 : only warnings
    1 : only errors
    0 : Off
    """
    if value in (0,1,2,3):
        logging.info(f'Set CresControl led verbosity:')
        output = execute_command_and_report(f'led:verbosity={level}')
        return output
    else:
        logging.error(f'Faulty value. Must be between 0 and 3 included')
        return f'Faulty value. Must be between 0 and 3 included', 0,0

def get_crescontrol_websocket_remote_allow_connection():
    """
    """
    logging.info(f'Get CresControl websocket remote allow connection:')
    output = execute_command_and_report(f'websocket:remote:allow-connection')
    return output

def set_crescontrol_websocket_remote_allow_connection(value):
    """
    0 : False
    1 : True
    """
    if value in (0,1):
        logging.info(f'Set CresControl websocket remote allow connection to {value}:')
        output = execute_command_and_report(f'websocket:remote:allow-connection={value}')
        return output
    else:
        logging.error(f'Faulty value. Must be 0 or 1')
        return f'Faulty value. Must be 0 or 1'

def create_schedule_if_not_exists(schedule_name):
    """
    This function creates a schedule with the given name
    """
    status = False
    logging.info(f'Creating schedule {schedule_name} if not existant:')
    # Check if schedule exists already, if not, creates it.
    output = execute_command_and_report(f'schedule:get-name("{schedule_name}")')
    if ' error : a schedule with this name does not exist ' not in output:
        logging.info(f'Schedule {schedule_name} already exists :-).')
        return True
    else:
        logging.info(f'Creating schedule {schedule_name} :-).')
        output = execute_command_and_report(f'schedule:add("{schedule_name}")')
        status = ('success' in output)
        # Check if the request was successful (status code 200)
        if status:
            logging.info(f'{schedule_name} successfully created :-).')
        else:
            logging.error(f'Failed to create {schedule_name} :-(.')
        return status

def send_schedules_to_crescontrol(schedule_dic):
    """
    This function sends all the schedules defined in the dictionary given.
    keys of dic are the schedule names, content is a tuple containing the schedule
    and the out name it has to modulate.
    """
    global_status = True
    for schedule_name, (schedule, out_port, meta) in schedule_dic.items():
        logging.info(f'Sending schedule data for schedule {schedule_name} to modulate {out_port}:')

        status = create_schedule_if_not_exists(schedule_name)
        global_status = global_status and status
        if not status:
            logging.warning(f'Schedule {schedule_name} encountered a problem during its creation or search, passing it.')
            continue
        logging.info(f'Schedule {schedule_name} created or existing already :-).')

        output = execute_command_and_report(f'schedule:set-enabled("{schedule_name}",0)')
        status = ('success' in output)
        global_status = global_status and status
        if not status:
            logging.warning(f'Schedule {schedule_name} encountered a problem during its disabling, passing it.')
            continue
        logging.info(f'Schedule {schedule_name} disabled :-).')

        output = execute_command_and_report(f'schedule:set-parameter("{schedule_name}","{out_port}:voltage")')
        status = ('success' in output)
        global_status = global_status and status
        if not status:
            logging.warning(f'Schedule {schedule_name} encountered a problem during its parameter:voltage setting, passing it.')
            continue
        logging.info(f'Schedule {out_port}:voltage set as parameter of {schedule_name} :-).')

        output = execute_command_and_report(f'schedule:set-timetable("{schedule_name}","{schedule}")')
        status = (schedule in output)
        global_status = global_status and status
        if not status:
            logging.warning(f'Schedule {schedule_name} encountered a problem during its schedule setting, passing it.')
            continue
        logging.info(f'Schedule {schedule_name} schedule updated :-).')

        res = '0.05,0.02'
        output = execute_command_and_report(f'schedule:set-resolution("{schedule_name}",{res})')
        status = (res in output)
        global_status = global_status and status
        if not status:
            logging.warning(f'Schedule {schedule_name} encountered a problem during its resolution setting, passing it.')
            continue
        logging.info(f'Schedule {schedule_name} resolution set at {res} :-).')

        """
        output = execute_command_and_report(f'{out_port}:meta="{meta}"', clean_answer=False)
        status = (meta in output)
        global_status = global_status and status
        if not status:
            logging.warning(f'Schedule {schedule_name} encountered a problem during its meta definition, passing it.')
            continue
        logging.info(f'Schedule {schedule_name} meta set :-).')
        """

        output = execute_command_and_report(f'schedule:set-enabled("{schedule_name}",1)')
        global_status = global_status and ('success' in output)
        if not status:
            logging.warning(f'Schedule {schedule_name} encountered a problem during its enabling, passing it.')
            continue
        logging.info(f'Schedule {schedule_name} enabled :-).')

        output = execute_command_and_report(f'schedule:save("{schedule_name}")')
        global_status = global_status and ('success' in output)
        if not status:
            logging.warning(f'Schedule {schedule_name} encountered a problem during its saving, passing it.')
            continue
        logging.info(f'Schedule {schedule_name} saved :-).\n')

        time.sleep(PAUSE_BETWEEN_QUERIES)
    return global_status


# --- Other functions ----------------------------------------------------------

def get_module_json(module_name, refresh_json=False):
    """
    This function download the json for the named module if needed.
    """
    if not os.path.isfile(f'./{module_name}.json') or refresh_json:
        response = requests.get(f'{CS_JSN_URL}{module_name}.json')
        with open(f'./{module_name}.json', mode = 'wb') as file:
            file.write(response.content)
    f = f'./{module_name}.json'
    records = json.loads(open(f).read())
    return records

def interpolate_value_for_i(module_json_dic, spec, i_value):
    """
    This function interpolate the value of spec ("I_U" or "I_photon_efficiency")
    # according to intensity (Amper) based on the
    measures provided by the module json dictionary under entry 'spec'
    """
    # Extract x and y values into separate lists
    i_values, u_values = zip(*module_json_dic[spec])

    # Create an interpolation function using scipy's interp1d
    interpolation_function = interp1d(i_values, u_values, kind='linear', fill_value='extrapolate')

    # Interpolate the u value for the desired i value
    u_value = interpolation_function(i_value)
    return u_value

def get_u_for_i(module_json_dic, i_value):
    """
    Each module has its own evolution of tension according to intensity. This
    relation has been measured by Cre.Science and is available in the json file.
    """
    return interpolate_value_for_i(module_json_dic, "I_U", i_value)

def get_ppe_for_i(module_json_dic, i_value):
    """
    Each module has its own evolution of PPE according to intensity. This
    relation has been measured by Cre.Science and is available in the json file.
    """
    return interpolate_value_for_i(module_json_dic, "I_photon_efficiency", i_value)

def get_photon_flux_for_i(module_json_dic, i_value):
    """
    """
    return interpolate_value_for_i(module_json_dic, "I_photon_flux", i_value)

def get_dli_by_m2(data_points_seconds, driver_maximum_intensity, module_json_dic, lit_area, plot=False):
    """
    This function calculates DLI (µmol/m²/day) as = PPE(I)*U(I)*I, integrated
    Throughout the scheduled intensities I.
    """
    # Extract time and dim volt values into separate lists
    t_values, v_values = zip(*data_points_seconds)

    # Calculate intensies I (A) from dim Volt and driver maximum intensity,
    # tension U (V) =f(I) from measured data from the module json,
    # PPE (µmol/J) =f(I) from measured data from the module json,
    # PPF (µmol/s) = PPE*I*U
    i_values = [v/10.0*driver_maximum_intensity/1000 for v in v_values]
    u_values = [get_u_for_i(module_json_dic, i_value) for i_value in i_values]
    ppf_values = [i_values[i]*u_values[j]*get_ppe_for_i(module_json_dic, i_values[i])
                    for i in range(len(i_values))
                    for j in range(len(u_values))
                    if i == j]

    # Calculates DLI by integrating PPF according to schedule using the Trapezoid methodology.
    dli_by_m2 = trapz(ppf_values, t_values)/lit_area
    logging.debug(dli_by_m2)

    if plot:
        # Create subplots for v_values, i_values, u_values, and ppf_values
        fig, axs = plt.subplots(4, 1, figsize=(10, 8))

        # Plot v_values
        axs[0].plot(t_values, v_values, label='v_values')
        axs[0].set_ylabel('v_values')

        # Plot i_values
        axs[1].plot(t_values, i_values, label='i_values')
        axs[1].set_ylabel('i_values')

        # Plot u_values
        axs[2].plot(t_values, u_values, label='u_values')
        axs[2].set_ylabel('u_values')

        # Plot ppf_values
        axs[3].plot(t_values, ppf_values, label='ppf_values')
        axs[3].set_xlabel('t_values')
        axs[3].set_ylabel('ppf_values')

        # Add a common x-axis label
        axs[-1].set_xlabel('t_values')

        # Display legends
        for ax in axs:
            ax.legend()

        plt.tight_layout()
        #plt.show()
        plt.pause(0.5)
        plt.close(fig=fig)

    return dli_by_m2

def get_i_from_u_and_maximum_driver_intensity(v_value, maximum_driver_intensity):
    """
    """
    return maximum_driver_intensity * (v_value / 10.0)

def get_i_from_schedule(schedule, time_in_seconds, maximum_driver_intensity):
    """
    """
    # Extract time in seconds and voltage control of the schedule
    t_values, v_values = zip(*schedule)

    # Create an interpolation function using scipy's interp1d
    interpolation_function = interp1d(t_values, v_values, kind='linear', fill_value=(0.0, 0.0), bounds_error=False)

    # Interpolate the i value for the desired time_in_seconds
    i_value = get_i_from_u_and_maximum_driver_intensity(interpolation_function(time_in_seconds), maximum_driver_intensity)

    return i_value

def get_photon_spectrum(module_json_dic):
    """
    This function extracts only the wavelength and photon part of the spectrum but not the power one.
    """
    photon_spectrum = [(wavelength, photon) for (wavelength, power, photon) in module_json_dic["spectrum_power_photon"]]
    return photon_spectrum

def get_spectrum_for_modules(spectrum, photon_flux, modules_number):
    """
    This function scale up the spectrum photon flux by the photon_flux and number of modules
    """
    spectrum_scaled = scale_data_points_seconds(spectrum, photon_flux*modules_number)
    return spectrum_scaled

def get_spectra_sum(spectra_list):
    """
    This function sum all the spectrum in the list of spectra received
    """
    spectra_sum = [(300,0),]
    for spectrum in spectra_list:
        spectra_sum = sum_data_points_seconds(spectra_sum, spectrum, max_intensity=10000.0)
    return spectra_sum

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
        data_points_hours = create_intensity_data_suntime(maximum_voltage, date=desired_date)[1]
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
    anim = animation.FuncAnimation(fig, update_plot, frames=pd.date_range(start_date, end_date), interval=100, cache_frame_data=False)
    if save_path:
        anim.save(save_path, writer='pillow', fps=10)  # Save the animation to a file
    plt.show()  # Display the animated plot

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
        data_points_seconds, _ = create_intensity_data_suntime(maximum_voltage, date=start_date + datetime.timedelta(days=day))[0:2]
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
    plt.pause(timing)  # Pause briefly to update the plot

def create_plot(schedule_dic, color_dic, timing=5.0):
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
    for label, (schedule, json, driver_maximum_intensity, number_of_modules) in schedule_dic.items():
        photon_schedule = [(time, number_of_modules*get_photon_flux_for_i(json, get_i_from_u_and_maximum_driver_intensity(v_value, driver_maximum_intensity))) for (time, v_value) in schedule]
        # Unpack the time and intensity values
        times, intensities = zip(*photon_schedule)
        # Create a plot and add lines
        ax.plot(times, intensities, label=label, marker='o', linestyle='-', color=color_dic[label])
    current_date        = datetime.date.today()
    sun                 = Sun(LATITUDE, LONGITUDE)
    sunrise_time_Seconds   = 3600 * convert_datetime_to_decimal_hour(sun.get_sunrise_time(current_date) + datetime.timedelta(seconds=3600*TIMEZONE))
    sunset_time_seconds    = 3600 * convert_datetime_to_decimal_hour(sun.get_sunset_time(current_date) + datetime.timedelta(seconds=3600*TIMEZONE))
    solstice_sum_sunrise = 3600 * get_summer_solstice_sunrise()
    solstice_sum_sunset = 3600 * get_summer_solstice_sunset()
    solstice_win_sunrise = 3600 * get_winter_solstice_sunrise()
    solstice_win_sunset = 3600 * get_winter_solstice_sunset()

    sunrise_sunset_ys = (0, maximum_intensity)
    ax.plot((solstice_sum_sunrise, solstice_sum_sunrise), sunrise_sunset_ys, label='Summer Solstice Sunrise', linestyle=':', color='gold')
    ax.plot((sunrise_time_Seconds, sunrise_time_Seconds), sunrise_sunset_ys, label=f'Current Sunrise ({convert_decimal_hour_to_human_hour(sunrise_time_Seconds/3600)})', linestyle='--', color='goldenrod')
    ax.plot((solstice_win_sunrise, solstice_win_sunrise), sunrise_sunset_ys, label='Winter Solstice Sunrise', linestyle=':', color='darkgoldenrod')
    ax.plot((solstice_sum_sunset, solstice_sum_sunset), sunrise_sunset_ys, label='Summer Solstice Sunset', linestyle=':', color='lightcoral')
    ax.plot((sunset_time_seconds, sunset_time_seconds), sunrise_sunset_ys, label=f'Current Sunset ({convert_decimal_hour_to_human_hour(sunset_time_seconds/3600)})', linestyle='--', color='indianred')
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
    ax.set_title('Intensity Comparison')
    ax.grid(True)
    # Add a legend
    legend = ax.legend()
    fig.savefig('./schedules.png')
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

    plt.show()

    #plt.pause(timing)
    #plt.close(fig=fig)

def animate_daily_spectrum(schedule_dic, time_step=300, save_path=None):
    """

    """
    schedules = [[schedule, get_photon_spectrum(json), maximum_driver_intensity, number_of_modules, json] for schedule_name, (schedule, json, maximum_driver_intensity, number_of_modules) in schedule_dic.items()]

    # Define the time range of the day in seconds
    start_time = 0
    end_time = 86400

    # Defines the maximum of intensity for the spectrum
    max_intensity = 5000

    # Create a figure and axis for the plot
    fig, ax = plt.subplots(figsize=(10, 6))

    # Create a color map based on the wavelength values
    def wavelength_to_rgb(wavelength, gamma=0.8):
        ''' taken from http://www.noah.org/wiki/Wavelength_to_RGB_in_Python
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
        spectra_list = []
        for i in range(len(schedules)):
            intensity = get_i_from_schedule(schedules[i][0], time_in_seconds, schedules[i][2])
            photon_flux_for_i = get_photon_flux_for_i(schedules[i][4], intensity)
            spectra_list.append(get_spectrum_for_modules(schedules[i][1],photon_flux_for_i, schedules[i][3]))
        spectra_sum = get_spectra_sum(spectra_list)
        wavelength, intensity = zip(*spectra_sum)

        # Plot spectrum
        ax.plot(wavelength, intensity, linestyle='-', color='darkgray')

        # show color spectrum below spectrum
        plt.imshow(X, clim=clim,  extent=extent, cmap=spectralmap, aspect='auto')

        # Hides color spectrum above spectrum
        ax.fill_between(wavelength, intensity, max_intensity, color='w')

        ax.set_xlim(clim[0],clim[1])
        ax.set_ylim(0.0, max_intensity)
        ax.set_xlabel('Wavelength (nm)')
        ax.set_ylabel('Intensity')
        ax.set_title(f'Spectrum Intensity - {convert_seconds_to_human_hour(time_in_seconds)}')
        ax.grid(True)

    # Create the animation
    anim = animation.FuncAnimation(fig, update_plot, frames=range(start_time, end_time+1, time_step), interval=100, cache_frame_data=False, repeat=False)
    if save_path:
        anim.save(save_path, writer='pillow', fps=10)  # Save the animation to a file
    plt.show()  # Display the animated plot


# ------------------------------------------------------------------------------
