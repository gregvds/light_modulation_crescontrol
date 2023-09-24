# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# Author: Gregoire Vandenschrick
# Date:   24/09/2023
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
# This little script creates a periodic schedule that check if switch-12v is enabled
# erroneously, and if so disables it.
if __name__ == "__main__":
    with open(os.path.join(LOCALDIRN, LOGFILE), 'w') as logFile:
        commands = (
            'schedule:set-enabled("disable_switch_12v",0)',
            'schedule:remove("disable_switch_12v")',
            'schedule:add("disable_switch_12v")',
            'schedule:set-period("disable_switch_12v",600)',
            'schedule:set-boolean-commands("disable_switch_12v","if(switch-12v:enabled,\\"switch-12v:enabled=0\\",\\"\\")","")',
            'schedule:set-timetable("disable_switch_12v","[[000,1],[001,0],[599,0]]")',
            'schedule:set-resolution("disable_switch_12v",2,1)',
            'schedule:set-enabled("disable_switch_12v",1)',
            'schedule:save("disable_switch_12v")',
            'system:save()'
        )
        for command in commands:
            response, time_taken = lml.execute_command(command, clean_answer=False)
            lml.printAndLog(str(response), logFile)
            lml.printAndLog(str(time_taken), logFile)

# ------------------------------------------------------------------------------
