// Logs the signals the Phase-2 energy monitor will read, once per second:
// epoch seconds, ProcessInfo.thermalState, Low Power Mode.
import Foundation
setvbuf(stdout, nil, _IOLBF, 0)
let names = ["nominal", "fair", "serious", "critical"]
print("epoch_s,thermal_state,low_power_mode")
while true {
    let p = ProcessInfo.processInfo
    print("\(Date().timeIntervalSince1970),\(names[p.thermalState.rawValue]),\(p.isLowPowerModeEnabled)")
    Thread.sleep(forTimeInterval: 1.0)
}
