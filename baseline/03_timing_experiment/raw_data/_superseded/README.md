# _superseded/: stopped attempts (not used)

These runs were stopped and then restarted from scratch under the correct conditions. They are kept for transparency only. **No result in the report uses them.**

| Folder | What happened |
|---|---|
| `e3a_aborted/` | First E3a attempt. It started with Wi-Fi on and before the screen brightness was fixed, so it was stopped after the first runs. The complete E3a is in `../e3a` |
| `bl_energy_old_223915/` | First energy attempt. The script hung after run 1: `wait` also waited on the sudo keep-alive loop (fixed with `wait $!`). It was stopped and rerun; the complete E7 is in `../bl_energy` |
