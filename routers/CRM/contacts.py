from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import os
import uuid

from schema import contact
from core.database import get_db
import crud_ops
from model import Contact as ContactModel
from core.dependencies import get_current_user
from model.models import User

router = APIRouter()


UPLOAD_FOLDER = "uploads/profiles"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)



def convert_contact_output(db_contact: ContactModel):
    """Convert DB fields into frontend-friendly structure."""
    if not db_contact:
        return None

    contact_dict = db_contact.__dict__.copy()

    
    if db_contact.tags:
        contact_dict["tags"] = [tag.strip() for tag in db_contact.tags.split(",")]
    else:
        contact_dict["tags"] = []

    if db_contact.profile_photo:
        
        normalized_path = db_contact.profile_photo.replace("\\", "/")
        if not normalized_path.startswith("/"):
            contact_dict["profile_photo"] = f"/{normalized_path}"
        else:
            contact_dict["profile_photo"] = normalized_path
    else:
        contact_dict["profile_photo"] = None

    contact_dict.pop("_sa_instance_state", None)

    return contact_dict


  
@router.post("/", response_model=contact.ContactResponse)
def create_contact(contact_data: contact.ContactCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
   
    contact_dict = contact_data.dict()
    if isinstance(contact_dict.get("tags"), list):
        contact_dict["tags"] = ",".join(contact_dict["tags"]) if contact_dict["tags"] else None
    
   
    from schema.contact import ContactCreate
    contact_data_converted = ContactCreate(**contact_dict)
    
    db_contact = crud_ops.create_contact(db=db, contact=contact_data_converted, tenant_id=current_user.tenant_id)
    return convert_contact_output(db_contact)



@router.get("/", response_model=List[contact.ContactResponse])
def read_contacts(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_contacts = crud_ops.get_contacts(db=db, skip=skip, limit=limit, tenant_id=current_user.tenant_id)
    return [convert_contact_output(c) for c in db_contacts]

 
@router.get("/{contact_id}", response_model=contact.ContactResponse)
def read_contact(contact_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_contact = crud_ops.get_contact(db=db, contact_id=contact_id, tenant_id=current_user.tenant_id)
    if not db_contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return convert_contact_output(db_contact)

 
@router.put("/{contact_id}", response_model=contact.ContactResponse)
def update_contact(contact_id: int, updated: contact.ContactUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
   
    db_contact = crud_ops.get_contact(db=db, contact_id=contact_id, tenant_id=current_user.tenant_id)
    if not db_contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    
    updated_dict = updated.dict(exclude_unset=True)
    if "tags" in updated_dict and isinstance(updated_dict["tags"], list):
        updated_dict["tags"] = ",".join(updated_dict["tags"]) if updated_dict["tags"] else None
    
   
    for key, value in updated_dict.items():
        setattr(db_contact, key, value)
    
    db.commit()
    db.refresh(db_contact)
    return convert_contact_output(db_contact)

 
@router.delete("/{contact_id}")
def delete_contact(contact_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ok = crud_ops.delete_contact(db=db, contact_id=contact_id, tenant_id=current_user.tenant_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"detail": "Contact deleted successfully"}



@router.put("/{contact_id}/profile-photo")
def update_profile_photo(
    contact_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    db_contact = db.query(ContactModel).filter(ContactModel.id == contact_id).first()
    if not db_contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    
    import uuid
    file_extension = os.path.splitext(file.filename)[1] if file.filename else '.jpg'
    unique_filename = f"profile_{contact_id}_{uuid.uuid4().hex[:8]}{file_extension}"
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename).replace("\\", "/")

    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())

   
    db_contact.profile_photo = file_path
    db.commit()
    db.refresh(db_contact)

    
    normalized_path = file_path.replace("\\", "/")
    if not normalized_path.startswith("/"):
        normalized_path = f"/{normalized_path}"

    return {
        "message": "Profile photo updated successfully",
        "profile_photo": normalized_path
    }