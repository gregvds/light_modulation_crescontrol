# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# Author: Gregoire Vandenschrick
# Date:   27/10/2023
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# -- Imports for communication with crescontrol
import time
import logging
import websocket
import light_modulation_settings as lmt

# -- Imports for communication of results by mail
import smtplib
from email.mime.text import MIMEText

# -- Imports to get LOCAL_IP
import socket

# ------------------------------------------------------------------------------
# -- local constants definitions.
ws = None

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

def open_ws(debug=False):
    """
    """
    debug = (logging.root.level == logging.DEBUG)
    websocket.enableTrace(debug)
    global ws
    if ws is None:
        logging.debug(f'No current websocket opened on {lmt.CRESCONTROL_IP}, creating connection:')
        ws = websocket.create_connection(f'ws://{lmt.CRESCONTROL_IP}:81',
            timeout=600,
            cookie='nutty',
            host=f'{lmt.CRESCONTROL_IP}',
            origin="light_modulation.org",
            skip_utf8_validation=True)
        logging.debug(f'Websocket connection created on ws://{lmt.CRESCONTROL_IP}:81')

def close_ws():
    """
    """
    global ws
    if ws is not None:
        logging.debug('Websocket open, closing it:')
        ws.close(status=websocket.STATUS_NORMAL, reason="Connection closed gracefully")
        logging.debug('Websocket closed.')

def execute_command(query, clean_answer=True):
    """
    sends a query to CresControl through websockets,
    gets the response,
    measure the delay it took between send and receive
    and return cleaned response and delay
    """
    global ws
    start = time.time()
    if ws is None:
        print('ws None, creating it')
        open_ws()
    logging.debug(f'ws opened in {time.time() - start}s')
    #ws = websocket.create_connection(f'ws://{CRESCONTROL_IP}:81',timeout=1000)
    ws.send(query)
    logging.debug(f'ws.send(query) in {time.time() - start}s')
    response=ws.recv()
    logging.debug(f'response=ws.recv() in {time.time() - start}s')
    #ws.close()
    end = time.time()
    time_taken = end - start
    if clean_answer:
        response = clean_up_crescontrol_response(response)
        logging.debug(f'clean up of CC response in {time.time() - start}s')
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
    logging.info(f'Testing if CresControl on ws://{lmt.CRESCONTROL_IP}:81 is accessible:')
    output = execute_command_and_report('system:cpu-id')
    status = lmt.CRESCONTROL_CPU_ID in output
    if status:
        logging.info(f'Crescontrol online :-)\n')
    else:
        logging.warning(f'Unable to reach {lmt.CRESCONTROL_URL} with CPU ID {lmt.CRESCONTROL_CPU_ID} :-(: {response}\n')
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

def set_crescontrol_access_point_key():
    """
    WIP here, not in use currently
    """
    logging.info('Setting crescontrol access point wifi key:')
    output = execute_command_and_report(f'wifi:access-point:key={lmt.CRESCONTROL_ACCESS_POINT_KEY}')

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

def wait_for_cc_frequency_recovery(minimum_frequency=400, minimum_time=10):
    """
    This function waits until the crescontrol frequency has recovered to a decent value
    """
    status = False
    while not status:
        output = float(execute_command_and_report('system:frequency'))
        logging.debug(f'Crescontrol frequency: {output}Hz.')
        status = (output >= minimum_frequency)
        time.sleep(minimum_time/3)
        output = float(execute_command_and_report('system:frequency'))
        logging.debug(f'Crescontrol frequency: {output}Hz.')
        status = status and (output >= minimum_frequency)
        time.sleep(minimum_time/3)
        output = float(execute_command_and_report('system:frequency'))
        logging.debug(f'Crescontrol frequency: {output}Hz.')
        status = status and (output >= minimum_frequency)
        time.sleep(minimum_time/3)

def create_schedule_if_not_exists(schedule_name, keep_existing_schedule=False):
    """
    This function creates a schedule with the given name.
    If this one already exists, it removes it first or not as asked.
    """
    status = False
    if not keep_existing_schedule:
        logging.info(f'Creating schedule {schedule_name} if not existant, else recreating it:')
    else:
        logging.info(f'Creating schedule {schedule_name} if not existant, else does nothing:')
    # Check if schedule exists already, if not, creates it.
    output = execute_command_and_report(f'schedule:get-name("{schedule_name}")')
    if ' error : a schedule with this name does not exist ' not in output:
        logging.info(f'Schedule {schedule_name} already exists.')
        if not keep_existing_schedule:
            status = remove_schedule(schedule_name)
            if status:
                return create_schedule_if_not_exists(schedule_name)
            else:
                logging.error(f'Impossible to remove schedule {schedule_name} :-(.')
                return status
        else:
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

