# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# Author: Gregoire Vandenschrick
# Date:   14/09/2023
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

# -- Import for the generation of data_points and communications
import light_modulation_library as lml
import os
import time

# ------------------------------------------------------------------------------

# -- log file. Please be sure you have write access to LOCALDIRN
LOCALDIRN   = '.'
LOGFILE     = os.path.basename(__file__).replace('py','log')

# -- local constants definitions
local_ip = lml.get_local_ip()

# ------------------------------------------------------------------------------
# -- Main use of code ----------------------------------------------------------
# This little script creates a schedule that limits the activity of the Crescontrol
# led during the night to errors only mode. Crescontrol full led behaviour is restored
# between 07:30 and 20:00.
if __name__ == "__main__":
    with open(os.path.join(LOCALDIRN, LOGFILE), 'w') as logFile:
        commands = (
            'schedule:set-enabled("led_off_at_night",0)',
            'schedule:remove("led_off_at_night")',
            'schedule:add("led_off_at_night")',
            'schedule:set-boolean-commands("led_off_at_night","led:verbosity=3","led:verbosity=1")',
            'schedule:set-timetable("led_off_at_night","[[00000,0],[26940,0],[27000,1],[71940,1],[72000,0]]")',
            'schedule:set-resolution("led_off_at_night",60,1)',
            'schedule:set-enabled("led_off_at_night",1)',
            'schedule:save("led_off_at_night")',
            'system:save()'
        )
        for command in commands:
            response, time_taken = lml.execute_command(command, clean_answer=False)
            lml.printAndLog(str(response), logFile)
            lml.printAndLog(str(time_taken), logFile)

# ------------------------------------------------------------------------------