# TODO: Das hier muss aufjedenfall refactored werden
def extract_user_message(messages):
    """Extrahiert die Benutzernachricht aus dem messages-Objekt."""
    # Wenn messages ein Dict mit einem "messages"-Schlüssel ist
    if isinstance(messages, dict) and "messages" in messages:
        messages_list = messages["messages"]
    else:
        messages_list = messages
            
    # Durchlaufe die Nachrichten und finde die Benutzernachricht
    for message in messages_list:
        if hasattr(message, "type") and message.type == "human":
            return message.content
        elif isinstance(message, dict) and message.get("role") == "user":
            return message.get("content", "")
    return ""
    