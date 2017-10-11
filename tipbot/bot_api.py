import re
from iota import *
import praw
import sqlite3
import random
import string
from iota.adapter.wrappers import RoutingWrapper
import config
import urllib.request
import json
import math
import time
import requests

node_address = config.node_address

class api:

    def __init__(self,seed):
        """
        Initializes the iota api
        Routes attachToTangle calls to local node
        Parameters:
            seed: The account seed
        """
        
        self.iota_api = Iota(
            RoutingWrapper(node_address)
                .add_route('attachToTangle','http://localhost:14265'),seed)
                      
        #Find the first address with non-zero balance
        self.starting_input = 0
        address_index = Database().get_address_index()
        if address_index != 0:
          used_addresses = self.iota_api.get_new_addresses(0,address_index)['addresses']
          balances = self.iota_api.get_balances(used_addresses)['balances']
          for i in range(0,len(balances)):
            if balances[i] != 0:
              self.starting_input = i
              break

    def get_iota_value(self,amount):
        """
        Returns the USD value of the given iota amount
        Parameters:
            amount: The amount of iota to get the value of
        """

        try:
            with urllib.request.urlopen('https://api.coinmarketcap.com/v1/ticker/iota/') as url:
                data = json.loads(url.read().decode())[0]
                price = data['price_usd']
                value = (amount/1000000)*float(price)
                return value
        except:
            return amount/1000000

    #---------IOTA API FUNCTIONS--------------#

    def send_transfer(self,addr,amount,new_address,index):
        """
        Wrapper function for iota.send_transfer
        Parameters:
            addr: the address to send the transfer to
            amount: the amount of iota to send 
            new_address: the address to migrate remaining iota to
            index: the current address index(i.e. the count of all the used addresses)
        Return:
            The bundle that was attached to the tangle
        """
        
        while True:
            try:  
                for i in range(self.starting_input + 1, index):
                    try:
                        input = self.iota_api.get_inputs(self.starting_input,i,amount)['inputs']
                        break
                    except iota.adapter.BadApiResponse:
                        pass
                ret = self.iota_api.send_transfer(
                    depth = 3,
                    transfers = [
                        ProposedTransaction(
                            address = Address(
                                addr
                            ),
                            value = amount,
                            tag = Tag(b'IOTATIPBOT')
                        ), 
                    ],
                    min_weight_magnitude=14,
                    change_address = new_address,
                    inputs = input
                )
                break
            except requests.exceptions.RequestException:
                print("Error sending transfer... Retrying...")
            
        bundle = ret['bundle'] 
        confirmed = False
        transaction_time = time.time()
        start_time = time.time()
        transactions_to_check = []
        transactions_to_check.append(bundle.tail_transaction)
        while not confirmed:
            for transaction in transactions_to_check:
                confirmed = self.check_transaction(transaction)
                if confirmed:
                    break
            if (time.time() - start_time) > (10*60) and not confirmed:
                trytes = self.replay_bundle(transaction)
                transactions_to_check.append(Transaction.from_tryte_string(trytes[0]))
                start_time = time.time()
        
        #Increment the starting input by the number of inputs used
        num_inputs = 0
        for t in bundle.__iter__():
            if t.value < 0:
                num_inputs = num_inputs + 1
        self.starting_input = self.starting_input + num_inputs
        return bundle

    def get_account_balance(self,index):
        """
        Returns the total balance of the iota account
        Parameters:
            index: the current address index(i.e. the count of all the used addresses)
        """

        while True:
            try:
              #Index must be at least 1
              if index==0:
                  index=1
              addresses = self.iota_api.get_new_addresses(self.starting_input,index)['addresses']
              balances = self.iota_api.get_balances(addresses)['balances']
              total = 0
              for balance in balances:
                  total = total + balance
              return total
            except requests.exceptions.RequestException:
                pass
    
    def get_balance(self,address):
        """
        Wrapper functon for iota.get_balances()
        Returns the balance of a single address
        Parameters:
            address: the address to get the balance of
        """

        while True:
            try:
                address_data = self.iota_api.get_balances([address])
                return address_data['balances'][0]
            except requests.exceptions.RequestException:
                pass


    def get_new_address(self,index):
        """
        Wrapper function for iota.get_new_addresses()
        Returns a single address of the given index with a valid checksum
        Parameters:
            index: the index of the address to get
        """

        addresses = self.iota_api.get_new_addresses(index,1)
        for address in addresses['addresses']:
            address = address.with_valid_checksum()
            return address

    def create_seed(self):
        """
        Generates a random seed
        Depricated and probably cryptographically insecure
        Do not use
        """

        seed = ''.join(random.choice(string.ascii_uppercase + "9") for _ in range(81))
        return seed

    def check_transaction(self,transaction):
        """
        Checks if the given transaction is confirmed       
        Parameters:
            transaction: The transaction to check.
        """
        
        while True:
            try:
                transaction_hash = transaction.hash
                inclusion_states = self.iota_api.get_latest_inclusion([transaction_hash])
                return inclusion_states['states'][transaction_hash]
            except requests.exceptions.RequestException:
                pass

    def replay_bundle(self,transaction):
        """
        Replays the given bundle
        Parameters:
            transaction: The transaction to replay.
        """

        while True:
            try:
                transaction_hash = transaction.hash
                return self.iota_api.replay_bundle(transaction_hash,3,14)['trytes']
            except requests.exceptions.RequestException:
                pass

    #-------------MESSAGE REGEX FUNCTIONS---------------#

    def is_deposit_request(self,message):
        """
        Check if the message body or subject contains a fund/deposit request
        Parameters:
            message: The message to check
        """

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

    def is_withdraw_request(self,message):
        """
        Check if the message body or subject contains a withdraw request
        Parameters:
            message: The message to check
        """

        withdraw_string = re.compile("Withdraw",re.I)
        match = withdraw_string.search(message.subject)
        if match:
                return True
        match = withdraw_string.search(message.body)
        if match:
            return True
        return False

    def is_balance_request(self,message):
        """
        Check if the message body or subject contains a balance request
        Parameters:
            message: The message to check
        """

        balance_string = re.compile("Balance",re.I)
        match = balance_string.search(message.subject)
        if match:
            return True
        match = balance_string.search(message.body)
        if match:
            return True
        return False

    def is_help_request(self,message):
        """
        Check if the message body or subject contains a help/commands request
        Parameters:
            message: The message to check
        """

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

    def contains_iota_amount(self,message):
        """
        Check if the message body contains an iota amount
        Parameters:
            message: The message to check
        """

        iota_amount_string = re.compile("([0-9]+)\s*iota",re.I)
        miota_amount_string = re.compile("([0-9]+)\s*miota",re.I)
        match = iota_amount_string.search(message.body)
        if match:
            return True
        match = miota_amount_string.search(message.body)
        if match:
            return True
        return False

    def get_iota_tip_amount(self,message):
        """
        Return the iota amount refrenced in the message, convets miota to iota
        Parameter:
            message: The message to get the iota tip amount from
        """
    
        iota_amount_string = re.compile("\+\s*([0-9]+)\s*iota",re.I)
        miota_amount_string = re.compile("\+\s*([0-9]+)\s*miota",re.I)
        miota_fraction_amount_string = re.compile("\+\s*([0-9]+.[0-9]+)\s*miota")
        match = iota_amount_string.search(message.body)
        if match:
            return int(match.group(1))
        match = miota_amount_string.search(message.body)
        if match:
            return (int(match.group(1))*1000000)
        match = miota_fraction_amount_string.search(message.body)
        if match:
            return(int(float(match.group(1))*1000000))

    def get_iota_amount(self,message):
        """
        Return the iota amount refrenced in the message, converts miota to iota
        Parameters:
            message: The message to get the iota amount from
        """

        iota_amount_string = re.compile("([0-9]+)\s*iota",re.I)
        miota_amount_string = re.compile("([0-9]+)\s*miota",re.I)
        match = iota_amount_string.search(message.body)
        if match:
            return int(match.group(1))
        match = miota_amount_string.search(message.body)
        if match:
            return (int(match.group(1))*1000000)

    def get_message_address(self,message):
        """
        Return the iota address refrenced in the message
        Parameters:
            message: The message to get the address from   
        """

        address_string = re.compile("[A-Z,9]{90}")
        match = address_string.search(message.body)
        if match:
            return bytearray(match.group(0),"utf-8")
        else:
            return None

    def is_tip(self,comment):
        """
        Check if the comment is a tip
        Parameters:
            comment: The comment to check
        """

        tip_string = re.compile("\+\s*[0-9]+\s*miota|\+\s*[0-9]+\s*iota|\+\s*[0-9]+.[0-9]+\s*miota",re.I)
        text = comment.body
        match = tip_string.search(text)
        if match:
            if self.get_iota_tip_amount(comment) == 0:
                return False
            else:
                return True
        return False

    def is_donation_request(self,message):
        """
        Check if the message is a donation request
        Parameters:
            message: The message to check
        """

        donate_string = re.compile("donat",re.I)
        match = donate_string.search(message.subject)
        if match:
            return True
        match = donate_string.search(message.body)
        if match:
            return True
        return False

    def is_mention(self,comment):
        mention_string = re.compile("u/iotaTipBot",re.I)
        match = mention_string.search(comment.body)
        if match:
            return True
        return False


