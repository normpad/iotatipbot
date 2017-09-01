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

class IotaUnitTests(unittest.TestCase):

        #test get_account_balance()
        #preconditions: 
        #   account has 9 iota in it
        #postconditions: 
        #   9 is returned
        def test_get_account_balance(self):
            seed = b'YJQCSOSYOLZAECLVZLGXONHDBL99SFOVFTUROVKQU9OHMUSJDBOOREHTCLZZSVCYLRLXRUDCAOQITYUGN'
            bot_api = api(seed,False)
            bot_api.init_custom_db('testDB.db')
            start_time = time.time()
            account_balance = bot_api.get_account_balance()
            end_time = time.time()
            self.assertEqual(account_balance,9)

        #test get_balance(address)
        #preconditions:
        #   address has 9 iota in it
        #postconditions: 
        #   9 is returned
        def test_get_balance(self):
            seed = b'YJQCSOSYOLZAECLVZLGXONHDBL99SFOVFTUROVKQU9OHMUSJDBOOREHTCLZZSVCYLRLXRUDCAOQITYUGN'
            address = b'FE9GTLROSVSYGOMUKUS9GVOCRGNSRAWNTBUXBY9CLFFULBKKMWDWIPJ9EOIMSGIOUEPZ9HBUOAHOTYL9AMYUCRFZUD'
            bot_api = api(seed,False)
            start_time = time.time()
            addressBalance = bot_api.get_balance(address)
            end_time = time.time()
            self.assertEqual(addressBalance,9)

        #test get_new_address()
        #preconditions:
        #   None
        #postconditions:
        #   An address is returned 
        def test_get_new_address(self):  
            seed = b'BPXAMKXH9RTEDLE9EGAJE9XGUEOGHRFFODKPLKNKGSISLERJJNSESNMUDUDMAGFIRELWNZAVHGLOIGVNF'
            bot_api = api(seed,False)
            bot_api.init_custom_db('testDB.db')
            conn = sqlite3.connect('testDB.db')
            db = conn.cursor()
            start_time = time.time()
            address = bot_api.get_new_address()
            validChecksum = address.is_checksum_valid()
            end_time = time.time()
            print("Address generated: {0}".format(address))
            self.assertTrue(validChecksum)

        #test send_transfer(addr, amount)    
        #preconditions:
        #   None
        #postconditions:
        #   Exception is not thrown
        def test_send_transfer(self):
            seed = b'SWMS9HOIE9EKPKWTBKJHTJOX9EU9NNJB9AEDWZPFOBSBQBXBFPYSRCE9SVIHRI9BJAGLSCAMMRUFSQRIJ'
            address = b'ROJLHG9AIQYLSNXZMUABJCVOMCZFILEAVNWKKK9CG9JWISIWX9VCDHCXOIYRFYVUAOAMYGFZWDQWLWHJWTXKJMSPZC'
            bot_api = api(seed,False)
            start_time = time.time()
            try:
                bot_api.send_transfer(address,1)
            except:
                self.fail()
            end_time = time.time()
            print("Time elapsed: {0}s".format(end_time-start_time))

unittest.main()
