from iota import *
from logging import basicConfig, DEBUG, getLogger
from sys import stderr
import time
from bot_api import api
import sqlite3
import unittest
import config

#basicConfig(level=DEBUG, stream=stderr, format='%(levelname)s: %(asctime)s: %(message)s')
#logger = getLogger(__name__)
#logger.setLevel(DEBUG)

test_seed = b'A'*81

class SystemTests(unittest.TestCase):

        """
        Test Addresses
        Generate 100 address and verify each one is unique and empty
        """
        def test_addresses(self):
            bot_api = api(b'BPXAMKXH9RTEDLE9EGAJE9XGUEOGHRFFODKPLKNKGSISLERJJNSESNMUDUDMAGFIRELWNZAVHGLOIGVNF')
            bot_api.init_custom_db('test_db.db')
            addresses = []
            for i in range(0,100):
                address = bot_api.get_new_address()
                addresses.append(address)
            for i in range(0,100):
                self.assertEqual(addresses.count(addresses[i]),1)
                self.assertEqual(bot_api.get_balance(addresses[i]),0)

        """
        Test Transactions
        Send 100 transfers and verify that each one is properly received
        """
        def test_transactions(self):
            bot_api_send = api(b'SWMS9HOIE9EKPKWTBKJHTJOX9EU9NNJB9AEDWZPFOBSBQBXBFPYSRCE9SVIHRI9BJAGLSCAMMRUFSQRIJ',False)
            bot_api_send.init_custom_db('test_db.db')
            bot_api_receive = api(b'BPXAMKXH9RTEDLE9EGAJE9XGUEOGHRFFODKPLKNKGSISLERJJNSESNMUDUDMAGFIRELWNZAVHGLOIGVNF')
            bot_api_receive.init_custom_db('test_db.db')
            for i in range(1,100):
                starting_balance = bot_api_receive.get_account_balance()
                print('Starting Balance: {0}'.format(starting_balance))
                address = bot_api_receive.get_new_address()
                self.assertEqual(bot_api_receive.get_balance(address),0)
                transaction = bot_api_send.send_transfer(address,i)
                print('{0} sent to address.'.format(i))
                confirmed = False
                start_time = time.time()
                while not confirmed:
                    confirmed = bot_api_send.check_transaction(transaction)
                    if (time.time() - start_time) > (60*5) and not confirmed:
                        print('Replaying Bundle')
                        confirmed = True
                        #bot_api_send.replay_bundle(transaction)
                print('Transaction Confirmed')
                self.assertEqual(bot_api_receive.get_account_balance(),starting_balance+i)

unittest.main()