class Database:
    """
    Implements necessary functions to read from and modify the database
    """

    def __init__(self,name=config.database_name):
        self.conn = sqlite3.connect(name,check_same_thread=False)
        self.db = self.conn.cursor()
        self.create_database()
        self.address_index = len(self.db.execute("SELECT * FROM usedAddresses").fetchall())
        
    def create_database(self):
        """
        Creates the database structure
        """
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
        """
        Add a new user to the database
        Parameters:
            reddit_username: The reddit username of the new user
        """
        entry = self.db.execute("SELECT * FROM users WHERE redditUsername=?",(reddit_username,)).fetchone()
        if not entry:
            self.db.execute("INSERT INTO users(redditUsername,balance) VALUES (?,?)",(reddit_username,0))
            self.conn.commit()
               
    def set_balance(self,reddit_username, amount):
        """
        Sets the balance of the given user
        Parameters:
            reddit_username: The reddit username of the user
            amount: The amount to set the user's balance to
        """
        entry = self.db.execute("SELECT * FROM users WHERE redditUsername=?",(reddit_username,)).fetchone()
        if entry:
            self.db.execute("UPDATE users SET balance=? WHERE redditUsername=?",(amount,reddit_username))
            self.conn.commit()
        else:
            self.add_new_user(reddit_username)
            self.set_balance(reddit_username,amount)

    def add_balance(self,reddit_username,amount):
        """
        Adds to a user's account balance
        Parameters:
            reddit_username: The reddit username of the user
            amount: The amount to add to the user's account
        """
        entry = self.db.execute("SELECT * FROM users WHERE redditUsername=?",(reddit_username,)).fetchone()
        if entry:
            balance = entry[1]
            balance = balance + amount
            self.set_balance(reddit_username,balance)
        else:
            self.add_new_user(reddit_username)
            self.add_balance(reddit_username,amount)

    def subtract_balance(self,reddit_username,amount):
        """
        Subtracts from a user's account balance
        Parameters:
            reddit_username: The reddit username of the user
            amount: The amount to subtract from the user's account
        """
        entry = self.db.execute("SELECT * FROM users WHERE redditUsername=?",(reddit_username,)).fetchone()
        if entry:
            balance = entry[1]
            balance = balance - amount
            self.set_balance(reddit_username,balance)

    def check_balance(self,reddit_username,amount):
        """
        Check if the user's balance is at least a given amount
        Parameters:
            reddit_username: The reddit username of the user
            amount: The amount to check
        """

        entry = self.db.execute("SELECT * FROM users WHERE redditUsername=?",(reddit_username,)).fetchone()
        if entry:
            balance = entry[1]
            if amount > balance:
                return False
            else:
                return True
        else:
            return False
     
    def get_user_balance(self,reddit_username):
        """
        Returns the user's account balance
        Parameters:
            reddit_username: The reddit username of the user
        """

        entry = self.db.execute("SELECT * FROM users WHERE redditUsername=?",(reddit_username,)).fetchone()
        if entry:
            balance = entry[1]
            return balance
        else:
            self.add_new_user(reddit_username)
            return self.get_user_balance(reddit_username)

    def get_total_balance(self):
        """
        Returns the total balance of all user's
        """

        query = self.db.execute("SELECT * FROM users").fetchall()
        total = 0
        for entry in query:
            total = total + entry[1]
        return total

    def get_comments_replied_to(self):
        """
        Returns a list of comment ids of all the comments that the bot has replied to        
        """

        query = self.db.execute("SELECT commentId FROM commentsRepliedTo").fetchall()
        comments = []
        for entry in query:
            comments.append(entry[0])
        return comments

    def add_replied_to_comment(self,comment_id):
        """
        Adds a comment id to to the database of replied to comments
        Parameters:
            commend_id: The id of the comment to add
        """

        self.db.execute("INSERT INTO commentsRepliedTo(commentId) VALUES (?)",(comment_id,))
        self.conn.commit()

    def add_used_address(self,index,address):
        """
        Adds an address to the database of used addresses
        Parameters:
            index: The index of the address
            address: The address to add to the database
        """
        self.db.execute("INSERT INTO usedAddresses(addressIndex,address) VALUES (?,?)",(index,address))
        self.conn.commit()

    def add_deposit_request(self,request):
        """
        Adds a deposit request to the database
        Parameters:
            request: The request to add
        """

        address = request.address
        reddit_username = request.reddit_username
        message = request.message
        message_id = message.id
        query = self.db.execute("SELECT * FROM depositRequests WHERE messageId=?",(message_id,)).fetchone()
        if query is not None:
            return
        if address is None:
            self.db.execute("INSERT INTO depositRequests(messageId) VALUES (?)",(message_id,))
        else:
            self.db.execute("INSERT INTO depositRequests(messageId,address) VALUES (?,?)",(message_id,address._trytes.decode("utf-8")))
        self.conn.commit()

    def remove_deposit_request(self,request):
        """
        Removes a deposit request from the database
        Parameters:
            request: The request to remove
        """

        message = request.message
        message_id = message.id
        self.db.execute("DELETE FROM depositRequests WHERE messageId=?",(message_id,))
        self.conn.commit()

    def get_deposit_requests(self):
        """
        Returns all the deposit requests in the database
        """

        query = self.db.execute("SELECT * FROM depositRequests")
        return query.fetchall()

    def add_withdraw_request(self,request):
        """
        Adds a withdraw request to the database
        Parameters:
            request: The request to add
        """

        address = request.address
        reddit_username = request.reddit_username
        message = request.message
        message_id = message.id
        amount = request.amount
        self.db.execute("INSERT INTO withdrawRequests(messageId,address,amount) VALUES (?,?,?)",(message_id,address.decode("utf-8"),amount))
        self.conn.commit()

    def remove_withdraw_request(self,request):
        """
        Removes a withdraw request from the database
        Parameters:
            request: The request to remove
        """
        
        message = request.message
        message_id = message.id
        self.db.execute("DELETE FROM withdrawRequests WHERE messageId=?",(message_id,))
        self.conn.commit()

    def get_withdraw_requests(self):
        """
        Returns all the withdraw requests in the database        
        """

        query = self.db.execute("SELECT * FROM withdrawRequests")
        return query.fetchall()

    def get_used_addresses(self):
        """
        Returns all the used addresses
        """

        query = self.db.execute("SELECT * FROM usedAddresses")
        return query.fetchall()

    def get_address_index(self):
        """
        Returns the current address index(i.e. the count of all the used addresses)
        """

        query = self.db.execute("SELECT * FROM usedAddresses")
        address_index = len(query.fetchall())
        return address_index 
