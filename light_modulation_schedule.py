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
import logging

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

def generate_3500K_schedule(date, schedule_name, driver_maximum_intensity, maximum_intensity_required):
    """
    Generate a curve for 3500k for dawn and dusk by summing two different schedules
    One can pass to the generating functions the proportion of dawn and dusk
    vs the length of the current day; by default = 0.25.
    """
    # Parameters (you can adjust these)
    maximum_voltage = 10 * (maximum_intensity_required/driver_maximum_intensity)  # Maximum voltage (adjustable, 0-10V)
    transition_duration_minutes = 45  # Duration of smooth transitions at the begin and end (x minutes)

    # A first curve is generated for dawn, of a duration of 25% of the current day duration
    (data_points_seconds_first,
    junk,
    daily_earliest_power_on,
    junk,
    daily_maximum_intensity) = lml.create_intensity_data_suntime(maximum_voltage,
                                                                 date=date,
                                                                 mode="dawn",
                                                                 length_proportion=0.23,
                                                                 shift_proportion=0.04,
                                                                 transition_duration_minutes=transition_duration_minutes,
                                                                 maximum_broadness = 3,
                                                                 plot=PLOT)

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
    junk) = lml.create_intensity_data_suntime(maximum_voltage*0.95,
                                              date=date,
                                              mode='dusk',
                                              length_proportion=0.25,
                                              shift_proportion=-0.04,
                                              transition_duration_minutes=transition_duration_minutes,
                                              maximum_broadness = 4,
                                              plot=PLOT)

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

def generate_5000K_schedule(date, schedule_name, driver_maximum_intensity, maximum_intensity_required):
    """
    Generate total envelope curve for 5000k
    """
    # Parameters (you can adjust these)
    maximum_voltage = 10 * (maximum_intensity_required/driver_maximum_intensity)  # Maximum voltage (adjustable, 0-10V)
    transition_duration_minutes = 0  # Duration of smooth transitions at the begin and end (x minutes)

    # A simple curve is generated for day, of a duration of 95% of the current day duration
    (data_points_seconds,
    junk,
    daily_earliest_power_on,
    daily_latest_power_off,
    daily_maximum_intensity) = lml.create_intensity_data_suntime(maximum_voltage,
                                                                 date=date,
                                                                 length_proportion=1.055,
                                                                 shift_proportion=0.0,
                                                                 transition_duration_minutes=transition_duration_minutes,
                                                                 maximum_broadness = 5,
                                                                 plot=PLOT)

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

def generate_385_schedule(date, schedule_name, driver_maximum_intensity, maximum_intensity_required):
    """
    Generate total envelope curve for 385nm
    """
    # Parameters (you can adjust these)
    maximum_voltage = 10 * (maximum_intensity_required/driver_maximum_intensity)  # Maximum voltage (adjustable, 0-10V)
    transition_duration_minutes = 0

    # A simple curve is generated centered on midday, of a duration of 70% of the current day duration
    (data_points_seconds,
    junk,
    daily_earliest_power_on,
    daily_latest_power_off,
    daily_maximum_intensity) = lml.create_intensity_data_suntime(maximum_voltage,
                                                                 date=date,
                                                                 length_proportion=0.85,
                                                                 shift_proportion=0.0,
                                                                 transition_duration_minutes=transition_duration_minutes,
                                                                 maximum_broadness = 5,
                                                                 plot=PLOT)

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

