# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# Author: Gregoire Vandenschrick
# Date:   14/09/2023
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

# -- Import for the generation of data_points and communications
import os
import sys
import argparse
import logging
import light_modulation_library as lml
import light_modulation_schedule as lms

# ------------------------------------------------------------------------------
# -- local constants definitions. Please be sure you have write access to LOCALDIRN
LOCALDIRN   = './'
LOGFILE     = os.path.basename(__file__).replace('py','log')

# ------------------------------------------------------------------------------
local_ip = lml.get_local_ip()

def get_args():
    """
    Analyse arguments passed to the script
    """
    parser = argparse.ArgumentParser(description="""
    Python script to generate schedules modulated according to the current day.
    This script can be run manually, or called regularly with cron for example.""",
                                     epilog="""
    Please, refer to light_modulation_schedule.py for further informations on
    how to tailor your schedules.
    Currently, light_modulation_schedule generates three schedules:
    - one for FLUXengine 3500K, mainly active at dawn and dusk
    - one for FLUXengine 5000K, during all day
    - one for APEXengine 385nm, around the mid part of the day.
    !! Be sure to adapt light_modulation_settings.py to your environment !!""",
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
    return args

def set_log(debug=False):
    """
    """
    lml.plt.set_loglevel (level = 'warning')
    level = logging.INFO
    if debug:
        level = logging.DEBUG
    logging.basicConfig(handlers=[
                            logging.FileHandler(os.path.join(LOCALDIRN, LOGFILE), mode='w'),
                            logging.StreamHandler(sys.stdout)
                        ],
                        format='-- %(asctime)s -- [%(levelname)s]: %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p',
                        level=level)

def main():
    logging.info('\nScript for daily generation of lighting schedules\n')
    logging.info(f'Sending from            system on {local_ip}\n')
    logging.info(f'Current day and time of system on {local_ip}: {lml.datetime.datetime.now():%d %b %Y - %H:%M:%S}')

    # First we generate all the schedules
    schedule_dic, result_for_mail = lms.generate_schedules(debug=args.debug)
    
    logging.info("Produced schedules:\n")
    for schedule_name, (schedule_string, out_name) in schedule_dic.items():
        logging.info(f'Schedule {schedule_name} for {out_name}:\n{schedule_string}\n')
    logging.info('\n\n')

    # then we send them to the Crescontrol, if not in debug mode
    if not args.debug:
        # Let's find out if CresControl is reachable:
        result, status = lml.test_crescontrol_online()
        logging.info(result)
        result_for_mail += result
        result_for_mail += "\n"
        if status is True:
            # Let's be sure the Crescontrol time is aligned on the good timezone:
            result, status = lml.set_crescontrol_timezone(lml.TIMEZONE)
            logging.info(result)
            result_for_mail += result
            result_for_mail += "\n"

            # Post of schedules to CresControl
            result, status2 = lml.send_schedules_to_crescontrol(schedule_dic)
            logging.info(result)
            if status2 is True:
                logging.info('Schedules sent :-).\n\n')
            else:
                logging.error(f'Problem sending schedules :-(.\n')
            result_for_mail += result
            result_for_mail += "\n"

            # Saving system configuration
            response, time_taken = lml.execute_command_and_report('system:save()')
            result_for_mail += response
            result_for_mail += '\n'

            result_for_mail += 'Finished.\n'
        else:
            # no CresControl found!
            message = f"Crescontrol on {lms.CRESCONTROL_IP} was not found, nothing done!\n"
            logging.warning(message)
            result_for_mail += message
        # Send of mail
        lml.send_mail(result_for_mail)
    logging.info(result_for_mail)
    logging.info("Finished.")

# ------------------------------------------------------------------------------
# -- Main use of code ----------------------------------------------------------
if __name__ == "__main__":
    args = get_args()

    if args.plot:
        args.debug = True
        lms.PLOT = True

    set_log(debug=args.debug)

    main()
