from typing import List, Optional

from pydantic import BaseModel


class PassportData(BaseModel):
    document_type: Optional[str] = None
    issuing_country: Optional[str] = None
    surname: Optional[str] = None
    given_names: Optional[str] = None
    passport_number: Optional[str] = None
    nationality: Optional[str] = None
    date_of_birth: Optional[str] = None
    sex: Optional[str] = None
    expiration_date: Optional[str] = None
    personal_number: Optional[str] = None
    raw_mrz: Optional[str] = None
    structural_valid: bool = False
    checksum_valid: bool = False
    logical_valid: bool = False
    valid: bool = False
    note: Optional[str] = None


class FileResult(BaseModel):
    filename: str
    status: str
    error: Optional[str] = None
    data: Optional[PassportData] = None


class BatchResponse(BaseModel):
    total_uploaded: int
    total_processed: int
    results: List[FileResult]
