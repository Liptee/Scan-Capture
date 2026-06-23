from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/status")
def camera_status(request: Request):
    service = request.app.state.capture_service
    if service is None:
        return {
            "connected": False,
            "model": None,
            "serial": None,
            "vendor": None,
            "usb_speed": None,
            "preview_active": False,
            "recording_active": False,
            "error": "Capture service not initialized",
        }
    return service.get_status()
