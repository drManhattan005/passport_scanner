import json
import os
import re
import tempfile
from io import BytesIO
from typing import Any

import cv2
import numpy as np
from PIL import Image

from omnimrz import OmniMRZ
from omnimrz.parser import parse_mrz_fields
from omnimrz.validation import (
    checksum_mrz_validation,
    logical_mrz_validation,
    structural_mrz_validation,
)

MRZ_WEIGHTS = [7, 3, 1]

omni = OmniMRZ()


def mrz_char_value(ch: str) -> int:
    if ch.isdigit():
        return int(ch)
    if "A" <= ch <= "Z":
        return ord(ch) - ord("A") + 10
    if ch == "<":
        return 0
    raise ValueError(f"Invalid MRZ character: {ch}")


def mrz_checksum(text: str) -> str:
    total = 0
    for i, ch in enumerate(text):
        total += mrz_char_value(ch) * MRZ_WEIGHTS[i % 3]
    return str(total % 10)


def is_valid_check(text: str, check_digit: str) -> bool:
    return check_digit.isdigit() and mrz_checksum(text) == check_digit


def normalize_mrz_line(line: str) -> str:
    return re.sub(r"[^A-Z0-9<]", "", str(line).strip().upper().replace(" ", ""))


def normalize_mrz_text(text: str) -> str:
    return re.sub(r"[^A-Z0-9<]", "", str(text).upper().replace(" ", "").strip())


def image_bytes_to_bgr(content: bytes) -> np.ndarray:
    image = Image.open(BytesIO(content)).convert("RGB")
    rgb = np.array(image)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def validate_mrz_text(mrz_text: str) -> dict[str, Any]:
    lines = [
        normalize_mrz_line(line)
        for line in mrz_text.splitlines()
        if normalize_mrz_line(line)
    ]
    joined = "\n".join(lines)

    result = {
        "raw_mrz": joined or None,
        "structural_valid": False,
        "checksum_valid": False,
        "logical_valid": False,
        "parsed": {},
    }

    if not joined:
        return result

    try:
        result["structural_valid"] = bool(structural_mrz_validation(joined))
    except Exception:
        result["structural_valid"] = False

    try:
        result["checksum_valid"] = bool(checksum_mrz_validation(joined))
    except Exception:
        result["checksum_valid"] = False

    try:
        result["logical_valid"] = bool(logical_mrz_validation(joined))
    except Exception:
        result["logical_valid"] = False

    try:
        parsed = parse_mrz_fields(joined)
        if isinstance(parsed, dict):
            result["parsed"] = parsed
    except Exception:
        result["parsed"] = {}

    return result


def run_omnimrz_on_tempfile(content: bytes, suffix: str = ".jpg") -> Any:
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        return omni.process(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def debug_result_shape(obj: Any) -> dict[str, Any]:
    if isinstance(obj, dict):
        return {
            "type": "dict",
            "keys": list(obj.keys()),
        }
    if isinstance(obj, list):
        return {
            "type": "list",
            "length": len(obj),
            "item_types": [type(x).__name__ for x in obj[:5]],
        }
    return {
        "type": type(obj).__name__,
        "repr": str(obj)[:500],
    }


def extract_raw_mrz_from_result(result: Any) -> tuple[str | None, dict[str, Any], dict[str, Any]]:
    raw_mrz = None
    parsed = {}
    debug = {"result_shape": debug_result_shape(result)}

    if isinstance(result, str):
        raw_mrz = result

    elif isinstance(result, dict):
        extraction = result.get("extraction", {})
        parsed_data = result.get("parsed_data", {})
        parsed_block = parsed_data.get("data", {}) if isinstance(parsed_data, dict) else {}

        debug["top_level_keys"] = list(result.keys())
        if isinstance(extraction, dict):
            debug["extraction_keys"] = list(extraction.keys())
        if isinstance(parsed_data, dict):
            debug["parsed_data_keys"] = list(parsed_data.keys())
        if isinstance(parsed_block, dict):
            debug["parsed_data_data_keys"] = list(parsed_block.keys())

        raw_mrz = (
            result.get("mrz_text")
            or result.get("raw_mrz")
            or result.get("mrz")
            or result.get("text")
        )

        if not raw_mrz and isinstance(extraction, dict):
            raw_mrz = (
                extraction.get("mrz_text")
                or extraction.get("raw_mrz")
                or extraction.get("text")
                or extraction.get("clean_mrz")
            )

        if isinstance(parsed_block, dict) and parsed_block:
            parsed = parsed_block

    elif isinstance(result, list):
        clean_lines = [normalize_mrz_line(x) for x in result if isinstance(x, str)]
        raw_mrz = "\n".join([x for x in clean_lines if x]) or None

    return raw_mrz, parsed, debug


def map_parsed_fields(parsed: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_type": parsed.get("document_type") or parsed.get("type"),
        "issuing_country": parsed.get("issuing_country") or parsed.get("country") or parsed.get("issuingState"),
        "surname": parsed.get("surname"),
        "given_names": parsed.get("given_names") or parsed.get("givenNames"),
        "passport_number": parsed.get("passport_number") or parsed.get("document_number") or parsed.get("documentNumber"),
        "nationality": parsed.get("nationality"),
        "date_of_birth": parsed.get("date_of_birth") or parsed.get("dateOfBirth"),
        "sex": parsed.get("sex") or parsed.get("gender"),
        "expiration_date": parsed.get("expiration_date") or parsed.get("expiry_date") or parsed.get("date_of_expiry"),
        "personal_number": parsed.get("personal_number") or parsed.get("optional_data"),
    }


def extract_passport_info(content: bytes, filename: str | None = None) -> dict:
    _ = image_bytes_to_bgr(content)

    omni_result = run_omnimrz_on_tempfile(content)
    raw_mrz, parsed, debug = extract_raw_mrz_from_result(omni_result)

    validation = validate_mrz_text(raw_mrz or "")

    final_parsed = parsed or validation.get("parsed", {}) or {}
    mapped = map_parsed_fields(final_parsed)

    has_meaningful_data = any(
        mapped.get(key)
        for key in [
            "document_type",
            "issuing_country",
            "surname",
            "given_names",
            "passport_number",
            "nationality",
            "date_of_birth",
            "sex",
            "expiration_date",
            "personal_number",
        ]
    )

    note_parts = [f"Processed with OmniMRZ for {filename or 'uploaded image'}"]
    if not has_meaningful_data:
        note_parts.append("No parsed fields mapped from OmniMRZ response.")
        note_parts.append(json.dumps(debug, default=str)[:1200])

    return {
        "document_type": mapped.get("document_type"),
        "issuing_country": mapped.get("issuing_country"),
        "surname": mapped.get("surname"),
        "given_names": mapped.get("given_names"),
        "passport_number": mapped.get("passport_number"),
        "nationality": mapped.get("nationality"),
        "date_of_birth": mapped.get("date_of_birth"),
        "sex": mapped.get("sex"),
        "expiration_date": mapped.get("expiration_date"),
        "personal_number": mapped.get("personal_number"),
        "raw_mrz": validation.get("raw_mrz") or raw_mrz,
        "structural_valid": validation.get("structural_valid", False),
        "checksum_valid": validation.get("checksum_valid", False),
        "logical_valid": validation.get("logical_valid", False),
        "valid": bool(
            validation.get("structural_valid")
            and validation.get("checksum_valid")
            and validation.get("logical_valid")
        ),
        "note": " | ".join(note_parts),
    }
