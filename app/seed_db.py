from database import SessionLocal, Prompt, init_db

def seed():
    init_db()
    db = SessionLocal()
    
    db.query(Prompt).delete()  # Clear existing data
    
    db.add_all([
        Prompt(id=1, text = "Explain cardiovascular risk factors in simple terms."),
        Prompt(id=2, text = "Give a 5-point summary of hypertension management."),
        Prompt(id=3, text = "Write lifestyle advice for preventing heart disease.")
    ])
    
    db.commit()
    db.close()
    print("Seeded prompts.db with IDs 1, 2, 3")
    
if __name__ == "__main__":
    print("Running seed_db.py ...")
    seed()
