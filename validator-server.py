from http.client import HTTPException
import json
import pathlib
import tempfile
import traceback
import os

from pydantic import ValidationError
from repack import repack

from fastapi import FastAPI, File, UploadFile, Response, status, Form
from typing import Annotated
import shutil

from curation_validator import EditCurationMeta, update_meta, validate_curation, get_tag_list_wiki, get_tag_list_file
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

@app.post("/edit-meta")
async def edit_meta(response: Response, path: str, metadata: Annotated[str | None, Form()] = None, logo: Annotated[UploadFile | None, File()] = None, screenshot: Annotated[UploadFile | None, File()] = None):
    try:
        l.debug(f"editing meta of provided file '{path}'")
        if metadata:
            try:
                print(metadata)
                # Parse the JSON string into the Pydantic model
                metadata_dict = json.loads(metadata)
                metadata = EditCurationMeta(**metadata_dict)
            except (json.JSONDecodeError, ValidationError) as e:
                raise HTTPException(status_code=400, detail=f"Invalid metadata JSON: {str(e)}")
        curation_errors, curation_warnings, filename = update_meta(path, metadata, logo, screenshot)
    
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
        "filename": os.path.basename(filename),
        "path": filename,
        "curation_errors": curation_errors,
        "curation_warnings": curation_warnings,
    }

# TODO this does not return all valid tags because the wiki page sucks
@app.get("/tags")
async def get_wiki_tags():
    return {"tags": get_tag_list_file() + get_tag_list_wiki()}

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
        errors, output_file = await repack(path)
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