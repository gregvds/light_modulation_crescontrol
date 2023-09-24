# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# Author: Gregoire Vandenschrick
# Date:   20/09/2023
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

# -- Import for the generation of data_points and communications
import light_modulation_library as lml
import os

# ------------------------------------------------------------------------------

PLOT = False

# ------------------------------------------------------------------------------
# -- Generation of schedules ---------------------------------------------------
"""
    Here we will generate the schedule(s) that are to be modulated according to
    the day in the year. Each schedule is basically the positive half part of a
    cosine curve, set to begin at a given time and end at another and reach a
    given maximum. begin and end are computed from the latitude-longitude given
    in the light_modulation_settings.py file. Maximum is reached at the Summer
    solstice, minimum at the Winter solstice. A small transition period at begin
    and end is added according to a given duration to mimic dawn and dusk twilights.

    Here we define three schedules, one being produced by adding one to
    another, to achieve light lit only at the begin and end of the day, to
    modulate the spectrum, again to mimic dawn and dusk light composition.

    For easier reading, we encapsulate all this in function generate_schedules().
"""

def generate_3500K_schedule(schedule_name):
    """
    Generate a curve for 3500k for dawn and dusk by summing two different schedules
    One can pass to the generating functions the proportion of dawn and dusk
    vs the length of the current day; by default = 0.25.
    """
    # Parameters (you can adjust these)
    maximum_voltage = 4  # Maximum voltage (adjustable, 0-10V)
    transition_duration_minutes = 90  # Duration of smooth transitions at the begin and end (x minutes)

    # We save back the data and the modulated begin and max intensity
    (data_points_seconds_first,
    junk,
    daily_earliest_power_on,
    junk,
    daily_maximum_intensity) = lml.create_intensity_data_suntime(maximum_voltage,
                                                                 mode="dawn",
                                                                 length_proportion=0.25,
                                                                 transition_duration_minutes=transition_duration_minutes)

    schedule_3500_dic = {
        'schedule_name': schedule_name,
        'earliest_power_on': lml.get_equinox_sunrise(),
        'daily_earliest_power_on': daily_earliest_power_on,
        'daily_maximum_intensity': daily_maximum_intensity
    }

    # We save back the data and the modulated end
    (data_points_seconds_second,
    junk,
    junk,
    daily_latest_power_off,
    junk) = lml.create_intensity_data_suntime(maximum_voltage,
                                              mode='dusk',
                                              length_proportion=0.25,
                                              transition_duration_minutes=transition_duration_minutes)

    # sum dawn and dusk schedules
    data_points_seconds = lml.sum_data_points_seconds(data_points_seconds_first,
                                                      data_points_seconds_second)

    schedule_3500_dic['full_schedule'] = data_points_seconds
    schedule_3500_dic['latest_power_off'] = lml.get_equinox_sunset()
    schedule_3500_dic['daily_latest_power_off'] = daily_latest_power_off
    schedule_3500_dic['transition_duration_minutes'] = transition_duration_minutes
    schedule_3500_dic['maximum_voltage'] = maximum_voltage
    return schedule_3500_dic

def generate_5000K_schedule(schedule_name):
    """
    Generate total envelope curve for 5000k
    """
    # Parameters (you can adjust these)
    maximum_voltage = 10  # Maximum voltage (adjustable, 0-10V)
    transition_duration_minutes = 60  # Duration of smooth transitions at the begin and end (x minutes)

    # We save back the data and the modulated begin, end and max intensity
    (data_points_seconds,
    junk,
    daily_earliest_power_on,
    daily_latest_power_off,
    daily_maximum_intensity) = lml.create_intensity_data_suntime(maximum_voltage,
                                                                 transition_duration_minutes=transition_duration_minutes)

    schedule_5000_dic = {
        'schedule_name': schedule_name,
        'full_schedule': data_points_seconds,
        'earliest_power_on': lml.get_equinox_sunrise(),
        'daily_earliest_power_on': daily_earliest_power_on,
        'latest_power_off': lml.get_equinox_sunset(),
        'daily_latest_power_off': daily_latest_power_off,
        'transition_duration_minutes': transition_duration_minutes,
        'maximum_voltage': maximum_voltage,
        'daily_maximum_intensity': daily_maximum_intensity
    }
    return schedule_5000_dic

