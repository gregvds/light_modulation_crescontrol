# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# Author: Gregoire Vandenschrick
# Date:   20/09/2023
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

# -- Constant for the generation of data_points
# Time step in minutes (adjustable) used for precise computation only
# schedules are reduced to 32 points before being sent to CresControl
TIME_STEP_MINUTES = 5

# -- Constants for email reporting
# ! COMPLETE THESE !
SMTP_SERVER = ""
SENDER_EMAIL = ""
SENDER_PASSWORD = ""
RECEIVER_EMAIL = ""
RPI_IP = ""                                     # IP of the Raspberry pi executing the main script
CRESCONTROL_IP = ""                             # IP of the CresControl where schedule are to be sent
CRESCONTROL_URL = f'http://{CRESCONTROL_IP}'
CRESCONTROL_CPU_ID = ''                         # curl http://CRESCONTROL_IP/commands?query=\"system:cpu-id\"
PAUSE_BETWEEN_QUERIES = 10                      # seconds, this to allow the CC pile to be treated in case of large query

# lat lon of kind of Poffader in the northern hemispher
# adapt this to your place to follow your daylight or to simulate daylight of
# any place on Earth.
LATITUDE = 29.1288
LONGITUDE = 4.3947
TIMEZONE = 2
