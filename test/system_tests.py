from iota import *
from logging import basicConfig, DEBUG, getLogger
from sys import stderr
import time
from bot_api import api, Database
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
            bot_api_send = api(b'SWMS9HOIE9EKPKWTBKJHTJOX9EU9NNJB9AEDWZPFOBSBQBXBFPYSRCE9SVIHRI9BJAGLSCAMMRUFSQRIJ')
            bot_api_receive = api(b'DHHJILKLLZBOCQNDMDWETDNMKEBJPAAYM9QNKAVWCEE99DSZXMNHUSWWIPJGUHUGZXEMEJLADOYJPRYSY')
            bot_db_send = Database('system_test_db1.db')
            bot_db_receive = Database('system_test_db2.db')
            for i in range(1,100):
                starting_balance = bot_api_receive.get_account_balance(bot_db_receive.get_address_index())
                print('Starting Balance: {0}'.format(starting_balance))
                #Get the receiving address
                while True:
                    address_index = bot_db_receive.get_address_index()
                    address = bot_api_receive.get_new_address(address_index)
                    bot_db_receive.add_used_address(address_index,address._trytes.decode("utf-8"))
                    if bot_api_receive.get_balance(address) == 0:
                        break
                #Get the new sending address
                address_index = bot_db_send.get_address_index()
                new_address = bot_api_send.get_new_address(address_index)
                bot_db_send.add_used_address(address_index,address._trytes.decode("utf-8"))
                transaction = bot_api_send.send_transfer(address,i,new_address,address_index)
                print('{0} sent to address.'.format(i))
                confirmed = False
                start_time = time.time()
                while not confirmed:
                    confirmed = bot_api_send.check_transaction(transaction)
                    print(confirmed)
                    if (time.time() - start_time) > (60) and not confirmed:
                        print('Replaying Bundle')
                        #confirmed = True
                        bot_api_send.replay_bundle(transaction)
                print('Transaction Confirmed')
                self.assertEqual(bot_api_receive.get_account_balance(),starting_balance+i)

unittest.main()
