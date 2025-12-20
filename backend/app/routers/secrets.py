from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.middleware.rate_limit import limiter
from app.schemas.secret import (
    SecretCreate,
    SecretCreateResponse,
    SecretEditRequest,
    SecretEditResponse,
    SecretRetrieveResponse,
    SecretStatusResponse,
)
from app.services.pow_service import verify_pow
from app.services.secret_service import (
    create_secret,
    extend_unlock_date,
    find_secret_by_decrypt_token,
    find_secret_by_edit_token,
    get_secret_status,
    retrieve_secret,
)

router = APIRouter()


def extract_bearer_token(authorization: str = Header(...)) -> str:
    """Extract token from Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    return authorization[7:]


@router.post("/secrets", response_model=SecretCreateResponse, status_code=201)
@limiter.limit(settings.rate_limit_creates)
async def create_new_secret(
    request: Request,
    secret_data: SecretCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new time-locked secret.

    Requires a valid proof-of-work solution.
    """
    # Verify proof of work
    try:
        verify_pow(
            db=db,
            challenge_id=secret_data.pow_proof.challenge_id,
            nonce=secret_data.pow_proof.nonce,
            counter=secret_data.pow_proof.counter,
            payload_hash=secret_data.pow_proof.payload_hash,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Create the secret
    secret = create_secret(
        db=db,
        ciphertext_b64=secret_data.ciphertext,
        iv_b64=secret_data.iv,
        auth_tag_b64=secret_data.auth_tag,
        unlock_at=secret_data.unlock_at,
        edit_token=secret_data.edit_token,
        decrypt_token=secret_data.decrypt_token,
    )

    return SecretCreateResponse(
        secret_id=secret.id,
        unlock_at=secret.unlock_at,
        created_at=secret.created_at,
    )


@router.put("/secrets/edit", response_model=SecretEditResponse)
@limiter.limit(settings.rate_limit_retrieves)
async def edit_secret(
    request: Request,
    edit_data: SecretEditRequest,
    authorization: str = Header(...),
    db: Session = Depends(get_db),
):
    """
    Extend the unlock date of a secret.

    Requires the edit token in the Authorization header.
    """
    edit_token = extract_bearer_token(authorization)

    secret = find_secret_by_edit_token(db, edit_token)
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")

    try:
        updated_secret = extend_unlock_date(db, secret, edit_data.unlock_at)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return SecretEditResponse(
        secret_id=updated_secret.id,
        unlock_at=updated_secret.unlock_at,
        updated_at=updated_secret.unlock_at,  # Using unlock_at as proxy for updated_at
    )


@router.get("/secrets/retrieve", response_model=SecretRetrieveResponse)
@limiter.limit(settings.rate_limit_retrieves)
async def retrieve_secret_endpoint(
    request: Request,
    authorization: str = Header(...),
    db: Session = Depends(get_db),
):
    """
    Retrieve a secret's encrypted content.

    This is a ONE-TIME operation. After successful retrieval post-unlock,
    the secret is permanently deleted.
    """
    decrypt_token = extract_bearer_token(authorization)

    secret = find_secret_by_decrypt_token(db, decrypt_token)
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")

    result = retrieve_secret(db, secret)

    if result["status"] == "pending":
        raise HTTPException(
            status_code=403,
            detail={
                "status": "pending",
                "unlock_at": result["unlock_at"].isoformat(),
                "message": result["message"],
            },
        )

    if result["status"] == "retrieved":
        raise HTTPException(status_code=410, detail=result["message"])

    return SecretRetrieveResponse(**result)


@router.get("/secrets/status", response_model=SecretStatusResponse)
@limiter.limit(settings.rate_limit_retrieves)
async def get_status(
    request: Request,
    authorization: str = Header(...),
    db: Session = Depends(get_db),
):
    """
    Check the status of a secret without triggering one-time deletion.

    Useful for showing countdown timers in the UI.
    """
    decrypt_token = extract_bearer_token(authorization)

    secret = find_secret_by_decrypt_token(db, decrypt_token)
    if not secret:
        return SecretStatusResponse(exists=False, status="not_found")

    status = get_secret_status(db, secret)
    return SecretStatusResponse(**status)
