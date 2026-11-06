"""MOCK network serviceability check. The real thing would call a coverage and feasibility service.

Synthetic rule so the demo can show every branch: pincodes ending in 9 have no fibre (5G AirFiber still works),
pincodes ending in 8 or 9 cannot get a leased line, and pincodes ending in 00 need a surveyor (nothing confirmed).
"""
import re


def check(pincode):
    p = re.sub(r"\D", "", str(pincode or ""))
    if len(p) != 6:
        return {"known": False, "fibre": True, "airfiber": True, "leased": True, "source": "no pincode given, assumed serviceable"}
    last, last2 = int(p[-1]), int(p[-2:])
    if last2 == 0:
        return {"known": True, "fibre": False, "airfiber": False, "leased": False, "source": "mock: needs a site survey"}
    return {"known": True, "fibre": last != 9, "airfiber": True, "leased": last not in (8, 9), "source": "mock coverage data"}
