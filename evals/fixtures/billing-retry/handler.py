def handle_payment(event, db):
    if db.event_exists(event["id"]):
        return "already_processed"
    db.credit_balance(event["account_id"], event["amount"])
    db.save_processed_event(event["id"])
    return "credited"
