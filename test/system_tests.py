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
        Test Transactions
        Send 100 transfers and verify that each one is properly received
        """
        def test_systems(self):
            bot_api_send = api(b'SWMS9HOIE9EKPKWTBKJHTJOX9EU9NNJB9AEDWZPFOBSBQBXBFPYSRCE9SVIHRI9BJAGLSCAMMRUFSQRIJ',False)
            bot_api_receive = api(b'BPXAMKXH9RTEDLE9EGAJE9XGUEOGHRFFODKPLKNKGSISLERJJNSESNMUDUDMAGFIRELWNZAVHGLOIGVNF')
            bot_db = Database('test_db.db')
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
