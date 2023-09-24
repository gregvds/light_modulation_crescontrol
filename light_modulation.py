# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# Author: Gregoire Vandenschrick
# Date:   14/09/2023
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

# -- Import for the generation of data_points and communications
import light_modulation_library as lml
import light_modulation_schedule as lms
import os
import argparse

# ------------------------------------------------------------------------------
# -- local constants definitions. Please be sure you have write access to LOCALDIRN
LOCALDIRN   = '.'
LOGFILE     = os.path.basename(__file__).replace('py','log')

# ------------------------------------------------------------------------------
local_ip = lml.get_local_ip()

# ------------------------------------------------------------------------------
# -- Main use of code ----------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""
    Python script to generate schedules modulated according to the current day.
    This script can be run manually, or called regularly with cron for example.
    Parameters of the schedules are to be modified in light_modulation_schedule.py.""",
                                     epilog="""
    Please, refer to light_modulation_schedule.py for further informations on
    how to tailor your schedules.
    Currently, light_modulation_schedule generates three schedules,
    - one for FLUXengine 3500K, mainly active at dawn and dusk
    - one for FLUXengine 5000K, during all day
    - one for APEXengine 385nm, around the mid part of the day.
    !! Be sure to adapt light_modulation_settings.py to your environment !!""",
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-d",
                        "--debug",
                        action='store_true',
                        help="Debug mode: does not send schedules to Crescontrol.")
    parser.add_argument("-p",
                        "--plot",
                        action='store_true',
                        help="Plot mode: show several plots for schedules. Forces debug mode too.")

    args = parser.parse_args()

    if args.plot:
        args.debug = True
        lms.PLOT = True

    with open(os.path.join(LOCALDIRN, LOGFILE), 'w') as logFile:
        lml.printAndLog('Script for daily generation of lighting schedules\n', logFile)
        lml.printAndLog('Sending  from %s:\n' % local_ip, logFile)
        lml.printAndLog(f"Current day on {local_ip}: {lml.datetime.datetime.now():%d %b %Y - %H:%M:%S}", logFile)
        lml.printAndLog(f'Time of CresControl system: {lml.get_crescontrol_time()}.', logFile)

        # Generation of Schedules
        schedule_dic, result_for_mail = lms.generate_schedules()

        string_schedule_dic = lml.stringify_schedules_in_dic(schedule_dic)
        lml.printAndLog("Produced schedules:\n", logFile)
        for schedule_name, schedule_string in string_schedule_dic.items():
            lml.printAndLog(f'Schedule {schedule_name}:\n{schedule_string}', logFile)
        lml.printAndLog('\n\n', logFile)

        # Dictionary linking schedule_name and output of CresControl
        schedules_names_params_dic = {
            "schedule_3500" : "out-a",
            "schedule_5000" : "out-b",
            "schedule_385"  : "out-c"
        }

        print(result_for_mail)

        if not args.debug:
            # Post of schedules to CresControl
            for schedule_name, _ in schedule_dic.items():
                result, status = lml.create_schedule_if_not_exists(schedule_name, schedules_names_params_dic[schedule_name])
                lml.printAndLog(result, logFile)
                result_for_mail += result
                result_for_mail += "\n"
                if status is True:
                    single_schedule_dic = {schedule_name : [string_schedule_dic[schedule_name], schedules_names_params_dic[schedule_name]]}
                    result, status2 = lml.send_schedules_to_crescontrol(single_schedule_dic)
                    lml.printAndLog(result, logFile)
                    if status2 is True:
                        lml.printAndLog('Schedule sent.\n', logFile)
                    else:
                        lml.printAndLog(f'Problem during sending schedule {schedule_name}.\n', logFile)
                    result_for_mail += result
                    result_for_mail += "\n"
            response, time_taken = lml.execute_command('system:save()')
            result_for_mail += response
            result_for_mail += '\n'

            # Currently, the switch-12v turns on erratically for no reason...
            # For good measure, let's disable it:
            response, time_taken = lml.execute_command('switch-12v:enabled')
            if response != "0":
                message = "Switch-12v enabled. Disabling it:\n"
                lml.printAndLog(message, logFile)
                result_for_mail += message
                response, time_taken = lml.execute_command('switch-12v:enabled=0')
                result_for_mail += response
                result_for_mail += '\n'
            result_for_mail += 'Finished.\n'

            # Send of mail
            lml.send_mail(result_for_mail)
        else:
            # DEBUG
            # These plots are intended to test and show the effect of the yearly
            # modulation
            lml.create_triple_plot(schedule_dic["schedule_3500"],
                                   schedule_dic["schedule_5000"],
                                   schedule_dic["schedule_385"])
            # lml.animate_yearly_schedule(6.75,18.50,1,1,60,0.1,10)
            # lml.create_monthly_plots()

        lml.printAndLog("Finished.", logFile)
