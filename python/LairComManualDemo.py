#Manual control demo of the LairCom library. This just prints out a list
#of the bank 0 voltages.
from LairCom0_4 import LairCom
from LairCom0_4 import MCGas
import time

try:
    lc=LairCom()
    lc.clearControllers()
    lc.loadController(MCGas())
    while True:
        time.sleep(1)
        lc.tick()
        lc.req("gas")
        v=lc.get("gas")
        if True:
            print("Voltages "+str(v))
            v=False
except KeyboardInterrupt:
    print("Beendet")
