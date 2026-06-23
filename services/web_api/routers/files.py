from fastapi import APIRouter

router = APIRouter()


@router.get("/recordings")
def list_recording_files():
    return {"files": []}
