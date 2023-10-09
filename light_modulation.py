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
    - one for APEXengine 385nm, around the mid part of the day
    - one for APEXengine 660nm, mainly active at dawn and dusk
    !! Be sure to adapt light_modulation_settings.py to your environment !!""",
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-p",
                        "--plot",
                        action='count',
                        help="plot mode, cumulative: show several plots for schedules and schedule creation")
    parser.add_argument("-v",
                        "--verbosity",
                        action='count',
                        help="verbosity mode, cumulative: -v for warning level, -vv for info level, -vvv for debug level")
    parser.add_argument("-q",
                        "--noquery",
                        action='store_true',
                        help="No queries sent to CresControl")
    parser.add_argument("-m",
                        "--nomail",
                        action='store_true',
                        help="No report sent by email")

    args = parser.parse_args()
    if args.verbosity is None:
        args.verbosity = 0
    if args.plot is None:
        args.plot = 0
    return args

def set_log(verbosity):
    """
    """
    lml.plt.set_loglevel (level = 'warning')
    level = logging.ERROR
    if verbosity == 1:
        level = logging.WARNING
    elif verbosity == 2:
        level = logging.INFO
    elif verbosity == 3:
        level = logging.DEBUG
    logging.basicConfig(handlers=[
                            logging.FileHandler(os.path.join(LOCALDIRN, LOGFILE), mode='w'),
                            logging.StreamHandler(sys.stdout)
                        ],
                        format='-- %(asctime)s -- [%(levelname)s]:\n-> %(message)s\n',
                        datefmt='%d %b %Y %H:%M:%S',
                        level=level)

def main():
    args = get_args()
    set_log(args.verbosity)

    lms.PLOT = args.plot > 1

    logging.info('Script for daily generation of lighting schedules')
    logging.info(f'Current day and time of system on {local_ip}: {lml.datetime.datetime.now():%d %b %Y - %H:%M:%S}')

    # First we generate all the schedules
    schedule_dic, result_for_mail = lms.generate_schedules(debug=(args.plot>=1))

    logging.debug("Produced schedules:")
    for schedule_name, (schedule_string, out_name, meta) in schedule_dic.items():
        logging.debug(f'Schedule {schedule_name} for {out_name}:\n{schedule_string}')
        logging.debug(f'Meta for schedule {schedule_name}:\n{meta}')
    logging.info(result_for_mail)

    # then we send them to the Crescontrol, if not in no query mode
    if not args.noquery:
        logging.info(f'Sending from            system on {local_ip}')
        # Let's find out if CresControl is reachable:
        status = lml.test_crescontrol_online()
        if status is True:
            # Let's be sure the Crescontrol time is aligned on the good timezone:
            result = lml.set_crescontrol_timezone(lml.TIMEZONE)
            if str(lml.TIMEZONE) in result:
                logging.info(f'Crescontrol time zone set to {lml.TIMEZONE} :-).\n')
            else:
                logging.warning(f'Problem setting the Crescontrol timezone :-(.')

            # Post of schedules to CresControl
            status2 = lml.send_schedules_to_crescontrol(schedule_dic)
            if status2 is True:
                logging.info('Schedules sent :-).')
            else:
                logging.error(f'Problem sending schedules, please see logs :-(.')

            # Saving system configuration
            response = lml.execute_command_and_report('system:save()')
            if "success" in response:
                logging.info("New configuration saved on CresControl system :-).")
            else:
                logging.warn("Save attempt of Crescontrol system failed :-(.")
        else:
            # no CresControl found!
            logging.warning(f"Crescontrol on {lms.CRESCONTROL_IP} was not found, nothing done!\n")
    else:
        logging.info("No queries sent to CresControl (arg -q received).")
    logging.info("Finished.")

    # Send of mail if not in no mail mode
    if not args.nomail:
        logging.info("Sending logging by email (no arg -m received).")
        with open(f'{os.path.join(LOCALDIRN, LOGFILE)}', mode = 'r') as file:
            fileContent = file.read()
            lml.send_mail(fileContent)
    else:
        logging.info("No mail sent (arg -m received).")

# ------------------------------------------------------------------------------
# -- Main use of code ----------------------------------------------------------
if __name__ == "__main__":
    main()
