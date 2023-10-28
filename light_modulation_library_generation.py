# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# Author: Gregoire Vandenschrick
# Date:   27/10/2023
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# -- Imports for the generation of data_points
import os
import logging
import light_modulation_library_plot as lmlp
import light_modulation_settings as lmt
from light_modulation_library_plot import plt

import math
from suntime import Sun
import time
import datetime
import numpy as np

from scipy.interpolate import UnivariateSpline, interp1d
from scipy.integrate import trapz, simps, quad

import json
import requests

# ------------------------------------------------------------------------------
# -- local constants definitions.
sun = Sun(lmt.LATITUDE, lmt.LONGITUDE)

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
    Methodology to draw the curve of the schedule, based on
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
    d being maximum_broadness (2.5 - 15)
    e being (-2.05/39.0625)*(d-2)*(d-15)
    All this working to create a broader and broader cosine curve with its feet not moving
    Maximum_broadness = 2.5 gives almost a triangle curve.
    Maximum_broadness = 3 gives a normal cosine curve.
    Values higher broadens the maximum area where intensity = 1.
    Maximum_broadness = 15 gives almost a square wave.
    """
    # Calculate the current time in hours
    current_hour = convert_datetime_to_decimal_hour(current_time)
    earliest_power_on -= transition_duration_minutes/60.0
    latest_power_off += transition_duration_minutes/60.0

    # Calculate the fraction of the day passed
    fraction_of_day = (current_hour - earliest_power_on) / (latest_power_off - earliest_power_on)
    # Calculate a simple intensity using the positive half of the cosine curve
    # from earliest_power_on to latest_power_of
    if 0.0 < fraction_of_day and fraction_of_day < 1.0:
        # Calculate the angle for the cosine curve within the interval from -π/2 to +π/2
        cosine_angle = math.pi * (fraction_of_day - 0.5)
        b = maximum_broadness/3.0
        c = b**maximum_broadness
        e = (-2.05/39.0625)*(maximum_broadness-2)*(maximum_broadness-15)
        a = (1/(b + e))**(1/(4*maximum_broadness))
        #logging.debug(f'angle: {cosine_angle}\nd: {maximum_broadness}\nb: {b}\nc: {c}\ne: {e}\na: {a}')
        intensity = max(0, 1-(math.cos((math.pi/2)*(math.cos(a*cosine_angle)**b))**c))
        #logging.debug(f'Intensity: {intensity}')
    else:
        intensity = 0.0
    return intensity * amplitude_modulation

def get_equinox_sunrise():
    """
    This function gives the hour of sunrise at Equinox, used to evaluate the
    difference between it and sunrise time of the current day.
    Time is given according to timezone (default = 2).
    The 22th of March of the current year is used, rather roughly...
    """
    global sun
    timezone_hours = datetime.timedelta(seconds=3600*lmt.TIMEZONE)
    equinox_sunrise_time = sun.get_sunrise_time(date=datetime.date(datetime.date.today().year,3,22)) + timezone_hours
    return convert_datetime_to_decimal_hour(equinox_sunrise_time)

def get_equinox_sunset():
    """
    This function gives the hour of sunset at Equinox, used to evaluate the
    difference between it and sunset time of the current day.
    Time is given according to timezone (default = 2).
    The 22th of March of the current year is used, rather roughly...
    """
    global sun
    timezone_hours = datetime.timedelta(seconds=3600*lmt.TIMEZONE)
    equinox_sunset_time = sun.get_sunset_time(date=datetime.date(datetime.date.today().year,3,22)) + timezone_hours
    return convert_datetime_to_decimal_hour(equinox_sunset_time)

def get_summer_solstice_sunrise():
    """
    This function gives the hour of Summer Solstice, used to evaluate the
    difference between it and sunrise time of the current day.
    Time is given according to timezone (default = 2).
    The 22th of June of the current year is used, rather roughly...
    """
    global sun
    timezone_hours = datetime.timedelta(seconds=3600*lmt.TIMEZONE)
    equinox_sunrise_time = sun.get_sunrise_time(date=datetime.date(datetime.date.today().year,6,22)) + timezone_hours
    return convert_datetime_to_decimal_hour(equinox_sunrise_time)

def get_summer_solstice_sunset():
    """
    This function gives the hour of sunset at Summer Solstice, used to evaluate the
    difference between it and sunset time of the current day.
    Time is given according to timezone (default = 2).
    The 22th of June of the current year is used, rather roughly...
    """
    global sun
    timezone_hours = datetime.timedelta(seconds=3600*lmt.TIMEZONE)
    equinox_sunset_time = sun.get_sunset_time(date=datetime.date(datetime.date.today().year,6,22)) + timezone_hours
    return convert_datetime_to_decimal_hour(equinox_sunset_time)

def get_winter_solstice_sunrise():
    """
    This function gives the hour of Winter Solstice, used to evaluate the
    difference between it and sunrise time of the current day.
    Time is given according to timezone (default = 2).
    The 22th of December of the current year is used, rather roughly...
    """
    global sun
    timezone_hours = datetime.timedelta(seconds=3600*lmt.TIMEZONE)
    equinox_sunrise_time = sun.get_sunrise_time(date=datetime.date(datetime.date.today().year,12,22)) + timezone_hours
    return convert_datetime_to_decimal_hour(equinox_sunrise_time)

def get_winter_solstice_sunset():
    """
    This function gives the hour of sunset at Winter Solstice, used to evaluate the
    difference between it and sunset time of the current day.
    Time is given according to timezone (default = 2).
    The 22th of December of the current year is used, rather roughly...
    """
    global sun
    timezone_hours = datetime.timedelta(seconds=3600*lmt.TIMEZONE)
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

def get_modulated_max_intensity(current_date, earliest_power_on, latest_power_off, amplitude_modulation=0.9):
    """
    New methodology to calculate amplitude modulation based on current day length
    compared to the longest day of the year (namely the Summer Solstice day).
    """
    day_length = latest_power_off - earliest_power_on
    summer_solstice_day_length = get_summer_solstice_sunset() - get_summer_solstice_sunrise()
    winter_solstice_day_length = get_winter_solstice_sunset() - get_winter_solstice_sunrise()
    # This goes from 0 at the winter solstice to 1 at the summer solstice
    reduction_proportion = (day_length - winter_solstice_day_length) / (summer_solstice_day_length - winter_solstice_day_length)
    logging.debug(f'reduction proportion of maximum intensity: {reduction_proportion}')
    modulated_max_intensity = amplitude_modulation + (1.0 - amplitude_modulation) * reduction_proportion
    logging.debug(f'Modulated maximum intensity: {modulated_max_intensity}')
    return modulated_max_intensity

def calculate_Schedule(current_date, earliest_power_on, latest_power_off, modulated_max_intensity, maximum_broadness=2.5, transition_duration_minutes=0):
    """
    """
    # Calculates all tuples (time_in_second, intensity) for the current day
    current_datetime    = datetime.datetime(current_date.year, current_date.month, current_date.day, 0, 0)  # Start at midnight
    time_step           = datetime.timedelta(minutes=lmt.TIME_STEP_MINUTES) # Adjustable time step
    data_points_seconds = []                                            # Data points with time in seconds
    data_points_hours   = []                                            # Data points with time in hours
    max_iterations      = 24 * 60 // lmt.TIME_STEP_MINUTES                  # Maximum number of iterations (1 day)
    iterations          = 0                                             # Counter for iterations
    while iterations < max_iterations:
        intensity=0
        intensity = calculate_intensity_2(current_datetime, earliest_power_on, latest_power_off, modulated_max_intensity, maximum_broadness=maximum_broadness, transition_duration_minutes=transition_duration_minutes)
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

def create_intensity_data_suntime(maximum_voltage, mode="centered", length_proportion=1.0, shift_proportion=0.0, date=None, maximum_broadness=3, transition_duration_minutes=0, plot=False):
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
    global sun
    earliest_power_on   = convert_datetime_to_decimal_hour(sun.get_sunrise_time(current_date) + datetime.timedelta(seconds=3600*lmt.TIMEZONE))
    latest_power_off    = convert_datetime_to_decimal_hour(sun.get_sunset_time(current_date) + datetime.timedelta(seconds=3600*lmt.TIMEZONE))
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
        lmlp.plot_data_on_ax(data_points_seconds, ax, title="Data points before scaling", timing=2)
    else:
        ax = None
    scaled_data_points_seconds = [(time, intensity*scale_factor) for time, intensity in data_points_seconds]
    if ax:
        lmlp.plot_data_on_ax(scaled_data_points_seconds, ax, title=f"Data points after scaling at {scale_factor}", timing=2)
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
    ! Assuming data_points_seconds_1 and padded_data_points_seconds_2 have the same time intervals and time values
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
        lmlp.plot_data_on_ax(data_points_seconds, ax, title="Data points before gated", timing=2)
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
        lmlp.plot_data_on_ax(gated_data_points_seconds, ax, title="Data points after gated", timing=2)
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
        lmlp.plot_data_on_ax(data_points_intensities, ax)
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
        lmlp.plot_data_on_ax(filtered_result, ax)
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
        lmlp.plot_data_on_ax(filtered_result, ax, title="Reduction of number of data points")
        (times, intensities) = zip(*filtered_result)
    return filtered_result

def clean_and_simplify_to_desired_points(data_points_seconds, desired_num_points=32, plot=False):
    """
    The function combines both precent ones, trying to save a maximum of information
    while trimming down the schedule to 32 points such as allowed by the Crescontrol
    Because the suppression of intermediate zeros drops points, if applied directly
    on a trimmed down to 32 points, schedules contain always less than 32 points.
    here we decrease incrementally the number of points in schedule, drop unnecessary
    zeros and repeat the operation until the result contains 32 points after zeros
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
    data_string = "[" + ",".join([f"[{(int(time)):.{decimal_places}f},{min(max(minimum_intensity,intensity),maximum_intensity):.{decimal_places}f}]" for time, intensity in data_points_seconds]) + "]"
    return data_string

def stringify_schedules_in_dic(schedule_dic):
    """
    Stringify all schedules in dictionary
    """
    stringified_schedules_dic = {}
    for (key, (schedule, out_name, meta)) in schedule_dic.items():
        stringified_schedules_dic[key] = (convert_data_points_to_string(schedule), out_name, meta)
    return stringified_schedules_dic

# --- Other functions that deal with the parameters of modules -----------------

def get_json_file(json_name):
    f = f'./{json_name}.json'
    records = json.loads(open(f).read())
    return records

def get_module_json(module_name, refresh_json=False):
    """
    This function download the json for the named module if needed.
    """
    if not os.path.isfile(f'./{module_name}.json') or refresh_json:
        response = requests.get(f'{lmt.CS_JSN_URL}{module_name}.json')
        with open(f'./{module_name}.json', mode = 'wb') as file:
            file.write(response.content)
    return get_json_file(module_name)

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

def get_optical_power_for_i(module_json_dic, i_value):
    """
    """
    return interpolate_value_for_i(module_json_dic, "I_optical_power", i_value)

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

# ------------------------------------------------------------------------------
