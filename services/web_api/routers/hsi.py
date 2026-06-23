from fastapi import APIRouter

router = APIRouter()


@router.get("/presets")
def list_presets():
    return {"presets": [], "note": "Requires build_csi integration"}


@router.get("/calibration")
def get_calibration():
    return {"profiles": []}
