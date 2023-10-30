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
# -- Global variables definitions.
ws_on_cc = None
ws_on_server = None
token = None
uid = None

# - formating times ------------------------------------------------------------
def round_thousands_second_time_delta(time_taken):
    """
    """
    float_time = float(time_taken)
    if float_time > 60.0:
        return f'{int(float_time/60):02d}:{(float_time%60):02.3f}'
    else:
        return f'{float_time:02.3f}'

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

# - websockets -----------------------------------------------------------------
def open_ws_on_cc(debug=False):
    """
    """
    debug = (logging.root.level == logging.DEBUG)
    websocket.enableTrace(debug)
    global ws_on_cc
    if ws_on_cc is None:
        logging.info(f'No current websocket opened on ws://{lmt.CRESCONTROL_IP}:81, creating connection:')
        ws_on_cc = websocket.create_connection(f'ws://{lmt.CRESCONTROL_IP}:81',
            timeout=600,
            cookie='nutty',
            host=f'{lmt.CRESCONTROL_IP}',
            origin="light_modulation.org",
            skip_utf8_validation=True)
        #output=ws_on_cc.recv()
        #print(f'response from websocket connection opening on CC: {output}')
        logging.info(f'Websocket connection created on ws://{lmt.CRESCONTROL_IP}:81')

def close_ws_on_cc():
    """
    """
    global ws_on_cc
    if ws_on_cc is not None:
        logging.info('Websocket open on CC, closing it:')
        ws_on_cc.close(status=websocket.STATUS_NORMAL, reason="Connection closed gracefully")
        logging.info('Websocket on CC closed.')
        ws_on_cc = None

def open_ws_on_server(debug=False):
    """
    Open a websocket client connection to root.cre.science
    """
    debug = (logging.root.level == logging.DEBUG)
    websocket.enableTrace(debug)
    global ws_on_server
    if ws_on_server is None:
        logging.info(f'No current websocket opened on wss://{lmt.REMOTE_API_URL}:443, creating connection:')
        ws_on_server = websocket.create_connection(f'wss://{lmt.REMOTE_API_URL}:443',
            timeout=600,
            cookie='nutty',
            host=f'{lmt.REMOTE_API_URL}',
            origin="light_modulation.org",
            skip_utf8_validation=True)
        output=ws_on_server.recv()
        logging.debug(f'First answer at websocket on server creation: {output}')
        status = ('welcome' in output)
        if status:
            logging.info(f'Websocket connection created on wss://{lmt.REMOTE_API_URL}:443 :-)')
        else:
            logging.error(f'Websocket connection failed on wss://{lmt.REMOTE_API_URL}:443 :-/')

def close_ws_on_server():
    """
    Close a websocket client connection to root.cre.science
    """
    global ws_on_server
    if ws_on_server is not None:
        logging.info('Websocket open on server, closing it:')
        ws_on_server.close(status=websocket.STATUS_NORMAL, reason="Connection closed gracefully")
        logging.info('Websocket on server closed.')
        ws_on_server = None

def connect_cc_to_server(force_reconnect=False):
    """
    Connects the crescontrol to root.cre.science server with login/pwd and get
    token from it. This must be passed directly to the CC, not via server
    """
    global token
    global uid
    global_status = True
    cc_parameters_changed = False

    # Check if CC is already connected:
    output = execute_command_and_report('websocket:remote:connected')
    status = ('1' in output)
    if status:
        logging.info(f'CC connected :-).')
        logging.info('Getting token and uid from CC:')
        token = execute_command_and_report(f'user:token')
        uid = execute_command_and_report(f'websocket:remote:uid')
        logging.info(f'Token {token} obtained by CC from remote server :-).')
        logging.info(f'Uid {uid} obtained from CC :-).')
        return global_status
    logging.info(f'CC currently not connected to server, connecting it:')

    # Check if CC allows remote connection:
    output = execute_command_and_report('websocket:remote:allow-connection')
    status = ('0' in output)
    if status:
        logging.info('CC does not currently allows remote connection, allowing it:')
        output = execute_command_and_report('websocket:remote:allow-connection=1')
        status = ('1' in output)
        global_status = global_status and status
        if not status:
            logging.warning(f'Unable to allow remote connection :-/.')
            return global_status
    logging.info(f'Remote connection allowed :-).')

    # Check if CC has already been authenticated once:
    output = execute_command_and_report(f'websocket:remote:authenticated')
    status = ('1' in output)
    if not status:
        logging.info('CC currently not authenticated, authenticating it:')
        output = execute_command_and_report(f'user:name')
        status = (lmt.REMOTE_USER in output)
        if not status:
            cc_parameters_changed = True
            output = execute_command_and_report(f'user:name="{lmt.REMOTE_USER}"')
            status = (lmt.REMOTE_USER in output)
            global_status = global_status and status
            if not status:
                logging.error(f'Unable to define user name for remote connection {lmt.REMOTE_USER}.')
                return global_status
        logging.info(f'User name {lmt.REMOTE_USER} for remote connection defined :-).')

        output = execute_command_and_report(f'user:password')
        status = ('no access' in output)
        if not status:
            cc_parameters_changed = True
            output = execute_command_and_report(f'user:password="{lmt.REMOTE_PASSWORD}"')
            status = (lmt.REMOTE_PASSWORD in output)
            global_status = global_status and status
            if not status:
                logging.error(f'Unable to define user passowrd for remote connection {lmt.REMOTE_PASSWORD}.')
                return global_status
        logging.info(f'User password {lmt.REMOTE_PASSWORD} for remote connection defined :-).')

        output = execute_command_and_report(f'user:get-token("{lmt.REMOTE_USER}","{lmt.REMOTE_PASSWORD}")')
        status = ('requesting token' in output)
        global_status = global_status and status
        if not status:
            logging.error(f'Unable to obtain a token from remote server.')
            return global_status
        cc_parameters_changed = True
        token = execute_command_and_report(f'user:token')
        uid = execute_command_and_report(f'websocket:remote:uid')
        logging.info(f'Token {token} obtained by CC from remote server :-).')
        logging.info(f'Uid {uid} obtained from CC :-).')

        # Saving if some parameters have changed
        if cc_parameters_changed:
            output = execute_command_and_report(f'system:save()')
            status = ('success' in output)
            global_status = global_status and status
            if not status:
                logging.warning(f'A problem occured trying to save the system.')
                return global_status
            logging.info(f'System saved :-).')
    return global_status

