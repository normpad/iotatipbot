from iota import *
from logging import basicConfig, DEBUG, getLogger
from sys import stderr
import time
from bot_api import api, Database
import sqlite3
import unittest
import config
import os

#basicConfig(level=DEBUG, stream=stderr, format='%(levelname)s: %(asctime)s: %(message)s')
#logger = getLogger(__name__)
#logger.setLevel(DEBUG)

test_seed = b'A'*81

class SystemTests(unittest.TestCase):

       
        def test_systems(self):
            """
            Test Transactions
            Send 100 transfers and verify that each one is properly received
            """
            bot_api = api(test_seed)
            seed = bot_api.create_seed()
            bot_api_send = api(bytearray(seed,'utf-8'))
            if os.path.isfile('test_db_send.db'):
                os.remove('test_db_send.db')
            db_send = Database('test_db_send.db')
            send_address_index = db_send.get_address_index()
            fund_address = bot_api_send.get_new_address(send_address_index)
            db_send.add_used_address(send_address_index,fund_address._trytes.decode('utf-8'))
            print("Please send 100 iota to address {0}".format(fund_address._trytes.decode('utf-8')))

            #Wait until the account has been funded
            while True:
                if bot_api_send.get_balance(fund_address) > 0:
                    break
                time.sleep(1)

            #Initialize receiving account
            bot_api_receive = api(bytearray(bot_api.create_seed(),'utf-8'))
            if os.path.isfile('test_db_receive.db'):
                os.remove('test_db_receive.db')
            db_receive = Database('test_db_receive.db')

            confirmation_times = []
            for i in range(0,100):
                receive_address_index = db_receive.get_address_index()                
                receiving_address = bot_api_receive.get_new_address(receive_address_index)
                db_receive.add_used_address(receive_address_index,receiving_address._trytes.decode("utf-8"))
                starting_balance = bot_api_receive.get_balance(receiving_address)

                #Get the new sending address
                send_address_index = db_send.get_address_index()
                new_address = bot_api_send.get_new_address(send_address_index)
                db_send.add_used_address(send_address_index,new_address._trytes.decode("utf-8"))

                transaction_time = time.time()
                bundle = bot_api_send.send_transfer(receiving_address,1,new_address,send_address_index)
                print(bundle.hash)
                print(bundle.tail_transaction.hash)
                validator = BundleValidator(bundle)
                valid_bundle = validator.is_valid()
                self.assertTrue(valid_bundle)
                confirmation_time = time.time()
                print('Transaction Confirmed in {0} minutes'.format((confirmation_time - transaction_time)/60))
                self.assertEqual(bot_api_receive.get_balance(receiving_address),starting_balance+1)

            receive_address_index = db_receive.get_address_index()
            self.assertEqual(bot_api_receive.get_account_balance(receive_address_index),100)
            average_confirmation_time = 0
            for t in confirmation_times:
                average_confirmation_time = average_confirmation_time + t
            average_confirmation_time = average_confirmation_time / len(confirmation_times)
            print('Average confirmation time: {0}'.format(average_confirmation_time))

unittest.main()