def generate_660_schedule(date, schedule_name, driver_maximum_intensity, maximum_intensity_required):
    """
    Generate a curve for 660nm for dawn and dusk by summing two different schedules
    One can pass to the generating functions the proportion of dawn and dusk
    vs the length of the current day; by default = 0.10.
    """
    # Parameters (you can adjust these)
    maximum_voltage = 10 * (maximum_intensity_required/driver_maximum_intensity)  # Maximum voltage (adjustable, 0-10V)
    transition_duration_minutes = 60  # Duration of smooth transitions at the begin and end (x minutes)

    # A first curve is generated for dawn, of a duration of 25% of the current day duration
    (data_points_seconds_first,
    junk,
    daily_earliest_power_on,
    junk,
    daily_maximum_intensity) = lml.create_intensity_data_suntime(maximum_voltage*0.8,
                                                                 date=date,
                                                                 mode="dawn",
                                                                 length_proportion=0.10,
                                                                 shift_proportion=0.05,
                                                                 transition_duration_minutes=transition_duration_minutes,
                                                                 maximum_broadness = 3,
                                                                 plot=PLOT)

    # A second curve is generated for dusk, of a duration of 30% of the current day duration
    (data_points_seconds_second,
    junk,
    junk,
    daily_latest_power_off,
    junk) = lml.create_intensity_data_suntime(maximum_voltage,
                                              date=date,
                                              mode='dusk',
                                              length_proportion=0.15,
                                              shift_proportion=-0.07,
                                              transition_duration_minutes=transition_duration_minutes,
                                              maximum_broadness = 3,
                                              plot=PLOT)

    # the two curves for dawn and dusk schedules are added
    data_points_seconds = lml.sum_data_points_seconds(data_points_seconds_first,
                                                      data_points_seconds_second)


    # We save back the data and the modulated begin, end and max intensity
    schedule_660_dic = {
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
    return schedule_660_dic

def generate_result_for_email(schedule_dic_list, complementary_text=""):
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
--------------------------------------------------------------------------------\n'
    result_for_mail += complementary_text
    return result_for_mail

def generate_dli_details(schedules_dic_to_treat, out_schedule_dic):
    """
    """
    lit_area = 0.4 #m²
    loss_factor = 0.8 #%
    total_dli = 0
    dli_details = f'\
DLI for the schedules calculated based on modules numbers, \n\
characteristics and driver settings for a lit area of {lit_area}m² \n\
and a loss factor of {((1.0-loss_factor)*100):2.0f}% \n\
--------------------------------------------------------------------------------\n'

    for schedule_name, schedule_dic in schedules_dic_to_treat.items():
        # get the json files for the modules
        json = lml.get_module_json(schedule_dic["json"])
        number_of_modules_in_serie = schedule_dic["number_of_modules_in_serie"]
        schedule = out_schedule_dic[schedule_name][0]
        driver_maximum_intensity = schedule_dic["driver_maximum_intensity"]
        dli = loss_factor*number_of_modules_in_serie*lml.get_dli_by_m2(schedule, driver_maximum_intensity, json, lit_area)/1000000
        total_dli += dli
        dli_details += f'\
{dli:6.3f} mol/m²/day of photon delivered by {number_of_modules_in_serie} {schedule_dic["json"]} on a driver set at {driver_maximum_intensity:4.0f}mA.\n'
    dli_details += f'\
{total_dli:6.3f} mol/m²/day of photon delivered in total.\n\
--------------------------------------------------------------------------------\n'
    return dli_details

def generate_meta(schedule_dic):
    """
    """
    meta = schedule_dic["out"] +\
           ':meta="{\\"unit\\":\\"A\\",\\"module\\":{\\"driver\\":{\\"configuration\\":[' +\
           f'{schedule_dic["number_of_modules_in_serie"]:1d},1],\\"id\\":\\"' +\
           f'{schedule_dic["driver"]}' + '\\"},\\"id\\":\\"' +\
           f'{schedule_dic["module"]}' + '\\"},\\"type\\":\\"light\\",\\"icon\\":\\"' +\
           f'{schedule_dic["module_type"]}' + '\\",\\"id\\":\\"' +\
           f'{schedule_dic["module"]}' + '\\",\\"name\\":\\"' +\
           f'{schedule_dic["eco_module_name"]}' +\
           f'\\",\\"ecos\\":[\\"Lithops\\"],\\"curr\\":{(schedule_dic["driver_maximum_intensity"]/1000):0.2f}' + '}"'
    return meta

def generate_schedule(date, schedules_dic, schedule_name, debug=False):
    """
    """
    schedule_dic = schedules_dic[schedule_name]
    if "composed" in schedule_dic.keys():
        print(f'Composed...')
        # if the schedule is a composition of schedules
        schedule = generate_composed_schedule(date, schedules_dic, schedule_name, debug=debug)
        print(f'Composed {schedule_name} finished')
    else:
        print(f'Simple...')
        # We generate a simple schedule
        schedule = generate_simple_schedule(date, schedules_dic, schedule_name, debug=debug)
        print(f'Simple {schedule_name} finished')
    return schedule

def generate_simple_schedule(date, schedules_dic, schedule_name, debug=False):
    """
    """
    schedule_dic = schedules_dic[schedule_name]
    maximum_voltage = 10 * schedule_dic["maximum_intensity_required"] * schedule_dic["maximum_voltage_proportion"]

    (data_points_seconds,
    junk,
    daily_earliest_power_on,
    daily_latest_power_off,
    daily_maximum_intensity) = lml.create_intensity_data_suntime(maximum_voltage,
                                                                 date=date,
                                                                 mode=schedule_dic["mode"],
                                                                 length_proportion=schedule_dic["length_proportion"],
                                                                 shift_proportion=schedule_dic["shift_proportion"],
                                                                 transition_duration_minutes=schedule_dic["transition_duration_minutes"],
                                                                 maximum_broadness=schedule_dic["maximum_broadness"],
                                                                 plot=PLOT)
    schedule_dic = {
        'schedule_name': schedule_name,
        'full_schedule': data_points_seconds,
        'earliest_power_on': lml.get_equinox_sunrise(),
        'daily_earliest_power_on': daily_earliest_power_on,
        'latest_power_off': lml.get_equinox_sunset(),
        'daily_latest_power_off': daily_latest_power_off,
        'transition_duration_minutes': schedule_dic["transition_duration_minutes"],
        'maximum_voltage': maximum_voltage,
        'daily_maximum_intensity': daily_maximum_intensity
    }
    return schedule_dic

def generate_composed_schedule(date, schedules_dic, schedule_name, debug=False):
    """
    """
    schedule_dic = schedules_dic[schedule_name]
    schedules = []
    ponderation_factors = []
    for schedule_name_in_list in schedule_dic["composed"]["list"]:
        # recursive call to generate the schedules required to compose the schedule
        #if isinstance(schedule_name_in_list, dict):

        schedules.append(generate_schedules_new(date, schedules_dic, schedule_name=schedule_name_in_list, debug=debug))
        ponderation_factors.append(schedules_dic[schedule_name_in_list]["maximum_intensity_required"] * schedules_dic[schedule_name_in_list]["driver_maximum_intensity"])
    if schedule_dic["composed"]["operation"] == "sum":
        # A sum should be done between two schedules with the same modules/drivers characteristics.
        # If not, the second schedule should be scaled accordingly (NOT THE CASE CURRENTLY, see next elif for implementation)
        full_schedule = lml.sum_data_points_seconds(schedules[0]['full_schedule'], schedules[1]['full_schedule'])
    elif schedule_dic["composed"]["operation"] == "diff":
        # A substraction is usually conducted to retract from one schedule the light
        # produced by another, not of the same modules/drivers characteristics.
        # Hence the scaling of the second by the ratio of the maximum_intensity_required of each schedule.
        full_schedule = lml.substract_data_points_seconds(schedules[0]['full_schedule'], lml.scale_data_points_seconds(schedules[1]['full_schedule'], ponderation_factors[1]/ponderation_factors[0]))
    schedule_dic = {
        'schedule_name': schedule_name,
        'full_schedule': full_schedule,
        'earliest_power_on': lml.get_equinox_sunrise(),
        'daily_earliest_power_on': min(schedules[0]['daily_earliest_power_on'], schedules[1]['daily_earliest_power_on']),
        'latest_power_off': lml.get_equinox_sunset(),
        'daily_latest_power_off': max(schedules[0]['daily_latest_power_off'], schedules[1]['daily_latest_power_off']),
        'transition_duration_minutes': max(schedules[0]['transition_duration_minutes'], schedules[1]['transition_duration_minutes']),
        'maximum_voltage': schedules[0]['maximum_voltage'],
        'daily_maximum_intensity': schedules[0]['daily_maximum_intensity']
    }
    return schedule_dic

def generate_schedules_new(date, schedules_dic, schedule_name=None, debug=False):
    """
    This function generates all the schedules defined in the schedules dictionary.
    This dictionary is imported from a json file where all the parameters are kept.
    See light_modulation.json for more details.
    """
    out_schedule_dic = {}
    color_dic = {}
    schedule_dic_list = []
    schedules_json_driver_dic = {}
    schedules_dic_to_treat = {}

    # if we receive no schedule_name, we begin by the schedules to output (with a "name" key).
    # This should be the case during the first and general call. The function is
    # called recursively with a schedule_name defined.
    if schedule_name is None:
        print(f'0- Schedule_name is None')
        for schedule_name, schedule_dic in schedules_dic.items():
            if "name" in schedule_dic.keys():
                print(f'0- Name in schedule_dic: {schedule_name}')
                schedules_dic_to_treat[schedule_name] = schedules_dic[schedule_name]
    else:
        print(f'1- Schedule_name: {schedule_name}')
        schedules_dic_to_treat[schedule_name] = schedules_dic[schedule_name]

    # We treat all (or only one) schedules
    schedule = {}
    schedule_out = []
    for name, schedule_dic in schedules_dic_to_treat.items():
        print(f'Name to treat: {name}')
        schedule = generate_schedule(date, schedules_dic, name, debug=debug)
        if (schedule_name is not None) and len(schedules_dic_to_treat.keys()) == 1:
            print(f'{schedule_name}, Schedule_name is not None: {schedule_name is not None}')
            # the simple schedule is to be used to calculate another schedule
            # return from a recursive call
            return schedule
        else:
            print(f'Schedule_name is not None: {schedule_name is not None}')
            # the simple schedule is a final one to output
            schedule_out = lml.clean_and_simplify_to_desired_points(lml.gate_data_points_seconds(schedule['full_schedule'], lower_gate=schedule_dic["driver_minimal_voltage_for_light"], plot=PLOT), plot=PLOT)
            out_schedule_dic[name] = (schedule_out, schedule_dic["out"], schedule_dic["meta"])
        # keep schedules and details in structures for output
        out_schedule_dic[name] = (schedule_out, schedule_dic["out"], generate_meta(schedule_dic))
        # for plots
        color_dic[name] = schedule_dic["plot_color"]
        schedules_json_driver_dic[name] = (schedule_out, lml.get_module_json(schedule_dic["json"]), schedule_dic["driver_maximum_intensity"], schedule_dic["number_of_modules_in_serie"])
        # for mail report
        schedule_dic_list.append(schedule)

    # generation of documentations
    dli_details = generate_dli_details(schedules_dic_to_treat, out_schedule_dic)
    result_for_mail = generate_result_for_email(schedule_dic_list, complementary_text=dli_details)

    # generation of plots TODO: change the arg debug to follow better switchargs...
    if debug is True:
        lml.create_plot(schedules_json_driver_dic, color_dic, date, timing=10, save_path="./schedules.png")
        lml.animate_daily_spectrum(schedules_json_driver_dic, save_path="./spectrum_animation.mp4")

    return lml.stringify_schedules_in_dic(out_schedule_dic), result_for_mail

def generate_schedules(date, debug=False):
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
    number_of_modules_in_serie_3500K = 6
    driver_maximum_intensity_3500K   = 610                                     # This is the maximum Amper your led driver can produce
    driver_minimal_voltage_for_light_3500K = 0.75                               # This is the minimal voltage dim signal the driver reacts to
    maximum_intensity_required_3500K = driver_maximum_intensity_3500K*(500/610) # This is the maximum Amper you want the driver to deliver during the schedule
    schedule_3500_dic = generate_3500K_schedule(date, "schedule_3500", driver_maximum_intensity_3500K, maximum_intensity_required_3500K)
    # Gating the data so the lowest values produce already light.
    # Depending on your led array and driver, you should adjust this
    data_points_seconds_3500 = lml.gate_data_points_seconds(schedule_3500_dic['full_schedule'], lower_gate=driver_minimal_voltage_for_light_3500K, plot=PLOT)
    # The result is cleaned from redundant values and trimmed down to 32 values
    schedule_3500 = lml.clean_and_simplify_to_desired_points(data_points_seconds_3500, plot=PLOT)


    # --------------------------------------------------------------------------
    # Generation of schedule for FLUXengines 5000K
    number_of_modules_in_serie_5000K = 6
    driver_maximum_intensity_5000K   = 1510                                     # This is the maximum Amper your led driver can produce
    driver_minimal_voltage_for_light_5000K = 0.95                               # This is the minimal voltage dim signal the driver reacts to
    maximum_intensity_required_5000K = driver_maximum_intensity_5000K*0.75         # This is the maximum Amper you want the driver to deliver during the schedule
    schedule_5000_dic = generate_5000K_schedule(date, "schedule_5000", driver_maximum_intensity_5000K, maximum_intensity_required_5000K)
    # Remove light from 5000K that is already given by 3500K
    # (hence the scaling! and the need to know relative drivers maximum intensity settings).
    data_points_seconds_5000 = lml.substract_data_points_seconds(schedule_5000_dic['full_schedule'],
                                                                 lml.scale_data_points_seconds(schedule_3500_dic['full_schedule'],
                                                                                               (maximum_intensity_required_3500K/maximum_intensity_required_5000K)))
    # Gating the data so the lowest values produce already light.
    # Depending on your led array and driver, you should adjust this
    data_points_seconds_5000 = lml.gate_data_points_seconds(data_points_seconds_5000, lower_gate=driver_minimal_voltage_for_light_5000K, plot=PLOT)
    # The result is cleaned from redundant values and trimmed down to 32 values
    schedule_5000 = lml.clean_and_simplify_to_desired_points(data_points_seconds_5000, plot=PLOT)


    # --------------------------------------------------------------------------
    # Generation of schedule for APEXengines 385
    number_of_modules_in_serie_385 = 5
    driver_maximum_intensity_385   = 600                                        # This is the maximum Amper your led driver can produce
    driver_minimal_voltage_for_light_385 = 0.71                                 # This is the minimal voltage dim signal the driver reacts to
    maximum_intensity_required_385 = driver_maximum_intensity_385*0.6          # This is the maximum Amper you want the driver to deliver during the schedule
    schedule_385_dic = generate_385_schedule(date, "schedule_385", driver_maximum_intensity_385, maximum_intensity_required_385)
    # Gating the data so the lowest values produce already light.
    # Depending on your led array and driver, you should adjust this
    data_points_seconds_385 = lml.gate_data_points_seconds(schedule_385_dic['full_schedule'], lower_gate=driver_minimal_voltage_for_light_385, plot=PLOT)
    # The result is cleaned from redundant values and trimmed down to 32 values
    schedule_385 = lml.clean_and_simplify_to_desired_points(data_points_seconds_385, plot=PLOT)

    # --------------------------------------------------------------------------
    # Generation of schedule for APEXengines 660 MKIII
    number_of_modules_in_serie_660 = 5
    driver_maximum_intensity_660   = 510                                        # This is the maximum Amper your led driver can produce
    driver_minimal_voltage_for_light_660 = 0.9                                 # This is the minimal voltage dim signal the driver reacts to
    maximum_intensity_required_660 = driver_maximum_intensity_660*0.30          # This is the maximum Amper you want the driver to deliver during the schedule
    schedule_660_dic = generate_660_schedule(date, "schedule_660", driver_maximum_intensity_660, maximum_intensity_required_660)
    # Gating the data so the lowest values produce already light.
    # Depending on your led array and driver, you should adjust this
    data_points_seconds_660 = lml.gate_data_points_seconds(schedule_660_dic['full_schedule'], lower_gate=driver_minimal_voltage_for_light_660, plot=PLOT)
    # The result is cleaned from redundant values and trimmed down to 32 values
    schedule_660 = lml.clean_and_simplify_to_desired_points(data_points_seconds_660, plot=PLOT)

    # --------------------------------------------------------------------------
    # packing of all the schedules generated in a dictionary.
    # !! Key values ARE THE NAMES OF THE SCHEDULES DEFINED IN THE CRESCONTROL !!
    # !! Second element in tuple is the out name for the schedule to modulate !!
    # !! Third element is the meta info for Cre.Science HUB.
    meta_3500 = 'out-a:meta="{\\"unit\\":\\"A\\",\\"module\\":{\\"driver\\":{\\"configuration\\":[' + f'{number_of_modules_in_serie_3500K:1d}' + ',1],\\"id\\":\\"MW-XLG-150-LAB\\"},\\"id\\":\\"CSC-FXE-140-C-35\\"},\\"type\\":\\"light\\",\\"icon\\":\\"sysFluxEngine\\",\\"id\\":\\"CSC-FXE-140-C-35\\",\\"name\\":\\"FXengine 3500K\\",\\"ecos\\":[\\"Lithops\\"],\\"curr\\":' + f'{(driver_maximum_intensity_3500K/1000):0.2f}' + '}"'
    meta_5000 = 'out-b:meta="{\\"unit\\":\\"A\\",\\"module\\":{\\"driver\\":{\\"configuration\\":[' + f'{number_of_modules_in_serie_5000K:1d}' + ',1],\\"id\\":\\"MW-XLG-150-LAB\\"},\\"id\\":\\"CSC-FXE-140-C-50\\"},\\"type\\":\\"light\\",\\"icon\\":\\"sysFluxEngine\\",\\"id\\":\\"CSC-FXE-140-C-50\\",\\"name\\":\\"FXengine 5000K\\",\\"ecos\\":[\\"Lithops\\"],\\"curr\\":' + f'{(driver_maximum_intensity_5000K/1000):0.2f}' + '}"'
    meta_385  = 'out-c:meta="{\\"unit\\":\\"A\\",\\"module\\":{\\"driver\\":{\\"configuration\\":[' + f'{number_of_modules_in_serie_385:1d}' + ',1],\\"id\\":\\"MW-LCM-040\\"},\\"id\\":\\"CSC-AXE-004-A-38\\"},\\"type\\":\\"light\\",\\"icon\\":\\"sysApexEngine\\",\\"id\\":\\"CSC-AXE-004-A-38\\",\\"name\\":\\"APEXengine 385 \\",\\"ecos\\":[\\"Lithops\\"],\\"curr\\":' + f'{(driver_maximum_intensity_385/1000):0.2f}' + '}"'
    meta_660  = 'out-d:meta="{\\"unit\\":\\"A\\",\\"module\\":{\\"driver\\":{\\"configuration\\":[' + f'{number_of_modules_in_serie_660:1d}' + ',1],\\"id\\":\\"MW-XLG-025-XAB\\"},\\"id\\":\\"CSC-AXE-004-C-66\\"},\\"type\\":\\"light\\",\\"icon\\":\\"sysApexEngine\\",\\"id\\":\\"CSC-AXE-004-C-66\\",\\"name\\":\\"APEXengine 660 \\",\\"ecos\\":[\\"Lithops\\"],\\"curr\\":' + f'{(driver_maximum_intensity_660/1000):0.2f}' + '}"'

    schedule_dic = {
        "schedule_3500" : (schedule_3500, "out-a", meta_3500),
        "schedule_5000" : (schedule_5000, "out-b", meta_5000),
        "schedule_385"  : (schedule_385,  "out-c", meta_385),
        "schedule_660"  : (schedule_660,  "out-d", meta_660)
    }
    color_dic = {
        "schedule_3500" : 'ivory',
        "schedule_5000" : 'lightSkyBlue',
        "schedule_385"  : 'blueviolet',
        "schedule_660"  : 'DarkRed'
    }

    # --------------------------------------------------------------------------
    # get the json files for the modules
    json_3500 = lml.get_module_json("fluxengine_3500k")
    json_5000 = lml.get_module_json("fluxengine_5000k")
    json_385  = lml.get_module_json("apexengine_385")
    json_660  = lml.get_module_json("apexengine_660")
    lit_area = 0.4 #m²
    loss_factor = 0.8 #%

    dli_3500 = loss_factor*number_of_modules_in_serie_3500K*lml.get_dli_by_m2(schedule_3500, driver_maximum_intensity_3500K, json_3500, lit_area)/1000000
    dli_5000 = loss_factor*number_of_modules_in_serie_5000K*lml.get_dli_by_m2(schedule_5000, driver_maximum_intensity_5000K, json_5000, lit_area)/1000000
    dli_385  = loss_factor*number_of_modules_in_serie_385*lml.get_dli_by_m2(schedule_385,  driver_maximum_intensity_385,   json_385, lit_area) /1000000
    dli_660  = loss_factor*number_of_modules_in_serie_660*lml.get_dli_by_m2(schedule_660,  driver_maximum_intensity_660,   json_660, lit_area) /1000000

    dli_details = f'\
DLI for the schedules calculated based on modules numbers, \n\
characteristics and driver settings for a lit area of {lit_area}m² \n\
and a loss factor of {((1.0-loss_factor)*100):2.0f}% \n\
--------------------------------------------------------------------------------\n\
    {dli_3500:6.3f} mol/m²/day of photon delivered by 6 FLUXengines 3500K on a driver set at {driver_maximum_intensity_3500K:4.0f}mA. \n\
    {dli_5000:6.3f} mol/m²/day of photon delivered by 6 FLUXengines 5000K on a driver set at {driver_maximum_intensity_5000K:4.0f}mA. \n\
    {dli_385:6.3f} mol/m²/day of photon delivered by 5 APEXengines 385nm on a driver set at {driver_maximum_intensity_385:4.0f}mA. \n\
    {dli_660:6.3f} mol/m²/day of photon delivered by 5 APEXengines 660nm on a driver set at {driver_maximum_intensity_660:4.0f}mA. \n\
    {(dli_3500+dli_5000+dli_385+dli_660):6.3f} mol/m²/day of photon delivered in total.\n\
--------------------------------------------------------------------------------\n'

    # --------------------------------------------------------------------------
    # Create a schedules plot and an animated spectrum for the current day
    if debug is True:
        schedules_json_driver_dic = {
            "schedule_3500" : (schedule_3500, json_3500, driver_maximum_intensity_3500K, number_of_modules_in_serie_3500K),
            "schedule_5000" : (schedule_5000, json_5000, driver_maximum_intensity_5000K, number_of_modules_in_serie_5000K),
            "schedule_385"  : (schedule_385,  json_385, driver_maximum_intensity_385, number_of_modules_in_serie_385),
            "schedule_660"  : (schedule_660,  json_660, driver_maximum_intensity_660, number_of_modules_in_serie_660)
        }
        lml.create_plot(schedules_json_driver_dic, color_dic, date, timing=10, save_path="./schedules.png")
        lml.animate_daily_spectrum(schedules_json_driver_dic, save_path="./spectrum_animation.mp4")

    # --------------------------------------------------------------------------
    # Shedules need to be passed as string to the Crescontrol.
    schedule_dic = lml.stringify_schedules_in_dic(schedule_dic)

    # generate a report of schedules generated to be sent by email (or simply printed)
    schedules_dic_list = [schedule_3500_dic, schedule_5000_dic, schedule_385_dic, schedule_660_dic]
    result_for_mail = generate_result_for_email(schedules_dic_list, complementary_text=dli_details)

    return schedule_dic, result_for_mail

# ------------------------------------------------------------------------------
