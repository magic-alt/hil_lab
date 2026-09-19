#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
CHECKS={
    "fieldbus/ethercat/igh/cia402_cycle.c":[
        "ecrt_master_application_time","ecrt_domain_state",
        "ecrt_master_sync_reference_clock","ecrt_master_sync_slave_clocks",
        "EC_WC_COMPLETE","enable_drive"
    ],
    "fieldbus/ethercat/soem/soem_cycle.c":[
        "ec_configdc","ec_send_processdata","ec_receive_processdata",
        "expected_wkc","ec_DCtime"
    ],
    "fieldbus/canopen/sdo.py":["0x2F","0x2B","0x23","SdoAbort"],
    "fieldbus/canopen/cia402.py":["0x6040","0x6041","OPERATION_ENABLED"],
    "fieldbus/canopen/pdo.py":["mapping_value","0x80000000","configure_pdo_mapping"],
    "lab/labgrid/client.py":["acquire","release","labgrid-client"],
    "lab/session.py":["force_safe(True)"],
}
def main():
    errors=[]
    for rel,tokens in CHECKS.items():
        path=ROOT/rel
        if not path.exists():
            errors.append(f"missing {rel}"); continue
        text=path.read_text(encoding="utf-8")
        for token in tokens:
            if token not in text: errors.append(f"{rel} missing {token}")
    if errors:
        print("Industrial HIL static check FAILED")
        for error in errors: print(" -",error)
        return 1
    print("Industrial HIL static check PASSED")
    return 0
if __name__=="__main__": sys.exit(main())
