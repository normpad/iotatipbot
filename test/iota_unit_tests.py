from iota import *
from logging import basicConfig, DEBUG, getLogger
from sys import stderr
import time
from bot_api import api,Database
import sqlite3
import unittest
import config

#basicConfig(level=DEBUG, stream=stderr, format='%(levelname)s: %(asctime)s: %(message)s')
#logger = getLogger(__name__)
#logger.setLevel(DEBUG)

test_seed = b'A'*81

class IotaUnitTests(unittest.TestCase):

        
        def test_get_account_balance(self):
            """
            test get_account_balance()
            preconditions: 
               account has 9 iota in it
            postconditions: 
               9 is returned
            """
            seed = b'YJQCSOSYOLZAECLVZLGXONHDBL99SFOVFTUROVKQU9OHMUSJDBOOREHTCLZZSVCYLRLXRUDCAOQITYUGN'
            bot_api = api(seed)
            account_balance = bot_api.get_account_balance(100)
            self.assertEqual(account_balance,9)

        
        def test_get_balance(self):
            """
            test get_balance(address)
            preconditions:
               address has 9 iota in it
            postconditions: 
               9 is returned
            """
            seed = b'YJQCSOSYOLZAECLVZLGXONHDBL99SFOVFTUROVKQU9OHMUSJDBOOREHTCLZZSVCYLRLXRUDCAOQITYUGN'
            address = b'FE9GTLROSVSYGOMUKUS9GVOCRGNSRAWNTBUXBY9CLFFULBKKMWDWIPJ9EOIMSGIOUEPZ9HBUOAHOTYL9AMYUCRFZUD'
            bot_api = api(seed)
            start_time = time.time()
            addressBalance = bot_api.get_balance(address)
            end_time = time.time()
            self.assertEqual(addressBalance,9)
        
        def test_get_new_address(self):  
            """
            Test get_new_address
            preconditions:
               None
            postconditions:
               An address is returned 
            """
            seed = b'BPXAMKXH9RTEDLE9EGAJE9XGUEOGHRFFODKPLKNKGSISLERJJNSESNMUDUDMAGFIRELWNZAVHGLOIGVNF'
            bot_api = api(seed)
            address = bot_api.get_new_address(0)
            validChecksum = address.is_checksum_valid()
            print("Address generated: {0}".format(address))
            self.assertTrue(validChecksum)

        def test_send_transfer(self):
            """
            Test send_transfer
            Preconditions:
                Seed has at least 1 iota
            Postconditions:
                No error is thrown
                Created bundle is valid
                Address balance has increased by 1 iota
            """
            seed = b'SWMS9HOIE9EKPKWTBKJHTJOX9EU9NNJB9AEDWZPFOBSBQBXBFPYSRCE9SVIHRI9BJAGLSCAMMRUFSQRIJ'
            address = b'ROJLHG9AIQYLSNXZMUABJCVOMCZFILEAVNWKKK9CG9JWISIWX9VCDHCXOIYRFYVUAOAMYGFZWDQWLWHJWTXKJMSPZC'
            bot_api = api(seed)
            bot_db = Database('test_db.db')
            address_index = bot_db.get_address_index()
            new_address = bot_api.get_new_address(address_index)
            starting_balance = bot_api.get_balance(address)
            start_time = time.time()
            bundle = None
            try:
                bundle = bot_api.send_transfer(address,1,new_address,address_index)
            except:
                self.fail('Transfer Failed')
            validator = BundleValidator(bundle)
            self.assertTrue(validator.is_valid())
            end_time = time.time()
            end_balance = bot_api.get_balance(address)
            self.assertEqual(end_balance,starting_balance+1)
            print("Time elapsed: {0}s".format(end_time-start_time))

unittest.main()
