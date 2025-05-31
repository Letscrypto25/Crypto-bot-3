def get_balance(user_id: str, source: str, user=None) -> dict:
    print(f"Fetching balance for user: {user_id} on {source}")
    try:
        if source == "luno":
            key = user["api_key"]
            secret = user["secret"]
            auth = base64.b64encode(f"{key}:{secret}".encode()).decode()
            headers = {"Authorization": f"Basic {auth}"}
            r = requests.get("https://api.luno.com/api/1/balance", headers=headers)
            print("Luno response:", r.text)
            r.raise_for_status()
            data = r.json().get("balance", [])
            return {
                asset["asset"]: float(asset["balance"])
                for asset in data
                if float(asset["balance"]) > 0
            }

        elif source == "binance":
            client = get_binance_client(user_id)
            raw_balances = client.get_account()["balances"]
            print("Binance balances:", raw_balances)
            return {
                b["asset"]: float(b["free"])
                for b in raw_balances
                if float(b["free"]) > 0
            }

        else:
            raise ValueError(f"Unknown exchange source: {source}")

    except Exception as e:
        print(f"[Balance Fetch Error] {e}")
        return {}
