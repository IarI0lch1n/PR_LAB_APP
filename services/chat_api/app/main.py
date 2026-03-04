from fastapi import FastAPI, HTTPException
import httpx

app = FastAPI(title="Chat Service", version="1.1")

FILE_API_URL = "http://file_api:8002"

messages: list[dict] = []
message_id_counter = 1


@app.get("/health")
def health():
    return {"status": "ok", "service": "chat_api"}


@app.get("/messages")
def get_messages():
    return {"messages": messages}


def _ensure_file_exists(filename: str) -> None:
    try:
        resp = httpx.get(f"{FILE_API_URL}/files", timeout=5.0)
        resp.raise_for_status()
        files = resp.json().get("files", [])
    except Exception:
        raise HTTPException(status_code=500, detail="File service unavailable")

    if filename not in files:
        raise HTTPException(status_code=404, detail="Attached file not found in file service")


@app.post("/messages")
def send_message(text: str, filename: str | None = None):
    global message_id_counter

    if filename:
        _ensure_file_exists(filename)

    message = {"id": message_id_counter, "text": text, "file": filename}
    messages.append(message)
    message_id_counter += 1
    return message


@app.put("/messages/{message_id}")
def update_message(message_id: int, text: str | None = None, filename: str | None = None):
    # найти сообщение
    for m in messages:
        if m["id"] == message_id:
            # обновить поля (если передали)
            if text is not None:
                m["text"] = text

            if filename is not None:
                if filename != "":
                    _ensure_file_exists(filename)
                    m["file"] = filename
                else:
                    # если filename пустая строка — “удалить привязку файла”
                    m["file"] = None

            return m

    raise HTTPException(status_code=404, detail="Message not found")


@app.delete("/messages/{message_id}")
def delete_message(message_id: int):
    for i, m in enumerate(messages):
        if m["id"] == message_id:
            deleted = messages.pop(i)
            return {"deleted": deleted}

    raise HTTPException(status_code=404, detail="Message not found")