#!/usr/bin/env python3
"""Battery logger for Step 6: once a second, the battery's own readings (ioreg AppleSmartBattery): charge %, voltage,
current (negative = discharging), power = V x I, charger connected, charging, temperature; plus Low Power Mode.
usage: bat.py <out.csv>   (runs until killed)"""
import plistlib, subprocess, sys, time

out = open(sys.argv[1], "a", buffering=1)
if out.tell() == 0:
    out.write("t_epoch_s,pct,mV,mA,W,external,charging,temp_c,lpm\n")
lpm, tl = "", 0
while True:
    try:
        b = plistlib.loads(subprocess.run(["ioreg", "-rn", "AppleSmartBattery", "-a"], capture_output=True).stdout)[0]
        mv = int(b.get("Voltage", 0))
        ma = int(b.get("InstantAmperage", b.get("Amperage", 0)))
        if ma >= 2 ** 63:
            ma -= 2 ** 64
        if time.time() - tl > 10:
            g = subprocess.run(["pmset", "-g"], capture_output=True, text=True).stdout
            lpm = next((l.split()[-1] for l in g.splitlines() if "lowpowermode" in l), ""); tl = time.time()
        out.write(f"{time.time():.3f},{b.get('CurrentCapacity', '')},{mv},{ma},{mv * ma / 1e6:.3f},"
                  f"{int(bool(b.get('ExternalConnected')))},{int(bool(b.get('IsCharging')))},"
                  f"{int(b.get('Temperature', 0)) / 100:.1f},{lpm}\n")
    except Exception as e:
        out.write(f"{time.time():.3f},,,,,,,,err {type(e).__name__}\n")
    time.sleep(1)