def disconnect_cc_from_server():
    """
    Disconnects the crescontrol from root.cre.science server.
    This must be passed directly to the CC, not via server
    """
    global_status = True
    output = execute_command_and_report(f'websocket:remote:disconnect()')
    status = ('success' in output)
    global_status = global_status and status
    if not status:
        logging.warning(f'A problem occured trying to disconnect from remote server.')
        return global_status
    logging.info(f'Disconnected from remote server :-).')

    output = execute_command_and_report(f'websocket:remote:allow-connection=0')
    status = ('0' in output)
    global_status = global_status and status
    if not status:
        logging.warning(f'A problem occured trying to deny remote connection.')
        return global_status
    logging.info(f'Deny of remote connection succesful :-).')

    output = execute_command_and_report(f'system:save()')
    status = ('success' in output)
    global_status = global_status and status
    if not status:
        logging.warning(f'A problem occured trying to save the system.')
        return global_status
    logging.info(f'System saved :-).')
    return global_status

def login_to_server():
    """
    Once the ws connection is established with the server, log in to it.
    WIP: if token is None, uid is too!!! Arrange this asap!!!
    """
    global token
    global uid
    global_status = True
    if token is None:
        logging.info(f'Obtaining token from server {lmt.REMOTE_API_URL}')
        token = execute_command_and_report(f'root:get-token("{lmt.REMOTE_ID}","{lmt.REMOTE_USER}","{lmt.REMOTE_PASSWORD}")', clean_answer=True, send_via_server=True, uid_in_query=False)
        uid = lmt.REMOTE_ID
        logging.info('Token obtained from server. :-)')
    output = execute_command_and_report(f'root:login("{lmt.REMOTE_UID}","{token}")', clean_answer=True, send_via_server=True, uid_in_query=False)
    status = (lmt.REMOTE_UID in output)
    global_status = global_status and status
    if not status:
        logging.error(f'login to server failed :-/.')
        return global_status
    logging.info(f'Login to server successful :-).')
    return global_status

# - commands query -------------------------------------------------------------
def clean_up_crescontrol_response(response):
    """
    Tidy up the response from CresControl.
    split around ::, takes the second part, and suppress chars ", {, and }.
    """
    return response.split("::")[-1].replace('"','').replace('{','').replace('}','')

def execute_command(query, clean_answer=True, send_via_server=False, uid_in_query=True):
    """
    sends a query to CresControl through websockets,
    gets the response,
    measure the delay it took between send and receive
    and return cleaned response and delay
    """
    global ws_on_cc
    global ws_on_server
    global token
    global uid
    start = time.time()
    time_taken = 0
    response = ''
    if (not send_via_server):
        if (ws_on_cc is None):
            logging.debug('ws_on_cc None, creating it')
            open_ws_on_cc()
            logging.debug(f'ws_on_cc opened in {time.time() - start}s')
        ws_on_cc.send(query)
        logging.debug(f'ws_on_cc.send(query) in {time.time() - start}s')
        response=ws_on_cc.recv()
        logging.debug(f'response=ws_on_cc.recv() in {time.time() - start}s')
        end = time.time()
    else:
        if (ws_on_server is None):
            logging.debug('ws_on_server None, creating it')
            if token is None:
                logging.info('Make sure CC allows remote connection and is loggued in:')
                status = connect_cc_to_server()
                if not status:
                    logging.error('Something went wrong during CC connection to remote, stopping :-/')
                    return response, time_taken
            open_ws_on_server()
            logging.debug(f'ws_on_server opened in {time.time() - start}s')
            status = login_to_server()
            if not status:
                logging.error('Something went wrong went trying to login to server, stopping')
                return response, time_taken
        if uid_in_query:
            query = f'{uid}:{query}'
        ws_on_server.send(query)
        logging.debug(f'ws_on_server.send(query) in {time.time() - start}s: {query}')
        response=ws_on_server.recv()
        logging.debug(f'response=ws_on_server.recv() in {time.time() - start}s: {response}')
        end = time.time()
    time_taken = end - start
    if clean_answer:
        response = clean_up_crescontrol_response(response)
        logging.debug(f'clean up of server response in {time.time() - start}s')
    return response, time_taken

def execute_command_and_report(query, clean_answer=True, send_via_server=False, uid_in_query=True):
    """
    Wrapping function of above function and add reporting/time to given args
    """
    response, time_taken = execute_command(query, clean_answer=clean_answer, send_via_server=send_via_server, uid_in_query=uid_in_query)
    logging.debug(f'\
   -> Query:                      {query}\n\
      <- Response (in {round_thousands_second_time_delta(time_taken)} secs.): {response}')
    return response

# - commands query higher level ------------------------------------------------
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

def wait_for_cc_frequency_recovery(minimum_frequency=400, minimum_time=5):
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

# - global command -------------------------------------------------------------
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

# ------------------------------------------------------------------------------
