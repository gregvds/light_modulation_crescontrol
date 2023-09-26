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

def generate_3500K_schedule(schedule_name, driver_maximum_intensity, maximum_intensity_required):
    """
    Generate a curve for 3500k for dawn and dusk by summing two different schedules
    One can pass to the generating functions the proportion of dawn and dusk
    vs the length of the current day; by default = 0.25.
    """
    # Parameters (you can adjust these)
    maximum_voltage = 10 * (maximum_intensity_required/driver_maximum_intensity)  # Maximum voltage (adjustable, 0-10V)
    transition_duration_minutes = 90  # Duration of smooth transitions at the begin and end (x minutes)

    # A first curve is generated for dawn, of a duration of 25% of the current day duration
    (data_points_seconds_first,
    junk,
    daily_earliest_power_on,
    junk,
    daily_maximum_intensity) = lml.create_intensity_data_suntime(maximum_voltage,
                                                                 mode="dawn",
                                                                 length_proportion=0.25,
                                                                 transition_duration_minutes=transition_duration_minutes)

    # We save back the schedule name and the modulated begin and max intensity
    schedule_3500_dic = {
        'schedule_name': schedule_name,
        'earliest_power_on': lml.get_equinox_sunrise(),
        'daily_earliest_power_on': daily_earliest_power_on,
        'daily_maximum_intensity': daily_maximum_intensity
    }

    # A second curve is generated for dusk, of a duration of 30% of the current day duration
    (data_points_seconds_second,
    junk,
    junk,
    daily_latest_power_off,
    junk) = lml.create_intensity_data_suntime(maximum_voltage,
                                              mode='dusk',
                                              length_proportion=0.3,
                                              transition_duration_minutes=transition_duration_minutes)

    # the two curves for dawn and dusk schedules are added
    data_points_seconds = lml.sum_data_points_seconds(data_points_seconds_first,
                                                      data_points_seconds_second)

    # We save back the data and the modulated end
    schedule_3500_dic['full_schedule'] = data_points_seconds
    schedule_3500_dic['latest_power_off'] = lml.get_equinox_sunset()
    schedule_3500_dic['daily_latest_power_off'] = daily_latest_power_off
    schedule_3500_dic['transition_duration_minutes'] = transition_duration_minutes
    schedule_3500_dic['maximum_voltage'] = maximum_voltage
    return schedule_3500_dic

def generate_5000K_schedule(schedule_name, driver_maximum_intensity, maximum_intensity_required):
    """
    Generate total envelope curve for 5000k
    """
    # Parameters (you can adjust these)
    maximum_voltage = 10 * (maximum_intensity_required/driver_maximum_intensity)  # Maximum voltage (adjustable, 0-10V)
    transition_duration_minutes = 60  # Duration of smooth transitions at the begin and end (x minutes)

    # A simple curve is generated for day, of a duration of 95% of the current day duration
    (data_points_seconds,
    junk,
    daily_earliest_power_on,
    daily_latest_power_off,
    daily_maximum_intensity) = lml.create_intensity_data_suntime(maximum_voltage,
                                                                 curve_mode="cos2",
                                                                 length_proportion=0.90,
                                                                 transition_duration_minutes=transition_duration_minutes)

    # We save back the data and the modulated begin, end and max intensity
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

def generate_385_schedule(schedule_name, driver_maximum_intensity, maximum_intensity_required):
    """
    Generate total envelope curve for 385nm
    """
    # Parameters (you can adjust these)
    maximum_voltage = 10 * (maximum_intensity_required/driver_maximum_intensity)  # Maximum voltage (adjustable, 0-10V)
    transition_duration_minutes = 40  # Duration of smooth transitions at the begin and end (x minutes)

    # A simple curve is generated centered on midday, of a duration of 70% of the current day duration
    (data_points_seconds,
    junk,
    daily_earliest_power_on,
    daily_latest_power_off,
    daily_maximum_intensity) = lml.create_intensity_data_suntime(maximum_voltage,
                                                                 curve_mode="cos3",
                                                                 length_proportion=0.7,
                                                                 transition_duration_minutes=transition_duration_minutes)

    # We save back the data and the modulated begin, end and max intensity
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

