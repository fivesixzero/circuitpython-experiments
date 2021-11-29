# Print register state for all APDS-9960 registers without using the driver

import supervisor
from config_regs_apds import ConfigRegsAPDS
from clue_keypad import ClueKeys

regs = ConfigRegsAPDS()
keys = ClueKeys()

# Getting a clean state requires a power cycle, so lets only dump the data
#    once the user's had a chance to re-connect their serial console
print("RunReason: {}".format(supervisor.runtime.run_reason))
if supervisor.runtime.run_reason is supervisor.RunReason.STARTUP:
    print("Waiting for keypress before continuing")
    keys.wait_for_keypress()

regs.print_reg_states()