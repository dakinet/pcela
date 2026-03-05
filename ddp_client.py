"""
Meteor DDP klijent preko SockJS WebSocket-a.
Koristi se za komunikaciju sa TVI platformom.
"""

import json
import random
import string
import threading
import time

import websocket


class MeteorDDP:
    def __init__(self, server_url: str):
        # server_url: npr. "wss://tvi.meteor.teaminoving2.rs"
        self.server_url = server_url.rstrip("/")
        self.ws = None
        self.connected = False
        self.user_id: str | None = None
        self._msg_id = 0
        self._lock = threading.Lock()
        self._pending: dict[str, threading.Event] = {}
        self._results: dict[str, dict] = {}
        # Za pretrazivanje (subscriptions)
        self._sub_pending: dict[str, threading.Event] = {}
        self._sub_docs: list[dict] = []
        self._sub_collecting: bool = False
        # Za request_times kolekciju
        self._rt_docs: list[dict] = []
        self._rt_collecting: bool = False
        self._rt_last_added: float = 0.0   # timestamp poslednjeg "added" za request_times

    # ── interni helperi ───────────────────────────────────────────────────────

    def _sockjs_url(self) -> str:
        srv = "".join(random.choices(string.digits, k=3))
        sess = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return f"{self.server_url}/sockjs/{srv}/{sess}/websocket"

    def _next_id(self) -> str:
        with self._lock:
            self._msg_id += 1
            return str(self._msg_id)

    def _send(self, obj: dict) -> None:
        self.ws.send(json.dumps([json.dumps(obj)]))

    # ── WebSocket callbacks ───────────────────────────────────────────────────

    def _on_open(self, ws):
        self._send({"msg": "connect", "version": "1", "support": ["1"]})

    def _on_message(self, ws, raw: str):
        if raw in ("o", "h"):
            return
        if raw.startswith("c"):
            return
        if raw.startswith("a"):
            try:
                for item in json.loads(raw[1:]):
                    self._dispatch(json.loads(item))
            except Exception:
                pass

    def _on_error(self, ws, err):
        pass

    def _on_close(self, ws, code, msg):
        self.connected = False

    def _dispatch(self, msg: dict) -> None:
        t = msg.get("msg")
        if t == "connected":
            self.connected = True
        elif t == "ping":
            self._send({"msg": "pong"})
        elif t == "result":
            mid = msg.get("id", "")
            self._results[mid] = msg
            if mid in self._pending:
                self._pending[mid].set()
        elif t == "added":
            col = msg.get("collection", "")
            doc_id = msg.get("id", "")
            fields = msg.get("fields", {})
            if self._sub_collecting:
                self._sub_docs.append({"_id": doc_id, **fields})
            if self._rt_collecting and col == "request_times":
                with self._lock:
                    self._rt_docs.append({"_id": doc_id, **fields})
                    self._rt_last_added = time.time()
        elif t == "ready":
            for sub_id in msg.get("subs", []):
                if sub_id in self._sub_pending:
                    self._sub_pending[sub_id].set()

    # ── javni API ─────────────────────────────────────────────────────────────

    def connect(self, timeout: float = 10.0) -> bool:
        self.ws = websocket.WebSocketApp(
            self._sockjs_url(),
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        t = threading.Thread(target=self.ws.run_forever, daemon=True)
        t.start()
        deadline = time.time() + timeout
        while not self.connected and time.time() < deadline:
            time.sleep(0.05)
        return self.connected

    def call(self, method: str, params: list, timeout: float = 30.0):
        mid = self._next_id()
        ev = threading.Event()
        self._pending[mid] = ev
        self._send({"msg": "method", "method": method, "params": params, "id": mid})
        if ev.wait(timeout):
            self._pending.pop(mid, None)
            return self._results.pop(mid, None)
        self._pending.pop(mid, None)
        return None

    def login(self, username: str, password: str) -> bool:
        result = self.call("login", [{
            "username": username,
            "pass": password,
        }])
        if result and "result" in result:
            self.user_id = result["result"].get("id")
            return True
        return False

    def add_request_time(
        self,
        hours: float,
        price_per_hour: int,
        comment: str,
        engaged_user_id: str,
        start_ms: int,
        end_ms: int,
        activities_id: str,
        requests_id: str,
        cost_per_hour=None,
    ):
        total = round(hours * price_per_hour, 2)
        return self.call("requests.addRequestTime", [{
            "hours": round(hours, 4),
            "pricePerHour": price_per_hour,
            "costPerHour": cost_per_hour,
            "comment": comment,
            "engagedUserId": engaged_user_id,
            "startTime": {"$date": start_ms},
            "endTime": {"$date": end_ms},
            "total": total,
            "activities_id": {"$type": "oid", "$value": activities_id},
            "requests_id": {"$type": "oid", "$value": requests_id},
        }])

    def add_request_item(
        self,
        item: dict,
        amount: float,
        unit_price: float,
        date_ms: int,
        start_km: int,
        end_km: int,
        activities_id: str,
        requests_id: str,
        description: str | None = None,
        comment: str | None = None,
        added_by: dict | None = None,
        added_by_id: str | None = None,
    ):
        total = round(amount * unit_price, 2)
        payload = {
            "item": item,
            "amount": amount,
            "description": description,
            "unitPrice": unit_price,
            "unitCost": None,
            "percentage": None,
            "total": total,
            "date": {"$date": date_ms},
            "comment": comment,
            "startKm": start_km,
            "endKm": end_km,
            "activities_id": {"$type": "oid", "$value": activities_id},
            "requests_id": {"$type": "oid", "$value": requests_id},
        }
        if added_by:
            payload["added_by"] = added_by
            payload["added_by_id"] = added_by.get("_id")
        elif added_by_id:
            payload["added_by_id"] = added_by_id
        return self.call("requests.addRequestItem", [payload])

    def get_history(self, user_id: str, user_name: str, start_ms: int, end_ms: int):
        return self.call("user.mapForExportRequestTimesTvi", [{
            "userId": user_id,
            "userName": user_name,
            "startDate": {"$date": start_ms},
            "endDate": {"$date": end_ms},
        }])

    def remove_request_time(self, record_id: str):
        return self.call("requests.removeRequestTime", [
            {"$type": "oid", "$value": record_id}
        ])

    def car_km_report(self, item_id: str, start_ms: int, end_ms: int):
        """Povlači kompletnu km evidenciju automobila u periodu (sve aktivnosti, svi vozači)."""
        return self.call("items.mapForExportWithMaterialStep", [{
            "startDate": {"$date": start_ms},
            "endDate":   {"$date": end_ms},
            "itemId":    {"$type": "oid", "$value": item_id},
        }], timeout=20.0)

    def remove_request_item(self, record_id: str):
        """Briše stavku zahteva (kilometraža/materijal) po request_item ID-u."""
        return self.call("requests.removeRequestItem", [
            {"$type": "oid", "$value": record_id}
        ])

    def get_request_items(self, activities_id: str | None = None, timeout: float = 12.0) -> list[dict]:
        """Povlaci request_items dokumente (po aktivnosti ili globalno)."""
        with self._lock:
            self._sub_docs = []
            self._sub_collecting = True

        sub_id = self._next_id()
        ev = threading.Event()
        self._sub_pending[sub_id] = ev

        params = []
        if activities_id:
            params = [{"activities_id": {"$type": "oid", "$value": activities_id}}]

        self._send({"msg": "sub", "id": sub_id, "name": "request_items", "params": params})
        ev.wait(timeout)
        self._sub_pending.pop(sub_id, None)
        try:
            self._send({"msg": "unsub", "id": sub_id})
        except Exception:
            pass

        with self._lock:
            self._sub_collecting = False
            docs = list(self._sub_docs)
        return docs

    def search_activities_page(self, domain_code: str, name: str, page: int = 1, page_size: int = 20, timeout: float = 15.0) -> list[dict]:
        """Pretrazuje aktivne projekte - jedna stranica (za paginaciju).

        domain_code: string kod domena (npr. "9")
        name: naziv sa wildcardima (npr. "*" za sve)
        page: broj stranice, pocinje od 1
        page_size: broj rezultata po stranici
        """
        with self._lock:
            self._sub_docs = []
            self._sub_collecting = True

        sub_id = self._next_id()
        ev = threading.Event()
        self._sub_pending[sub_id] = ev

        skip = (page - 1) * page_size
        params = [
            {"domainCode": domain_code, "name": name},
            {
                "pageSize": page_size,
                "currentPage": page,
                "sortOptions": [{"value": 1, "key": "name", "translate": "ui.activity.label.name"}],
                "mongoOptionsForClient": {"sort": [["name", 1]], "skip": skip, "limit": page_size},
                "mongoOptionsForServer": {"sort": [["name", 1]], "skip": skip, "limit": page_size},
            },
            None,
            True,
        ]

        self._send({"msg": "sub", "id": sub_id, "name": "activities_search", "params": params})
        ev.wait(timeout)
        self._sub_pending.pop(sub_id, None)
        self._send({"msg": "unsub", "id": sub_id})

        with self._lock:
            self._sub_collecting = False
            docs = list(self._sub_docs)
        return docs

    def search_items(self, timeout: float = 15.0) -> list[dict]:
        """Povlači sve stavke (items) iz TVI-ja — automobili, materijali itd."""
        with self._lock:
            self._sub_docs = []
            self._sub_collecting = True

        sub_id = self._next_id()
        ev = threading.Event()
        self._sub_pending[sub_id] = ev

        params = [
            {"name": None},
            {
                "pageSize": 999,
                "currentPage": 1,
                "sortOptions": [{"key": "name", "value": 1}],
                "or": True,
                "mongoOptionsForClient": {"sort": {"name": 1}, "skip": 0, "limit": 999},
                "mongoOptionsForServer": {"sort": {"name": 1}, "skip": 0, "limit": 1998},
            },
        ]

        self._send({"msg": "sub", "id": sub_id, "name": "items_search", "params": params})
        ev.wait(timeout)
        self._sub_pending.pop(sub_id, None)
        self._send({"msg": "unsub", "id": sub_id})

        with self._lock:
            self._sub_collecting = False
            docs = list(self._sub_docs)
        return docs

    def search_activities(self, domain_code: str, name: str, timeout: float = 15.0) -> list[dict]:
        """Pretrazuje aktivne projekte po domenu i nazivu.

        domain_code: string kod domena (npr. "9" za OPSTE I NERADNO)
        name: naziv sa wildcardima (npr. "*dalibor")
        Vraca listu dokumenata sa poljima: _id, name, activityNumber, requests_id, ...
        """
        with self._lock:
            self._sub_docs = []
            self._sub_collecting = True

        sub_id = self._next_id()
        ev = threading.Event()
        self._sub_pending[sub_id] = ev

        params = [
            {"domainCode": domain_code, "name": name},
            {
                "pageSize": 20,
                "currentPage": 1,
                "sortOptions": [{"value": 1, "key": "name", "translate": "ui.activity.label.name"}],
                "mongoOptionsForClient": {"sort": [["name", 1]], "skip": 0, "limit": 20},
                "mongoOptionsForServer": {"sort": [["name", 1]], "skip": 0, "limit": 20},
            },
            None,
            True,
        ]

        self._send({"msg": "sub", "id": sub_id, "name": "activities_search", "params": params})
        ev.wait(timeout)
        self._sub_pending.pop(sub_id, None)
        self._send({"msg": "unsub", "id": sub_id})

        with self._lock:
            self._sub_collecting = False
            docs = list(self._sub_docs)
        return docs

    def get_request_time_ids_for_day(self, user_id: str, start_ms: int, end_ms: int, timeout: float = 10.0) -> list[dict]:
        """Vraca listu {id, start_ms, end_ms, comment} za zadati dan i korisnika.

        Koristi request_times subscription. Ceka dok podaci ne prestanu da stizu
        (0.6s stabilnost), a najduze 'timeout' sekundi.
        """
        with self._lock:
            self._rt_docs = []
            self._rt_collecting = True
            self._rt_last_added = 0.0

        sub_id = self._next_id()
        self._send({"msg": "sub", "id": sub_id, "name": "request_times", "params": [user_id]})

        # Poll svake 100ms: stani kad nema novih dokumenata 0.6s (i proslo min 0.5s)
        STABLE_SEC = 0.6
        MIN_WAIT   = 0.5
        deadline   = time.time() + timeout
        time.sleep(MIN_WAIT)
        while time.time() < deadline:
            time.sleep(0.1)
            with self._lock:
                last = self._rt_last_added
                count = len(self._rt_docs)
            if count > 0 and (time.time() - last) >= STABLE_SEC:
                break

        self._send({"msg": "unsub", "id": sub_id})

        with self._lock:
            self._rt_collecting = False
            docs = list(self._rt_docs)

        result = []
        for doc in docs:
            if doc.get("engagedUserId") != user_id:
                continue
            st = doc.get("startTime", {})
            st_ms = st.get("$date", 0) if isinstance(st, dict) else 0
            if start_ms <= st_ms <= end_ms:
                et = doc.get("endTime", {})
                et_ms = et.get("$date", 0) if isinstance(et, dict) else 0
                result.append({
                    "id": doc["_id"],
                    "start_ms": st_ms,
                    "end_ms": et_ms,
                    "comment": doc.get("comment") or "",
                })
        return result

    def close(self) -> None:
        if self.ws:
            self.ws.close()