def generate_385_schedule(schedule_name):
    """
    Generate total envelope curve for 385nm
    """
    # Parameters (you can adjust these)
    maximum_voltage = 3  # Maximum voltage (adjustable, 0-10V)
    transition_duration_minutes = 40  # Duration of smooth transitions at the begin and end (x minutes)

    (data_points_seconds,
    junk,
    daily_earliest_power_on,
    daily_latest_power_off,
    daily_maximum_intensity) = lml.create_intensity_data_suntime(maximum_voltage,
                                                                 length_proportion=0.6,
                                                                 transition_duration_minutes=transition_duration_minutes)

    schedule_385_dic = {
        'schedule_name': schedule_name,
        'full_schedule': data_points_seconds,
        'earliest_power_on': lml.get_equinox_sunrise(),
        'daily_earliest_power_on': daily_earliest_power_on,
        'latest_power_off': lml.get_equinox_sunset(),
        'daily_latest_power_off': daily_latest_power_off,
        'transition_duration_minutes': transition_duration_minutes,
        'maximum_voltage': maximum_voltage,
        'daily_maximum_intensity': daily_maximum_intensity
    }
    return schedule_385_dic

def generate_result_for_email(schedule_dic_list):
    result_for_mail = '\
Daily report of led lights schedules modulation\n\
--------------------------------------------------------------------------------\n\
Current day and time on %s: %s\n\
--------------------------------------------------------------------------------\n\
' % (f'{lml.get_local_ip()}',
     f'{lml.datetime.datetime.now():%d %b %Y - %H:%M:%S}')
    for schedule_dic in schedule_dic_list:
        result_for_mail += '\
Schedule for %s\n\
    begin: %s  (time modulation: %s)\n\
    end:   %s  (time modulation: %s)\n\
    max:   %sV (int. modulation:  %s%%)\n\n\
' % (schedule_dic['schedule_name'],
     "%02dh%02d" % (schedule_dic['daily_earliest_power_on'], (schedule_dic['daily_earliest_power_on']*60)%60),
     lml.format_time_modulation_delta(schedule_dic['daily_earliest_power_on'], schedule_dic['earliest_power_on'], "%02dh%02dm"),
     "%02dh%02d" % (schedule_dic['daily_latest_power_off'], (schedule_dic['daily_latest_power_off']*60)%60),
     lml.format_time_modulation_delta(schedule_dic['daily_latest_power_off'], schedule_dic['latest_power_off'], "%02dh%02dm"),
     "%05.2f" % (schedule_dic['maximum_voltage']*schedule_dic['daily_maximum_intensity']),
     "%02.2f" % ((schedule_dic['daily_maximum_intensity'])*100.0))
    result_for_mail += '\
--------------------------------------------------------------------------------\n\n'

    return result_for_mail

def generate_schedules():

    schedule_3500_dic = generate_3500K_schedule("schedule_3500")
    # The result is cleaned from redundant zero values and trimmed down to 32 values
    schedule_3500 = lml.clean_and_simplify_to_desired_points(schedule_3500_dic['full_schedule'], plot = PLOT)

    schedule_5000_dic = generate_5000K_schedule("schedule_5000")
    # Remove intensities of 5000K that are already given by 3500K
    data_points_seconds_5000 = lml.substract_data_points_seconds(schedule_5000_dic['full_schedule'], schedule_3500_dic['full_schedule'])
    # The result is cleaned from redundant zero values and trimmed down to 32 values
    schedule_5000 = lml.clean_and_simplify_to_desired_points(data_points_seconds_5000, plot = PLOT)

    schedule_385_dic = generate_385_schedule("schedule_385")
    # The result is cleaned from redundant zero values and trimmed down to 32 values
    schedule_385 = lml.clean_and_simplify_to_desired_points(schedule_385_dic['full_schedule'], plot = PLOT)

    # --------------------------------------------------------------------------
    # packing of all the schedules generated in a dictionary.
    # Key values ARE THE NAMES OF THE SCHEDULES DEFINED IN THE CRESCONTROL!
    schedule_dic = {
        "schedule_3500" : schedule_3500,
        "schedule_5000" : schedule_5000,
        "schedule_385"  : schedule_385
    }

    # --------------------------------------------------------------------------
    # generate a report of schedules generated to be sent by email (or simply printed)
    schedules_dic_list = [schedule_3500_dic, schedule_5000_dic, schedule_385_dic]
    result_for_mail = generate_result_for_email(schedules_dic_list)

    return schedule_dic, result_for_mail

# ------------------------------------------------------------------------------