def remove_schedule(schedule_name):
    """
    This function removes a schedule if it exists
    """
    status = False
    logging.info(f'Removing schedule {schedule_name}:')
    # Check if schedule exists already, if so removes it.
    output = execute_command_and_report(f'schedule:get-name("{schedule_name}")')
    status = ' error : a schedule with this name does not exist ' in output
    if not status:
        output = execute_command_and_report(f'schedule:remove("{schedule_name}")')
        status = ('success' in output)
        if status:
            logging.info(f'{schedule_name} successfully removed :-).')
        else:
            logging.error(f'Failed to remove {schedule_name} :-(.')
    else:
        logging.info(f'{schedule_name} does not exist, nothing removed.')
    return status

def disable_schedule(schedule_name):
    """
    This function disable a schedule if enabled.
    """
    status = False
    logging.info(f'Disabling schedule {schedule_name} if enabled:')
    output = execute_command_and_report(f'schedule:get-enabled("{schedule_name}")')
    if '1' in output:
        output = execute_command_and_report(f'schedule:set-enabled("{schedule_name}",0)')
        status = ('success' in output)
        if not status:
            logging.warning(f'Schedule {schedule_name} encountered a problem during its disabling: {output}, passing it.')
        else:
            logging.info(f'{schedule_name} disabled :-)!')
    elif '0' in output:
        status = True
        logging.info(f'{schedule_name} already disabled :-)!')
    else:
        logging.warning(f'Schedule {schedule_name} encountered a problem during its disabling: {output}, passing it.')
    return status

def enable_schedule(schedule_name):
    """
    This function enable a schedule if disabled.
    """
    status = False
    logging.info(f'Enabling schedule {schedule_name} if disabled:')
    output = execute_command_and_report(f'schedule:get-enabled("{schedule_name}")')
    if '0' in output:
        output = execute_command_and_report(f'schedule:set-enabled("{schedule_name}",1)')
        status = ('success' in output)
        if not status:
            logging.warning(f'Schedule {schedule_name} encountered a problem during its enabling: {output}, passing it.')
        else:
            logging.info(f'{schedule_name} enabled :-)!')
    elif '1' in output:
        status = True
        logging.info(f'{schedule_name} already enabled :-)!')
    else:
        logging.warning(f'Schedule {schedule_name} encountered a problem during its enabling: {output}, passing it.')
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

        status = create_schedule_if_not_exists(schedule_name, keep_existing_schedule=True)
        global_status = global_status and status
        if not status:
            logging.warning(f'Schedule {schedule_name} encountered a problem during its creation or search, passing it.')
            continue

        status = disable_schedule(schedule_name)
        global_status = global_status and status
        if not status:
            logging.warning(f'Schedule {schedule_name} encountered a problem during its disabling, passing it.')
            continue

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

        res = '1.00,0.02'
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

        status = enable_schedule(schedule_name)
        global_status = global_status and status
        if not status:
            continue

        output = execute_command_and_report(f'schedule:save("{schedule_name}")')
        global_status = global_status and ('success' in output)
        if not status:
            logging.warning(f'Schedule {schedule_name} encountered a problem during its saving, passing it.')
            continue
        logging.info(f'Schedule {schedule_name} saved :-).\n')

        wait_for_cc_frequency_recovery(minimum_time=10)
    return global_status

# ------------------------------------------------------------------------------

def get_local_ip(attempt=0):
    if attempt < 10:
        try:
            return [l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1],
                [[(s.connect(('1.1.1.1', 53)),
                s.getsockname()[0],
                s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]
        except Exception as err:
            attempt+=1
            logging.warning(f'New attempt at getting local IP ({attempt} failed attempts)')
            return get_local_ip(attempt=attempt)
    else:
        logging.warning('Unable to get the local IP, faking it to 0.0.0.0')
        return '0.0.0.0'

def send_mail(email_message):
    """
    Create an email message and sends it
    """
    email_message = MIMEText(email_message)
    email_message['Subject'] = "Generation of schedules script and CresControl Responses"
    email_message['From'] = lmt.SENDER_EMAIL
    email_message['Reply-to'] = lmt.SENDER_EMAIL
    email_message['To'] = lmt.RECEIVER_EMAIL
    logging.debug(f'Message to be mailed:\n{email_message}\n')
    # Connect to the SMTP server and send the email
    with smtplib.SMTP(lmt.SMTP_SERVER, 587) as server:  # Replace with your SMTP server details
        server.starttls()
        server.login(lmt.SENDER_EMAIL, lmt.SENDER_PASSWORD)
        server.sendmail(lmt.SENDER_EMAIL, lmt.RECEIVER_EMAIL, email_message.as_string())
