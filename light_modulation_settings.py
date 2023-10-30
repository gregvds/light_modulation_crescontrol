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
SMTP_SERVER = ''
SENDER_EMAIL = ''
SENDER_PASSWORD = ''
RECEIVER_EMAIL = ''

# -- Crescontrol url - IP address or domain name (SSID)
RPI_IP = ''                                     # IP of the Raspberry pi executing the main script
CRESCONTROL_IP = ''                             # IP of the CresControl where schedule are to be sent
CRESCONTROL_URL = f'http://{CRESCONTROL_IP}'
CRESCONTROL_CPU_ID = ''                         # curl http://CRESCONTROL_IP/commands?query=\"system:cpu-id\"
CRESCONTROL_ACCESS_POINT_KEY = ''

REMOTE_API_URL = "root.cre.science"
REMOTE_ID = ''                                  # curl http://CRESCONTROL_IP/commands?query=\"websocket:remote:uid\"
REMOTE_UID = ''                                 # A user id for the remote API server (choose one you like :-))
REMOTE_USER = ''                                # your login at Cre.Science website and hub
REMOTE_PASSWORD = ''                            # your paswd at Cre.Science website and hub

PAUSE_BETWEEN_QUERIES = 10                      # seconds, this to allow the CC pile to be treated in case of large query

# Cre.Science json database url
CS_JSN_URL = "https://raw.cre.science/products/modules/modules/"

# lat lon of kind of Poffader in the northern hemispher
# adapt this to your place to follow your daylight or to simulate daylight of
# any place on Earth.
LATITUDE = 29.1288
LONGITUDE = 4.3947
TIMEZONE = 2
