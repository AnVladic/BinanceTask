# python-binance==1.0.16

import asyncio
import datetime
from binance import AsyncClient, BinanceSocketManager


class Symbol():
    class Ticket:
        def __init__(self, time, price):
            self.time = time
            self.price = price

    @classmethod
    async def create(cls, client: AsyncClient, socket_manager: BinanceSocketManager, symbol: str):
        self = Symbol()
        self.symbol = symbol
        self.socket_manager = socket_manager

        klines = await client.futures_klines(symbol=symbol, interval=AsyncClient.KLINE_INTERVAL_1MINUTE, limit=60)
        self.tickets = list(map(lambda x: Symbol.Ticket(time=x[0], price=float(x[3])), klines))
        self.max_ticket = self.get_max_ticket(self.tickets)

        self.print_max_price()

        return self

    def print_max_price(self):
        dt = datetime.datetime.fromtimestamp(self.max_ticket.time / 1e3)
        print(f'[{dt}] {self.symbol} max_price = {self.max_ticket.price}')

    def get_max_ticket(self, tickets: Ticket) -> Ticket:
        return max(tickets, key=lambda x: x.price)

    async def observe(self, fall_limit=0.99):
        """
        Watching the price of a pair
        """
        ts = self.socket_manager.symbol_mark_price_socket(self.symbol, fast=True)
        async with ts as tscm:
            while True:
                res = await tscm.recv()
                current_ticket = Symbol.Ticket(time=res['data']['E'], price=float(res['data']['p']))
                self.tickets.append(current_ticket)

                # Clear the list from data that has gone beyond one hour
                # 60 * 60 * 1000 = 3600000 (1 hour)
                while self.tickets[0].time + 3600000 < current_ticket.time:
                    removed_price = self.tickets.pop(0)

                    # update max price
                    if removed_price.time == self.max_ticket.time and removed_price.price == self.max_ticket.price:
                        self.max_ticket = self.get_max_ticket(self.tickets)
                        self.print_max_price()

                if self.max_ticket.price < current_ticket.price:
                    self.max_ticket = current_ticket
                    self.print_max_price()

                if self.max_ticket.price / current_ticket.price <= fall_limit:
                    print(f'{self.symbol} price fell below {fall_limit * 100}%. '
                    'current_price = {self.current_price.price}, max_price = {self.max_ticket.price}')
        # await client.close_connection()
                

async def main():
    client = await AsyncClient.create()
    bm = BinanceSocketManager(client)

    symbol = await Symbol.create(client, bm, 'XRPUSDT')
    await symbol.observe()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()