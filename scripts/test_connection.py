"""Quick test: connect to status-backend, create account, start messenger."""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
import websockets

BASE_URL = "http://127.0.0.1:12345"
WS_URL = "ws://127.0.0.1:12345/signals"
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workspace", "data"))


async def main():
    http = httpx.AsyncClient(base_url=BASE_URL, timeout=300.0)

    # 1. Health check
    print("1. Health check...")
    r = await http.get("/health")
    print(f"   {r.json()}")

    # 2. Connect WebSocket FIRST (as per README)
    print("\n2. Connecting WebSocket for signals...")
    ws = await websockets.connect(WS_URL, ping_interval=None)
    print("   Connected")

    # 3. Initialize
    print(f"\n3. Initialize (data: {DATA_DIR})...")
    r = await http.post("/statusgo/InitializeApplication", json={"dataDir": DATA_DIR})
    data = r.json()
    accounts = data.get("accounts") or []
    print(f"   Accounts: {len(accounts)}")

    # 4. Create or login
    if accounts:
        key_uid = accounts[0]["key-uid"]
        print(f"\n4. Logging in as '{accounts[0]['name']}' ...")
        r = await http.post("/statusgo/LoginAccount", json={
            "keyUID": key_uid,
            "password": "status-agent-bot",
        })
    else:
        print("\n4. Creating account 'Status App Agent'...")
        r = await http.post("/statusgo/CreateAccountAndLogin", json={
            "rootDataDir": DATA_DIR,
            "displayName": "Status App Agent",
            "password": "status-agent-bot",
            "customizationColor": "primary",
        })

    error = r.json().get("error", "")
    if error:
        print(f"   ERROR: {error}")
        return
    print("   OK (async, waiting for node.login signal...)")

    # 5. Wait for node.login signal
    print("\n5. Waiting for signals...")
    logged_in = False
    for _ in range(60):  # max 60 signals or timeout
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
            signal = json.loads(msg)
            sig_type = signal.get("type", "")
            print(f"   Signal: {sig_type}")
            if sig_type == "node.login":
                error = signal.get("event", {}).get("error", "")
                if error:
                    print(f"   LOGIN ERROR: {error}")
                    return
                logged_in = True
                print("   LOGIN SUCCESS!")
                break
        except asyncio.TimeoutError:
            print("   (waiting...)")

    if not logged_in:
        print("   Failed to login")
        return

    # 6. Start messenger in background (blocks for a long time on first run)
    print("\n6. Starting messenger in background (Waku bootstrap can take minutes)...")

    rpc_id = 0

    async def call_rpc(method, params=None):
        nonlocal rpc_id
        rpc_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "method": method,
            "params": params or [],
        }
        r = await http.post("/statusgo/CallRPC", json=payload)
        raw = r.text
        print(f"   [{method}] raw response ({len(raw)} bytes): {raw[:500]}")
        return r.json()

    async def start_messenger():
        try:
            return await call_rpc("wakuext_startMessenger")
        except Exception as e:
            return {"error": str(e)}

    messenger_task = asyncio.create_task(start_messenger())

    # Meanwhile, drain WebSocket signals to see what's happening
    print("   Draining signals while messenger starts...")
    for _ in range(120):  # up to ~10 min
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            signal = json.loads(msg)
            sig_type = signal.get("type", "")
            if sig_type not in ("stats",):  # skip noisy signals
                print(f"   Signal: {sig_type}")
        except asyncio.TimeoutError:
            pass
        if messenger_task.done():
            break

    if messenger_task.done():
        result = messenger_task.result()
        if "result" in result:
            keys = list(result["result"].keys())[:10]
            print(f"   Messenger started! Keys: {keys}")
        else:
            print(f"   Messenger result: {str(result)[:300]}")
    else:
        print("   Messenger still starting, but Waku peers are connecting. Waiting for it to finish...")
        try:
            result = await asyncio.wait_for(messenger_task, timeout=300.0)
            if "result" in result:
                keys = list(result["result"].keys())[:10]
                print(f"   Messenger started! Keys: {keys}")
            else:
                print(f"   Messenger result: {str(result)[:300]}")
        except asyncio.TimeoutError:
            print("   Messenger still not done after 5min. Proceeding anyway.")

    # 7. Wait a bit for backend to stabilize, then test RPC
    print("\n7. Waiting 5s for backend to stabilize after messenger start...")
    await asyncio.sleep(5)

    print("\n8. Getting settings...")
    try:
        result = await call_rpc("settings_getSettings")
        if "result" in result and result["result"]:
            s = result["result"]
            print(f"   Display name: {s.get('display-name', 'N/A')}")
            pub_key = s.get("public-key", "N/A")
            print(f"   Public key: {pub_key[:40]}...")
            key_uid = s.get("key-uid", "N/A")
            print(f"   Key UID: {key_uid}")
            print(f"\n   Save to .env: STATUS_BOT_KEY_UID={key_uid}")
        else:
            print(f"   No result or empty: {str(result)[:300]}")
    except Exception as e:
        print(f"   Error ({type(e).__name__}): {e}")

    # 9. Check communities
    print("\n9. Checking communities...")
    try:
        result = await call_rpc("wakuext_communities")
        if "result" in result and result["result"]:
            communities = result["result"].get("communities", [])
            print(f"   Communities: {len(communities)}")
            for c in communities[:5]:
                print(f"   - {c.get('name', '?')} ({c.get('id', '?')[:20]}...)")
        else:
            print(f"   No result or empty: {str(result)[:300]}")
    except Exception as e:
        print(f"   Error ({type(e).__name__}): {e}")

    # 10. Try joined communities specifically
    print("\n10. Checking joined communities...")
    try:
        result = await call_rpc("wakuext_joinedCommunities")
        print(f"   Result keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
    except Exception as e:
        print(f"   Error ({type(e).__name__}): {e}")

    print("\n--- Done! Bot is connected to Status network. ---")
    try:
        await ws.close()
    except Exception:
        pass
    await http.aclose()


if __name__ == "__main__":
    asyncio.run(main())
