import random
import time
import socket
import json

catalog_items = ["Tux", "Whale", "Penguin", "Bear", "Barbie", "Crayola Crayon", "Erector Set",
                 "Etch A Sketch", "Frisbee", "Hula hoop", "Invalid Item"]

debugger_logs = True


# returns the random item.
def pick_random_item():
    return catalog_items[random.randint(0, len(catalog_items) - 1)]


# used to simulate a client
class ToyStoreClient:
    def __init__(self, name, req_count, buy_prob, max_buy):
        self.name = name
        self.req_count = req_count
        self.buy_prob = buy_prob
        self.max_buy = max_buy
        self.socket = socket.socket()
        self.query_response_times = []
        self.order_response_times = []
        self.existing_order_response_times = []
        self.orders = []

    def serve(self, host='localhost'):
        try:
            # self.socket.connect(('localhost', 8081))
            self.socket.connect((host, 8081))
            counter = 0
            while counter < self.req_count:
                item_name = pick_random_item()  # random item name
                # catalog_query
                query_res = self.query(item_name)
                # time.sleep(1)
                counter += 1
                # item does not exist
                if 'error' in query_res:
                    if debugger_logs:
                        print(self.name, "query error:", query_res['error'])
                # item exists
                else:
                    item_details = query_res['data']
                    if debugger_logs:
                        print(self.name, "query data:", item_details)
                    # quantity is available and meet the prob condition
                    if item_details['quantity'] > 0 and random.random() < self.buy_prob:
                        buy_res = self.buy(item_details['name'])
                        if buy_res is None:
                            continue
                        # time.sleep(1)
                        counter += 1
                        if 'error' in buy_res:
                            if debugger_logs:
                                print(self.name, "buy error:", buy_res['error'])
                        # order placed
                        else:
                            data = buy_res['data']
                            if debugger_logs:
                                print(self.name, "buy data:", data)
                            self.orders.append(data["order_number"])

        except Exception as e:
            print(e)
        finally:
            # print all the order details before closing the connection
            for order_no in self.orders:
                order_query_res = self.get_order_details(order_no)
                if order_query_res is None:
                    continue
                # time.sleep(1)
                if 'error' in order_query_res:
                    if debugger_logs:
                        print(self.name, "order query error:", order_query_res['error'])
                # order found
                else:
                    data = order_query_res['data']
                    if debugger_logs:
                        print(self.name, "order query data:", data)
            self.socket.close()

    # to fetch the item_details
    def query(self, item_name):
        start_time = time.time()
        self.socket.send(bytes('GET /products/{} HTTP/1.1'.format(item_name), 'utf-8'))  # send catalog request
        res = self.socket.recv(1024).decode("utf-8")
        end_time = time.time()
        self.query_response_times.append(end_time - start_time)
        arr = res.split('\n')
        arr[-1] = arr[-1].replace('\'', '"')
        return json.loads(arr[-1])

    # to place an order
    def buy(self, item_name):
        req_body = {
            "name": item_name,
            "quantity": random.randint(1, self.max_buy)
        }
        start_time = time.time()
        self.socket.send(bytes('POST /orders HTTP/1.1\n' + json.dumps(req_body), 'utf-8'))  # send order request
        res = self.socket.recv(1024).decode("utf-8")
        end_time = time.time()
        self.order_response_times.append(end_time - start_time)
        arr = res.split('\n')
        arr[-1] = arr[-1].replace('\'', '"')
        return json.loads(arr[-1])

    # to get order details
    def get_order_details(self, order_no):
        start_time = time.time()
        self.socket.send(bytes('GET /orders/{} HTTP/1.1'.format(order_no), 'utf-8'))  # send catalog request
        res = self.socket.recv(1024).decode("utf-8")
        end_time = time.time()
        self.existing_order_response_times.append(end_time - start_time)
        arr = res.split('\n')
        arr[-1] = arr[-1].replace('\'', '"')
        return json.loads(arr[-1])
