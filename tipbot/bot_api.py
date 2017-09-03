import re
from iota import *
import praw
import sqlite3
import random
import string
from iota.adapter.wrappers import RoutingWrapper
import config
import urllib.request
from urllib.error import HTTPError
import json
import math

node_address = config.node_address

class api:


    def __init__(self,seed,prod=True):
        self.address_index = 1
        if prod:
            self.init_db()
        self.iota_api = Iota(
            RoutingWrapper(node_address)
                .add_route('attachToTangle','http://localhost:14265'),seed)

    def init_db(self):
        self.conn = sqlite3.connect(config.database_name)
        self.db = self.conn.cursor()
        self.create_database()
        self.address_index = len(self.db.execute("SELECT * FROM usedAddresses").fetchall())
        
    def init_custom_db(self,name):
        self.conn = sqlite3.connect(name)
        self.db = self.conn.cursor()
        self.create_database()
        self.address_index = len(self.db.execute("SELECT * FROM usedAddresses").fetchall())

    def get_iota_value(self,amount):
        try:
            with urllib.request.urlopen('https://api.coinmarketcap.com/v1/ticker/iota/') as url:
                data = json.loads(url.read().decode())[0]
                price = data['price_usd']
                value = (amount/1000000)*float(price)
                return value
        except:
            return amount/1000000
        

    #---------IOTA API FUNCTIONS--------------#
    def send_transfer(self,addr,amount):
        new_address = self.get_new_address()
        ret = self.iota_api.send_transfer(
            depth = 3,
            transfers = [
                ProposedTransaction(
                    address = Address(
                        addr
                    ),
                    value = amount,
                ), 
            ],
            min_weight_magnitude=15,
            change_address = new_address
        )
        return ret

    def get_account_balance(self):
        addresses = self.iota_api.get_new_addresses(0,self.address_index)['addresses']
        balances = self.iota_api.get_balances(addresses)['balances']
        total = 0
        for balance in balances:
            total = total + balance
        return total
    
    def get_balance(self,address):
        address_data = self.iota_api.get_balances([address])
        return address_data['balances'][0]


    def get_new_address(self):
        addresses = self.iota_api.get_new_addresses(self.address_index,1)
        for address in addresses['addresses']:
            address = address.with_valid_checksum()
            self.add_used_address(self.address_index,address._trytes.decode("utf-8"))
            self.address_index = self.address_index + 1
            if self.get_balance(address) > 0:
                return self.get_new_address()
            return address

    def create_seed(self):
        seed = ''.join(random.choice(string.ascii_uppercase + "9") for _ in range(81))
        return seed

    def check_transaction(self,transaction):
        transaction_hash = transaction['bundle'].hash
        inclusion_states = self.iota_api.get_latest_inclusion([transaction_hash])
        return inclusion_states['states'][transaction_hash]

    def replay_bundle(self,transaction):
        transaction_hash = transaction['bundle'].tail_transaction.hash
        self.iota_api.replay_bundle(transaction_hash,3,15)
                

    #-------------MESSAGE REGEX FUNCTIONS---------------#

    #Check if the message body or subject contains a fund/deposit request
    def is_deposit_request(self,message):
        fund_string = re.compile("Fund",re.I)
        deposit_string = re.compile("Deposit",re.I)
        match = fund_string.search(message.subject)
        if match:
            return True
        match = fund_string.search(message.body)
        if match:
            return True
        match = deposit_string.search(message.subject)
        if match:
            return True
        match = deposit_string.search(message.body)
        if match:
            return True
        return False

    #Check if the message body or subject contains a withdraw request
    def is_withdraw_request(self,message):
        withdraw_string = re.compile("Withdraw",re.I)
        match = withdraw_string.search(message.subject)
        if match:
                return True
        match = withdraw_string.search(message.body)
        if match:
            return True
        return False

    #Check if the message body or subject contains a balance request
    def is_balance_request(self,message):
        balance_string = re.compile("Balance",re.I)
        match = balance_string.search(message.subject)
        if match:
            return True
        match = balance_string.search(message.body)
        if match:
            return True
        return False

    #Check if the message body or subject contains a help/commands request
    def is_help_request(self,message):
        help_string = re.compile("Help",re.I)
        commands_string = re.compile("Commands",re.I)
        match = help_string.search(message.subject)
        if match:
            return True
        match = help_string.search(message.body)
        if match:
            return True
        match = commands_string.search(message.subject)
        if match:
            return True
        match = commands_string.search(message.body)
        if match:
            return True
        return False

    #Check if the message body contains an iota amount
    def contains_iota_amount(self,message):
        iota_amount_string = re.compile("([0-9]+)\s*iota",re.I)
        miota_amount_string = re.compile("([0-9]+)\s*miota",re.I)
        match = iota_amount_string.search(message.body)
        if match:
            return True
        match = miota_amount_string.search(message.body)
        if match:
            return True
        return False

    #Return the iota amount refrenced in the message, convets miota to iota
    def get_iota_tip_amount(self,message):
        iota_amount_string = re.compile("\+\s*([0-9]+)\s*iota",re.I)
        miota_amount_string = re.compile("\+\s*([0-9]+)\s*miota",re.I)
        match = iota_amount_string.search(message.body)
        if match:
            return int(match.group(1))
        match = miota_amount_string.search(message.body)
        if match:
            return (int(match.group(1))*1000000)

    def get_iota_amount(self,message):
        iota_amount_string = re.compile("([0-9]+)\s*iota",re.I)
        miota_amount_string = re.compile("([0-9]+)\s*miota",re.I)
        match = iota_amount_string.search(message.body)
        if match:
            return int(match.group(1))
        match = miota_amount_string.search(message.body)
        if match:
            return (int(match.group(1))*1000000)

    def get_message_address(self,message):
        address_string = re.compile("[A-Z,9]{90}")
        match = address_string.search(message.body)
        if match:
            return bytearray(match.group(0),"utf-8")
        else:
            return None

    def is_tip(self,comment):
        tip_string_iota = re.compile("\+\s*[0-9]+\s*iota",re.I)
        tip_string_miota = re.compile("\+\s*[0-9]+\s*miota",re.I)
        text = comment.body
        match = tip_string_iota.search(text)
        if match:
            return True
        match = tip_string_miota.search(text)
        if match:
            return True
        return False

    def is_donation_request(self,message):
        donate_string = re.compile("donat",re.I)
        match = donate_string.search(message.subject)
        if match:
            return True
        match = donate_string.search(message.body)
        if match:
            return True
        return False


    #--------------------Database Functions----------------------#

    def create_database(self):
        self.db.execute("CREATE TABLE IF NOT EXISTS users (redditUsername TEXT PRIMARY KEY, balance INTEGER)")
        self.conn.commit()
        self.db.execute("CREATE TABLE IF NOT EXISTS commentsRepliedTo (commentId TEXT PRIMARY KEY)")
        self.conn.commit()
        self.db.execute("CREATE TABLE IF NOT EXISTS usedAddresses (addressIndex INTEGER PRIMARY KEY, address TEXT)")
        self.conn.commit()
        self.db.execute("CREATE TABLE IF NOT EXISTS depositRequests (messageId TEXT PRIMARY KEY, address TEXT)")
        self.conn.commit()
        self.db.execute("CREATE TABLE IF NOT EXISTS withdrawRequests (messageId TEXT PRIMARY KEY, address TEXT, amount INTEGER)")
        self.conn.commit()

    def add_new_user(self,reddit_username):
        entry = self.db.execute("SELECT * FROM users WHERE redditUsername=?",(reddit_username,)).fetchone()
        if not entry:
            self.db.execute("INSERT INTO users(redditUsername,balance) VALUES (?,?)",(reddit_username,0))
            self.conn.commit()
               
    def set_balance(self,reddit_username, amount):
        entry = self.db.execute("SELECT * FROM users WHERE redditUsername=?",(reddit_username,)).fetchone()
        if entry:
            self.db.execute("UPDATE users SET balance=? WHERE redditUsername=?",(amount,reddit_username))
            self.conn.commit()
        else:
            self.add_new_user(reddit_username)
            self.set_balance(reddit_username,amount)

    #Adds to a users balance
    def add_balance(self,reddit_username,amount):
        entry = self.db.execute("SELECT * FROM users WHERE redditUsername=?",(reddit_username,)).fetchone()
        if entry:
            balance = entry[1]
            balance = balance + amount
            self.set_balance(reddit_username,balance)
        else:
            self.add_new_user(reddit_username)
            self.add_balance(reddit_username,amount)

    #Subtracts from a users balance
    def subtract_balance(self,reddit_username,amount):
        entry = self.db.execute("SELECT * FROM users WHERE redditUsername=?",(reddit_username,)).fetchone()
        if entry:
            balance = entry[1]
            balance = balance - amount
            self.set_balance(reddit_username,balance)

    #Checks if the user has at least the given amount        
    def check_balance(self,reddit_username,amount):
        entry = self.db.execute("SELECT * FROM users WHERE redditUsername=?",(reddit_username,)).fetchone()
        if entry:
            balance = entry[1]
            if amount > balance:
                return False
            else:
                return True
        else:
            return False
     
    #Gets the balance for the speicifed user
    def get_user_balance(self,reddit_username):
        entry = self.db.execute("SELECT * FROM users WHERE redditUsername=?",(reddit_username,)).fetchone()
        if entry:
            balance = entry[1]
            return balance
        else:
            self.add_new_user(reddit_username)
            return self.get_user_balance(reddit_username)

    def get_total_balance(self):
        query = self.db.execute("SELECT * FROM users").fetchall()
        total = 0
        for entry in query:
            total = total + entry[1]
        return total

    def get_comments_replied_to(self):
        query = self.db.execute("SELECT commentId FROM commentsRepliedTo").fetchall()
        comments = []
        for entry in query:
            comments.append(entry[0])
        return comments

    def add_replied_to_comment(self,commentId):
        self.db.execute("INSERT INTO commentsRepliedTo(commentId) VALUES (?)",(commentId,))
        self.conn.commit()

    def add_used_address(self,index,address):
        self.db.execute("INSERT INTO usedAddresses(addressIndex,address) VALUES (?,?)",(index,address))
        self.conn.commit()

    def add_deposit_request(self,request):
        if request['type'] == 'deposit':
            address = request['address']
            reddit_username = request['reddit_username']
            message = request['message']
            message_id = message.fullname
            query = self.db.execute("SELECT * FROM depositRequests WHERE messageId=?",(message_id,)).fetchone()
            if query is not None:
                return
            self.db.execute("INSERT INTO depositRequests(messageId,address) VALUES (?,?)",(message_id,address._trytes.decode("utf-8")))
            self.conn.commit()

    def remove_deposit_request(self,request):
        if request['type'] == 'deposit':
            message = request['message']
            message_id = message.fullname
            self.db.execute("DELETE FROM depositRequests WHERE messageId=?",(message_id,))
            self.conn.commit()

    def get_deposit_requests(self):
        query = self.db.execute("SELECT * FROM depositRequests")
        return query.fetchall()

    def add_withdraw_request(self,request):
        address = request['address']
        message = request['message']
        message_id = message.fullname
        amount = request['amount']
        self.db.execute("INSERT INTO withdrawRequests(messageId,address,amount) VALUES (?,?,?)",(message_id,address.decode("utf-8"),amount))
        self.conn.commit()

    def remove_withdraw_request(self,request):
        message = request['message']
        message_id = message.fullname
        self.db.execute("DELETE FROM withdrawRequests WHERE messageId=?",(message_id,))
        self.conn.commit()

    def get_withdraw_requests(self):
        query = self.db.execute("SELECT * FROM withdrawRequests")
        return query.fetchall()

    def get_used_addresses(self):
        query = self.db.execute("SELECT * FROM usedAddresses")
        return query.fetchall()
