import pathlib
import tempfile

from fastapi import FastAPI, File, UploadFile
import shutil

from curation_validator import validate_curation
from logger import getLogger

l = getLogger("api")

app = FastAPI()


@app.post("/upload/")
async def create_upload_file(file: UploadFile = File(...)):
    l.debug(f"received file '{file.filename}'")
    base_path = tempfile.mkdtemp(prefix="curation_validator_")
    new_filepath = base_path + "/file" + pathlib.Path(file.filename).suffix
    with open(new_filepath, "wb") as dest:
        l.debug(f"copying file '{file.filename}' into '{dest}'.")
        shutil.copyfileobj(file.file, dest)
    curation_errors, curation_warnings, is_extreme, curation_type, meta, image_dict = validate_curation(new_filepath)

    l.debug(f"removing '{new_filepath}'.")
    shutil.rmtree(base_path)
    return {
        "filename": file.filename,
        "path": new_filepath,
        "curation_errors": curation_errors,
        "curation_warnings": curation_warnings,
        "is_extreme": is_extreme,
        "curation_type": curation_type,
        "meta": meta,
        "images": image_dict
    }
