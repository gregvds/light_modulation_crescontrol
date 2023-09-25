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
    Be sure to adapt light_modulation_settings.py to your environment""",
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-d",
                        "--debug",
                        action='store_true',
                        help="Debug mode: does not send schedules to Crescontrol")
    parser.add_argument("-p",
                        "--plot",
                        action='store_true',
                        help="Plot mode: show several plots for schedules in debug mode")

    args = parser.parse_args()

    if args.plot:
        args.debug = True
        lms.PLOT = True

    with open(os.path.join(LOCALDIRN, LOGFILE), 'w') as logFile:
        lml.printAndLog('\nScript for daily generation of lighting schedules\n', logFile)
        lml.printAndLog(f'Sending from            system on {local_ip}\n', logFile)
        lml.printAndLog(f'Current day and time of system on {local_ip}: {lml.datetime.datetime.now():%d %b %Y - %H:%M:%S}', logFile)
        lml.printAndLog(f'Time of     CresControl system on {lml.CRESCONTROL_IP}: {lml.get_crescontrol_time()}.\n', logFile)

        # Generation of Schedules
        schedule_dic, result_for_mail = lms.generate_schedules()

        string_schedule_dic = lml.stringify_schedules_in_dic(schedule_dic)
        lml.printAndLog("Produced schedules:\n", logFile)
        for schedule_name, (schedule_string, out_name) in string_schedule_dic.items():
            lml.printAndLog(f'Schedule {schedule_name} for {out_name}:\n{schedule_string}\n', logFile)
        lml.printAndLog('\n\n', logFile)

        print(result_for_mail)

        if not args.debug:
            # Let's find out if CresControl is reachable:
            result, status = lml.test_crescontrol_online()
            lml.printAndLog(result, logFile)
            result_for_mail += result
            result_for_mail += "\n"
            if status is True:
                # Let be sure the Crescontrol time is aligned on the good timezone:
                result, status = lml.set_crescontrol_timezone(lml.TIMEZONE)
                lml.printAndLog(result, logFile)
                result_for_mail += result
                result_for_mail += "\n"

                # Post of schedules to CresControl
                print(string_schedule_dic)
                result, status2 = lml.send_schedules_to_crescontrol(string_schedule_dic)
                lml.printAndLog(result, logFile)
                if status2 is True:
                    lml.printAndLog('Schedules sent :-).\n\n', logFile)
                else:
                    lml.printAndLog(f'Problem sending schedules :-(.\n', logFile)
                result_for_mail += result
                result_for_mail += "\n"

                # Currently, something somehow enables wrongly the switch-12v...
                # Let's disable it for now if enabled at this time:
                response, time_taken = lml.execute_command('switch-12v:enabled')
                if response != "0":
                    message = "Switch-12v enabled. Disabling it:\n"
                    lml.printAndLog(message, logFile)
                    result_for_mail += message
                    response, time_taken = lml.execute_command_and_report('switch-12v:enabled=0')
                    result_for_mail += response
                    result_for_mail += '\n'

                # Saving system configuration
                response, time_taken = lml.execute_command_and_report('system:save()')
                result_for_mail += response
                result_for_mail += '\n'

                result_for_mail += 'Finished.\n'
            else:
                # no CresControl found!
                result_for_mail += f"Crescontrol on {lms.CRESCONTROL_IP} was not found, nothing done!\n"
            # Send of mail
            lml.send_mail(result_for_mail)
        else:
            # DEBUG
            # These plots are intended to test and show the effect of the yearly
            # modulation
            lml.create_triple_plot(schedule_dic["schedule_3500"][0],
                                   schedule_dic["schedule_5000"][0],
                                   schedule_dic["schedule_385"][0])
            # lml.animate_yearly_schedule(10)
            # lml.create_yearly_schedule_3d_plot(10)
            # lml.create_monthly_plots()

        lml.printAndLog("Finished.", logFile)
