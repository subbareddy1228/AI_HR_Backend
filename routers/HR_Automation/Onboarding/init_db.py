from model.models import SessionLocal, Document, init_db

init_db()

required_docs = ["ID", "Tax", "Certificates"]

db = SessionLocal()
try:
    for doc_name in required_docs:
        exists = db.query(Document).filter(Document.name == doc_name).first()
        if not exists:
           doc = Document(name=doc_name)
           db.add(doc)
    db.commit()
finally:
    db.close()

print("Database initialized with required documents.")
