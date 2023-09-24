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
# This little script allow the user button to go from the normal schedules to a
# light level more gentle to the eyes and back to normal.
# a single push toggles between gentle lighting to observe plants growth and normal scheduled intensities.
# a double push toggle all light off and on.
# Adapt the names of your schedules in
#   scripts "observation_light" and "light_off"
#       :set-start-script and :set-stop-script
# Adapt variables
# out_a_voltage_single_push, out_b_voltage_single_push, out_c_voltage_single_push
# out_all_voltage_double_push to your likings and configuration
if __name__ == "__main__":
    with open(os.path.join(LOCALDIRN, LOGFILE), 'w') as logFile:
        # definition of light outputs for single and double pushes
        out_a_voltage_single_push = 2.5
        out_b_voltage_single_push = 2.5
        out_c_voltage_single_push = 0
        out_all_voltage_double_push = 0
        commands = (
            'script:remove("observation_light")',
            'script:add("observation_light")',
            f'script:set-start-script("observation_light","schedule:set-enabled(\\"schedule_3500\\",0);schedule:set-enabled(\\"schedule_5000\\",0);schedule:set-enabled(\\"schedule_385\\",0);out-a:voltage={out_a_voltage_single_push};out-b:voltage={out_b_voltage_single_push};out-c:voltage={out_c_voltage_single_push}")',
            'script:set-stop-script("observation_light","schedule:set-enabled(\\"schedule_3500\\",1);schedule:set-enabled(\\"schedule_5000\\",1);schedule:set-enabled(\\"schedule_385\\",1)")',
            'script:save("observation_light")',
            'user-button:single-press-command="if(script:get-running(\\"observation_light\\"),\\"script:stop(\\\\"observation_light\\\\")\\",\\"script:start(\\\\"observation_light\\\\")\\")"',
            'script:remove("light_off")',
            'script:add("light_off")',
            f'script:set-start-script("light_off","schedule:set-enabled(\\"schedule_3500\\",0);schedule:set-enabled(\\"schedule_5000\\",0);schedule:set-enabled(\\"schedule_385\\",0);out-a:voltage={out_all_voltage_double_push};out-b:voltage={out_all_voltage_double_push};out-c:voltage={out_all_voltage_double_push}")',
            'script:set-stop-script("light_off","schedule:set-enabled(\\"schedule_3500\\",1);schedule:set-enabled(\\"schedule_5000\\",1);schedule:set-enabled(\\"schedule_385\\",1)")',
            'script:save("light_off")',
            'user-button:double-press-command="script:stop(\\"light_off\\")"',
            'user-button:double-press-delay=1000',
            'system:save()'
        )
        for command in commands:
            response, time_taken = lml.execute_command(command, clean_answer=False)
            lml.printAndLog(str(response), logFile)
            lml.printAndLog(str(time_taken), logFile)

# ------------------------------------------------------------------------------
