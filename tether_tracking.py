import asyncio
import json
from web3 import Web3
from websockets import connect

# 알람 설정
frequency = 2500  # Hz
duration = 1000  # ms

# 노드에 연결
infura_ws_url = 'wss://mainnet.infura.io/ws/v3/[YOUR_API_KEY]'
infura_http_url = 'https://mainnet.infura.io/v3/[YOUR_API_KEY]'
web3 = Web3(Web3.HTTPProvider(infura_http_url))

# 모니터링할 스마트 계약 정보 (Tether USDT)
tether_account = web3.to_checksum_address('0xdAC17F958D2ee523a2206206994597C13D831ec7')
with open("./tether_abi.json") as f:
    tether_abi = json.load(f)
tetherContract = web3.eth.contract(address=tether_account, abi=tether_abi)

async def get_event():
    async with connect(infura_ws_url) as ws:
        # 새로운 대기 중인 트랜잭션에 대한 구독 요청
        await ws.send(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_subscribe",
            "params": ["newPendingTransactions"]
        }))
        subscription_response = await ws.recv()
        print("Subscription response:", subscription_response)

        while True:
            try:
                # 메시지 수신
                message = await asyncio.wait_for(ws.recv(), timeout=15)
                response = json.loads(message)
                txHash = response['params']['result']
                tx = web3.eth.get_transaction(txHash)

                # 트랜잭션이 Tether 스마트 계약을 대상으로 하는지 확인
                if tx.to == tether_account:
                    decoded_function = tetherContract.decode_function_input(tx["input"])
                    function_name = decoded_function[0]
                    function_args = decoded_function[1]
                    value_usdt = function_args['_value'] * 10**-6 if '_value' in function_args else None

                    print({
                        "hash": txHash,
                        "from": tx["from"],
                        "value_eth": Web3.from_wei(tx["value"], "ether"),  # 수정된 부분
                        "function": function_name,
                        "value_usdt": value_usdt
                    })

            except asyncio.TimeoutError:
                pass  # 타임아웃이 발생하면 계속 루프 실행
            except Exception as e:
                print(f"An error occurred: {e}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(get_event())