def generate_schedules(debug=False):
    """
    Here we define the maximum intensity the schedules should produce according to
    the capability of the drivers used.
    6 FLUXengines 3500K in serie are driven by an XLG-150-L set at 600mA (lower than max to deliver lower light to better approach dawn and dusk light).
    6 FLUXengines 5000K in serie are driven by an XLG-150-L set at 1050mA (max).
    5 APEXengines 385nm in serie are driven by an LCM-40 set at 600mA.
    You can adapt these settings according to your need and chains.
    The XLG-150-L requires at least 0.79V to generate modulated current.
    The LCM-40    requires at least 0.75V to generate modulated current.
    These voltage were derived from testing and could be different from driver to driver.
    They are needed to produce schedule values that are effectively generating light output.
    """

    # --------------------------------------------------------------------------
    # Generation of schedule for FLUXengines 3500K
    driver_maximum_intensity_3500K   = 1050                                      # This is the maximum Amper your led driver can produce
    driver_minimal_voltage_for_light_3500K = 0.79                               # This is the minimal voltage dim signal the driver reacts to
    maximum_intensity_required_3500K = driver_maximum_intensity_3500K*(5.0/10.5) # This is the maximum Amper you want the driver to deliver during the schedule
    schedule_3500_dic = generate_3500K_schedule("schedule_3500", driver_maximum_intensity_3500K, maximum_intensity_required_3500K)
    # Gating the data so the lowest values produce already light.
    # Depending on your led array and driver, you should adjust this
    data_points_seconds_3500 = lml.gate_data_points_seconds(schedule_3500_dic['full_schedule'], lower_gate=driver_minimal_voltage_for_light_3500K)
    # The result is cleaned from redundant values and trimmed down to 32 values
    schedule_3500 = lml.clean_and_simplify_to_desired_points(data_points_seconds_3500, plot = PLOT)


    # --------------------------------------------------------------------------
    # Generation of schedule for FLUXengines 5000K
    driver_maximum_intensity_5000K   = 1050                                     # This is the maximum Amper your led driver can produce
    driver_minimal_voltage_for_light_5000K = 0.79                               # This is the minimal voltage dim signal the driver reacts to
    maximum_intensity_required_5000K = driver_maximum_intensity_5000K*1         # This is the maximum Amper you want the driver to deliver during the schedule
    schedule_5000_dic = generate_5000K_schedule("schedule_5000", driver_maximum_intensity_5000K, maximum_intensity_required_5000K)
    # Remove light from 5000K that is already given by 3500K
    # (hence the scaling! and the need to know relative drivers maximum intensity settings).
    data_points_seconds_5000 = lml.substract_data_points_seconds(schedule_5000_dic['full_schedule'],
                                                                 lml.scale_data_points_seconds(schedule_3500_dic['full_schedule'],
                                                                                               (maximum_intensity_required_3500K/maximum_intensity_required_5000K)))
    # Gating the data so the lowest values produce already light.
    # Depending on your led array and driver, you should adjust this
    data_points_seconds_5000 = lml.gate_data_points_seconds(data_points_seconds_5000, lower_gate=driver_minimal_voltage_for_light_5000K)
    # The result is cleaned from redundant values and trimmed down to 32 values
    schedule_5000 = lml.clean_and_simplify_to_desired_points(data_points_seconds_5000, plot = PLOT)


    # --------------------------------------------------------------------------
    # Generation of schedule for APEXengines 385
    driver_maximum_intensity_385   = 600                                        # This is the maximum Amper your led driver can produce
    driver_minimal_voltage_for_light_385 = 0.75                                 # This is the minimal voltage dim signal the driver reacts to
    maximum_intensity_required_385 = driver_maximum_intensity_385*0.35          # This is the maximum Amper you want the driver to deliver during the schedule
    schedule_385_dic = generate_385_schedule("schedule_385", driver_maximum_intensity_385, maximum_intensity_required_385)
    # Gating the data so the lowest values produce already light.
    # Depending on your led array and driver, you should adjust this
    data_points_seconds_385 = lml.gate_data_points_seconds(schedule_385_dic['full_schedule'], lower_gate=driver_minimal_voltage_for_light_385)
    # The result is cleaned from redundant values and trimmed down to 32 values
    schedule_385 = lml.clean_and_simplify_to_desired_points(data_points_seconds_385, plot = PLOT)

    # --------------------------------------------------------------------------
    # packing of all the schedules generated in a dictionary.
    # !! Key values ARE THE NAMES OF THE SCHEDULES DEFINED IN THE CRESCONTROL !!
    # !! Second element in tuple is the out name for the schedule to modulate !!
    schedule_dic = {
        "schedule_3500" : (schedule_3500, "out-a"),
        "schedule_5000" : (schedule_5000, "out-b"),
        "schedule_385"  : (schedule_385,  "out-c")
    }

    if debug is True:
        lml.create_triple_plot(schedule_dic["schedule_3500"][0],
                               schedule_dic["schedule_5000"][0],
                               schedule_dic["schedule_385"][0])

    # Shedules need to be passed as string to the Crescontrol.
    schedule_dic = lml.stringify_schedules_in_dic(schedule_dic)

    # --------------------------------------------------------------------------
    # generate a report of schedules generated to be sent by email (or simply printed)
    schedules_dic_list = [schedule_3500_dic, schedule_5000_dic, schedule_385_dic]
    result_for_mail = generate_result_for_email(schedules_dic_list)

    # --------------------------------------------------------------------------
    # get the json files for the modules
    json_3500 = lml.get_module_json("fluxengine_3500k")
    json_5000 = lml.get_module_json("fluxengine_5000k")
    json_385  = lml.get_module_json("apexengine_385")

    dli_3500 = 6*lml.get_dli_by_m2(schedule_3500, driver_maximum_intensity_3500K, json_3500)/1000000
    dli_5000 = 6*lml.get_dli_by_m2(schedule_5000, driver_maximum_intensity_5000K, json_5000)/1000000
    dli_385  = 5*lml.get_dli_by_m2(schedule_385,  driver_maximum_intensity_385,   json_385) /1000000

    print(f'{dli_3500:6.3f} mol/m²/day of photon delivered by 6 FLUXengines 3500K')
    print(f'{dli_5000:6.3f} mol/m²/day of photon delivered by 6 FLUXengines 5000K')
    print(f'{dli_385:6.3f} mol/m²/day of photon delivered by 5 APEXengines 385')

    return schedule_dic, result_for_mail

# ------------------------------------------------------------------------------
