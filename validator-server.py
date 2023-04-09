import pathlib
import tempfile
import traceback
from repack import repack

from fastapi import FastAPI, File, UploadFile, Response, status
import shutil

from curation_validator import validate_curation, get_tag_list_wiki, get_tag_list_file
from logger import getLogger

l = getLogger("api")

app = FastAPI()


@app.post("/upload")
async def create_upload_file(response: Response, file: UploadFile = File(...)):
    l.debug(f"received file '{file.filename}'")

    base_path = tempfile.mkdtemp(prefix="curation_validator_")
    new_filepath = base_path + "/file" + pathlib.Path(file.filename).suffix

    with open(new_filepath, "wb") as dest:
        l.debug(f"copying file '{file.filename}' into '{new_filepath}'.")
        shutil.copyfileobj(file.file, dest)
    try:
        curation_errors, curation_warnings, is_extreme, curation_type, meta, image_dict = validate_curation(
            new_filepath)

    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "exception": "".join(
                traceback.format_exception(
                    etype=type(e), value=e, tb=e.__traceback__
                )
            )
        }

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


# just hand over absolute path to the file instead of uploading it, saves some unnecessary copying ay?
@app.post("/provide-path")
async def provide_file(response: Response, path: str):
    try:
        l.debug(f"validating provided file '{path}'")
        curation_errors, curation_warnings, is_extreme, curation_type, meta, image_dict = validate_curation(path)

    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "exception": "".join(
                traceback.format_exception(
                    etype=type(e), value=e, tb=e.__traceback__
                )
            )
        }

    return {
        "filename": pathlib.Path(path).name,
        "path": path,
        "curation_errors": curation_errors,
        "curation_warnings": curation_warnings,
        "is_extreme": is_extreme,
        "curation_type": curation_type,
        "meta": meta,
        "images": image_dict
    }

# TODO this does not return all valid tags because the wiki page sucks
@app.get("/tags")
async def get_wiki_tags():
    return {"tags": get_tag_list_wiki() + get_tag_list_file()}

@app.post("/pack-path")
async def pack_path(response: Response, path: str):
    try:
        l.debug(f"validating provided file before import '{path}'")
        curation_errors, curation_warnings, is_extreme, curation_type, meta, image_dict = validate_curation(path)

    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "exception": "".join(
                traceback.format_exception(
                    etype=type(e), value=e, tb=e.__traceback__
                )
            )
        }

    try:
        l.debug(f"packing '{path}'")
        errors, output_file = repack(path)
        if len(errors) > 0:
            return {
                "error": "error repacking curation"
            }
        else:
            return {
                "path": output_file,
                "meta": meta,
                "images": image_dict
            }
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "exception": "".join(
                traceback.format_exception(
                    etype=type(e), value=e, tb=e.__traceback__
                )
            )
        }
