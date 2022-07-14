import unittest
import socket
import json
import sys

host = str(sys.argv[1])
port = 8081


class TestRestAPI(unittest.TestCase):

    def test_query_valid_item(self):
        print('Query catalog for valid item: Tux')
        s = socket.socket()
        s.connect((host, port))
        s.send(bytes('GET /products/Tux HTTP/1.1', 'utf-8'))
        res = s.recv(1024).decode("utf-8")
        arr = res.split('\n')
        arr[-1] = arr[-1].replace('\'', '"')
        res_json = json.loads(arr[-1])
        self.assertTrue('data' in res_json)
        self.assertTrue(res_json['data']['name'] == 'Tux')
        self.assertFalse('error' in res_json)
        s.close()

    # catalog query for invalid item
    def test_query_invalid_item(self):
        print('Query catalog for invalid item')
        s = socket.socket()
        s.connect((host, port))
        s.send(bytes('GET /products/Random HTTP/1.1', 'utf-8'))
        res = s.recv(1024).decode("utf-8")
        arr = res.split('\n')
        arr[-1] = arr[-1].replace('\'', '"')
        res_json = json.loads(arr[-1])
        self.assertTrue('error' in res_json)
        self.assertFalse('data' in res_json)
        s.close()

    # order request for invalid item
    def test_buy_invalid_item(self):
        print('Order invalid item')
        s = socket.socket()
        s.connect((host, port))
        req_body = {
            "name": "Random",
            "quantity": 1
        }
        s.send(bytes('POST /orders HTTP/1.1\n' + json.dumps(req_body), 'utf-8'))
        res = s.recv(1024).decode("utf-8")
        arr = res.split('\n')
        arr[-1] = arr[-1].replace('\'', '"')
        res_json = json.loads(arr[-1])
        self.assertTrue('error' in res_json)
        self.assertFalse('data' in res_json)
        s.close()

    # order request for valid item and proper quantity
    def test_buy_valid_item_within_quantity(self):
        print('Order valid item(Tux) with less than or equal to quantity')
        s = socket.socket()
        s.connect((host, port))
        req_body = {
            "name": "Tux",
            "quantity": 1
        }
        s.send(bytes('POST /orders HTTP/1.1\n' + json.dumps(req_body), 'utf-8'))
        res = s.recv(1024).decode("utf-8")
        arr = res.split('\n')
        arr[-1] = arr[-1].replace('\'', '"')
        res_json = json.loads(arr[-1])
        self.assertTrue('data' in res_json)
        self.assertTrue('order_number' in res_json['data'])
        self.assertFalse('error' in res_json)
        s.close()

    # order request for valid item and quantity = 10000000
    def test_buy_valid_item_exceed_quantity(self):
        print('Order valid item(Tux) with greater quantity')
        s = socket.socket()
        s.connect((host, port))
        req_body = {
            "name": "Tux",
            "quantity": 100000
        }
        s.send(bytes('POST /orders HTTP/1.1\n' + json.dumps(req_body), 'utf-8'))
        res = s.recv(1024).decode("utf-8")
        arr = res.split('\n')
        arr[-1] = arr[-1].replace('\'', '"')
        res_json = json.loads(arr[-1])
        self.assertTrue('error' in res_json)
        self.assertFalse('data' in res_json)
        s.close()

    # order request for valid item and quantity = -1
    def test_buy_valid_item_negative_quantity(self):
        print('Order valid item(Tux) with lower than zero')
        s = socket.socket()
        s.connect((host, port))
        req_body = {
            "name": "Tux",
            "quantity": -1
        }
        s.send(bytes('POST /orders HTTP/1.1\n' + json.dumps(req_body), 'utf-8'))
        res = s.recv(1024).decode("utf-8")
        arr = res.split('\n')
        arr[-1] = arr[-1].replace('\'', '"')
        res_json = json.loads(arr[-1])
        self.assertTrue('error' in res_json)
        self.assertFalse('data' in res_json)
        s.close()

    def test_order_details_with_valid_order_id(self):
        print('Get Order details for valid order_id')
        s = socket.socket()
        s.connect((host, port))
        s.send(bytes('GET /orders/1 HTTP/1.1', 'utf-8'))
        res = s.recv(1024).decode("utf-8")
        arr = res.split('\n')
        arr[-1] = arr[-1].replace('\'', '"')
        res_json = json.loads(arr[-1])
        self.assertTrue('data' in res_json)
        self.assertTrue(res_json['data']['number'] == 1)
        self.assertFalse('error' in res_json)
        s.close()

    # test with order details with invalid order id
    def test_order_details_with_invalid_order_id(self):
        print('Get Order details for invalid order_id')
        s = socket.socket()
        s.connect((host, port))
        s.send(bytes('GET /orders/-1 HTTP/1.1', 'utf-8'))
        res = s.recv(1024).decode("utf-8")
        arr = res.split('\n')
        arr[-1] = arr[-1].replace('\'', '"')
        res_json = json.loads(arr[-1])
        self.assertTrue('error' in res_json)
        self.assertFalse('data' in res_json)
        s.close()


if __name__ == '__main__':
    unittest.main()
