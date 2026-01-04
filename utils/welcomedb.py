#
# Greetings Database for Spy Bot
# Optimized logic for Welcome and Goodbye messages
#

from Spy.core.mongo import mongodb

# Database Collection
greetingsdb = mongodb.greetings

# --- Welcome Functions ---

async def set_welcome(chat_id: int, message: str, raw_text: str, file_id: str):
    """Chat ke liye Welcome message set karta hai."""
    update_data = {
        "message": message,
        "raw_text": raw_text,
        "file_id": file_id,
        "type": "welcome",
    }
    return await greetingsdb.update_one(
        {"chat_id": chat_id, "type": "welcome"}, 
        {"$set": update_data}, 
        upsert=True
    )

async def get_welcome(chat_id: int) -> (str, str, str):
    """Welcome message fetch karta hai."""
    data = await greetingsdb.find_one({"chat_id": chat_id, "type": "welcome"})
    if not data:
        return "", "", ""
    return data.get("message", ""), data.get("raw_text", ""), data.get("file_id", "")

async def del_welcome(chat_id: int):
    """Welcome message delete karta hai."""
    return await greetingsdb.delete_one({"chat_id": chat_id, "type": "welcome"})


# --- Goodbye Functions ---

async def set_goodbye(chat_id: int, message: str, raw_text: str, file_id: str):
    """Chat ke liye Goodbye message set karta hai."""
    update_data = {
        "message": message,
        "raw_text": raw_text,
        "file_id": file_id,
        "type": "goodbye",
    }
    return await greetingsdb.update_one(
        {"chat_id": chat_id, "type": "goodbye"}, 
        {"$set": update_data}, 
        upsert=True
    )

async def get_goodbye(chat_id: int) -> (str, str, str):
    """Goodbye message fetch karta hai."""
    data = await greetingsdb.find_one({"chat_id": chat_id, "type": "goodbye"})
    if not data:
        return "", "", ""
    return data.get("message", ""), data.get("raw_text", ""), data.get("file_id", "")

async def del_goodbye(chat_id: int):
    """Goodbye message delete karta hai."""
    return await greetingsdb.delete_one({"chat_id": chat_id, "type": "goodbye"})


# --- Toggle Functions (On/Off) ---

async def set_greetings_on(chat_id: int, gtype: str) -> bool:
    """Welcome ya Goodbye module ko ON karta hai."""
    key = "welcome_on" if gtype == "welcome" else "goodbye_on"
    
    result = await greetingsdb.update_one(
        {"chat_id": chat_id}, 
        {"$set": {key: True}}, 
        upsert=True
    )
    return result.modified_count > 0 or result.upserted_id is not None

async def set_greetings_off(chat_id: int, gtype: str) -> bool:
    """Welcome ya Goodbye module ko OFF karta hai."""
    key = "welcome_on" if gtype == "welcome" else "goodbye_on"
    
    result = await greetingsdb.update_one(
        {"chat_id": chat_id}, 
        {"$set": {key: False}}, 
        upsert=True
    )
    return result.modified_count > 0 or result.upserted_id is not None

async def is_greetings_on(chat_id: int, gtype: str) -> bool:
    """Check karta hai ki module ON hai ya nahi."""
    key = "welcome_on" if gtype == "welcome" else "goodbye_on"
    
    data = await greetingsdb.find_one({"chat_id": chat_id})
    if not data:
        return False
    return data.get(key, False)
