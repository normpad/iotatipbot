import praw
import re
import threading
import time
import queue
import random
import string
from iota import *
from bot_api import api,Database
import logging
import config
from transaction_types import Deposit, Withdraw

#Grab static variables from the config
seed = config.seed

#Initialize the api and reddit
bot_api = api(seed)
reddit = praw.Reddit(
    user_agent=config.user_agent,
    client_id=config.client_id,
    client_secret=config.client_secret,
    username=config.username,
    password=config.password
)

logging.basicConfig(filename='transactionLogs.log',format='%(levelname)s: %(asctime)s: %(message)s ',level=logging.INFO)

#Message links to be appended to every message/comment reply
help_message = "iotaTipBot is a bot that allows reddit users to send iota to each other through reddit comments. The bot commands are as follows:\n\n* 'Deposit' - Initiates the process of depositing iota into your tipping account\n\n* 'Withdraw' - Withdraw iota from your tipping account. You must put the address you want to withdraw to and the amount of iota in the message.\n\n* 'Balance' - Check the amount of iota you have stored in the bot.\n\n* 'Help' - Sends the help message\n\n* 'Donate' - Get a list of options to help support the project.\n\nThese commands are activated by sending the command to the bot either in the subject or the body of the message.\n\nOnce you have iota in your tipping account you can start tipping! To do this simply reply to a comment with a message of the format: '+<amount> iota'\n\nFor example '+25 iota' will tip 25 iota to the author of the comment you replied to. To tip higher values, you can swap the 'iota' part of the comment with 'miota' to tip megaIota values: '+25 miota' will then tip 25 megaIota.\n\nIf you are new to iota and are looking for more information here are a few useful links:\n\n* [Reddit Newcomer Information](https://www.reddit.com/r/Iota/comments/61rc0c/for_newcomers_all_information_links_you_probably/)\n\n* [IOTA Wallet Download](https://github.com/iotaledger/wallet/releases/)\n\n* [Supply and Units Reference](https://i.imgur.com/lsq4610.jpeg)"
message_links = "\n\n[Deposit](https://np.reddit.com/message/compose/?to=iotaTipBot&subject=Deposit&message=Deposit iota!) | [Withdraw](https://np.reddit.com/message/compose/?to=iotaTipBot&subject=Withdraw&message=I want to withdraw my iota!\nxxx iota \naddress here) | [Balance](https://np.reddit.com/message/compose/?to=iotaTipBot&subject=Balance&message=I want to check my balance!) | [Help](https://www.reddit.com/r/iotaTipBot/wiki/index) | [Donate](https://np.reddit.com/message/compose/?to=iotaTipBot&subject=Donate&message=I want to support iotaTipBot!)\n"

bot_db = Database()
bot_db_lock = threading.Lock()

#A thread to handle deposits
#Deposits are handled in 2 phases. 
#   Phase1: A unique 0 balance address is generated and given to the user
#   Phase2: The address is checked for a balance, if the address has a balance greater than 0
#           then the user has deposited to that address and their account should be credited
deposit_queue = queue.Queue()
def deposits():
    bot_api = api(seed)
    deposits = []
    print("Deposit thread started. Waiting for deposits...")

    while True:
        time.sleep(1)
        try:
            #Check the queue for new deposits, add them to the database and local deposit list.
            new_deposit = deposit_queue.get(False)
            deposits.append(new_deposit)
            print("New deposit received: (" + new_deposit.reddit_username + ")")
        except queue.Empty:
            pass
        for index,deposit in enumerate(deposits):
            reddit_username = deposit.reddit_username
            message = deposit.message
            address = deposit.address

            if address is None:

                #lock the database
                #generate the address
                #add the address to the used addresses
                #make sure address has 0 balance
                with bot_db_lock:
                    while True:
                        address_index = bot_db.get_address_index()
                        address = bot_api.get_new_address(address_index)
                        bot_db.add_used_address(address_index,address._trytes.decode("utf-8"))
                        if bot_api.get_balance(address) == 0:
                            break
                    
                reply = "Please transfer your IOTA to this address:\n{0}\n\nDo not deposit to the same address more than once. This address will expire in 5 hours".format(address._trytes.decode("utf-8"))
                logging.info('{0} was assigned to address {1}'.format(reddit_username,address._trytes.decode("utf-8")))
                message.reply(reply + message_links)
                with bot_db_lock:
                    bot_db.remove_deposit_request(deposit)
                    deposit.address = address
                    bot_db.add_deposit_request(deposit)
                del deposits[index]
                deposits.append(deposit)

            else:
                deposit_time = deposit.deposit_time

                #Check if the deposit request has expired
                if (time.time() - deposit_time) > 18000:
                    reply = ('Your deposit request has timed out. Please start a new deposit. Do not transfer to the previous address.')
                    message.reply(reply+message_links)
                    with bot_db_lock:
                        bot_db.remove_deposit_request(deposit)
                    logging.info('{0}\'s deposit has timed out'.format(reddit_username))
                    del deposits[index]
                else:
                    address = deposit.address
                    reddit_username = deposit.reddit_username
                    balance = bot_api.get_balance(address)
                    if balance > 0:
                        print("Transaction found, {0} transfered {1} iota".format(reddit_username,balance))
                        with bot_db_lock:
                            bot_db.add_balance(reddit_username,balance)
                        reply = ('You have successfully funded your tipping account with {0} iota'.format(balance))
                        message.reply(reply + message_links)
                        with bot_db_lock:
                            bot_db.remove_deposit_request(deposit)
                        logging.info('{0} deposited {1} iota'.format(reddit_username,balance))
                        del deposits[index]

#Start the deposit thread
deposit_thread = threading.Thread(target=deposits,args = ())
deposit_thread.daemon = True
deposit_thread.start()
                

#This thread handles all withdraw requests
#Withdraw requests are pulled from the queue and executed one by one
withdraw_queue = queue.Queue()
def withdraws():
    withdraws = []
    print("Withdraw thread started. Waiting for withdraws...")
    
    while True:
        time.sleep(1)
        try:
            new_withdraw = withdraw_queue.get(False)    
            withdraws.append(new_withdraw)
            print("New withdraw received: ({0},{1})".format(new_withdraw.reddit_username,new_withdraw.amount))
            print("{0} withdraws in queue".format(withdraw_queue.qsize()))
        except queue.Empty:
                pass
        for index,withdraw in enumerate(withdraws):
            reddit_username = withdraw.reddit_username
            message = withdraw.message
            amount = withdraw.amount
            address = withdraw.address
            print("Sending transfer to address {0} of amount {1}".format(address.decode("utf-8"),amount))
            with bot_db_lock:
                address_index = bot_db.get_address_index()
                new_address = bot_api.get_new_address(address_index)
                bot_db.add_used_address(address_index,new_address._trytes.decode("utf-8"))
            bot_api.send_transfer(address,amount,new_address,address_index)
            print("Transfer complete.")
            logging.info('{0} withdrew {1} iota to address: {2}'.format(reddit_username,amount,address.decode("utf-8")))
            reply = "You have successfully withdrawn {0} IOTA to address {1}".format(amount,address.decode("utf-8"))
            message.reply(reply + message_links)
            with bot_db_lock:
                bot_db.remove_withdraw_request(withdraw)
            del withdraws[index]

withdrawThread = threading.Thread(target=withdraws,args = ())
withdrawThread.daemon = True
withdrawThread.start()

subreddit = reddit.subreddit(config.subreddits)
#Monitor all subreddit comments for tips
def monitor_comments():
    bot_api = api(seed)
    with bot_db_lock:
        comments_replied_to = bot_db.get_comments_replied_to()
    print("Comment thread started. Waiting for comments...")
    while True:
        try:
            for comment in subreddit.stream.comments():
                if not comment.fullname in comments_replied_to:
                    author = comment.author.name
                    if bot_api.is_tip(comment):
                        amount = bot_api.get_iota_tip_amount(comment)
                        with bot_db_lock:
                            valid = bot_db.check_balance(author,amount)
                        if valid:
                            parent_comment = comment.parent()
                            if parent_comment.author is None:
                                continue
                            recipient = parent_comment.author.name
                            with bot_db_lock:
                                bot_db.subtract_balance(author,amount)
                                bot_db.add_balance(recipient,amount)
                            print('Comment Thread: {0} tipped {1}'.format(author,recipient))
                            logging.info('{0} has tipped {1} {2} iota'.format(author,recipient,amount))
                            value = bot_api.get_iota_value(amount)
                            reply = "You have successfully tipped {0} {1} iota(${2}).".format(recipient,amount,'%f' % value)
                            comment.reply(reply + message_links)
                            comments_replied_to.append(comment.fullname)
                            with bot_db_lock:
                                bot_db.add_replied_to_comment(comment.fullname)
                            parent_comment.author.message("You have received a tip!","You received a tip of {0} iota from {1}".format(amount,author))
                        else:
                            reply = "You do not have the required funds."
                            comment.reply(reply + message_links)
                            comments_replied_to.append(comment.fullname)
                            with bot_db_lock:
                                bot_db.add_replied_to_comment(comment.fullname)
        except:
            print("Comment Thread Exception... Restarting...")


comment_thread = threading.Thread(target=monitor_comments,args = ())
comment_thread.daemon = True
comment_thread.start()

def periodic_check():
    print("Periodic Check thread started")
    while True:
        bot_api = api(seed)
        with bot_db_lock:
            total_balance = bot_db.get_total_balance()
            address_index = bot_db.get_address_index()
        account_balance = bot_api.get_account_balance(address_index)
        difference = account_balance - total_balance
        if total_balance == account_balance:
            print("Periodic Check Thread: Account balance matches total user balance:{0}.".format(account_balance))
            logging.info('Account balance matches total user balance:{0}'.format(account_balance))
        elif total_balance > account_balance:
            print("Periodic Check Thread: Account balance({0}) is less than user balance({1})! Difference: {2}".format(account_balance,total_balance,difference))
            logging.info('Account balance({0}) is less than user balance({1})'.format(account_balance,total_balance))
        elif total_balance < account_balance:
            print("Periodic Check Thread: Account balance({0}) is greater than user balance({1}). Difference: {2}".format(account_balance,total_balance,difference))
            logging.info('Account balance({0}) is greater than user balance({1})'.format(account_balance, total_balance))
        
        with bot_db_lock:
            used_addresses = bot_db.get_used_addresses()
        address_list = []
        print("Periodic Check Thread: {0} addresses have been used".format(len(used_addresses)))
        for address in used_addresses:
            address_list.append(address[1])
        for address in used_addresses:
            if address_list.count(address[1]) > 1:
                print("Periodic Check Thread: Duplicated address: {0} index {1}".format(address[1],address[0]))
        time.sleep(1800)

periodic_check_thread = threading.Thread(target=periodic_check, args = ())
periodic_check_thread.daemon = True
periodic_check_thread.start()

print("Message thread started. Waiting for messages...")


#Reinitiate any requests that were not completed
with bot_db_lock:
    deposit_requests = bot_db.get_deposit_requests()
    withdraw_requests = bot_db.get_withdraw_requests()

for deposit_request in deposit_requests:
    message_id = deposit_request[0]
    address = deposit_request[1]
    if address is not None:
        address = Address(address)
    message = reddit.inbox.message(message_id)
    reddit_username = message.author.name
    deposit = Deposit(reddit_username,message,address)
    deposit_queue.put(deposit)

for withdraw_request in withdraw_requests:
    message_id = withdraw_request[0]
    address = bytearray(withdraw_request[1],'utf-8')
    amount = withdraw_request[2]
    message = reddit.inbox.message(message_id)
    reddit_username = message.author.name
    withdraw = Withdraw(reddit_username,message,address,amount)
    withdraw_queue.put(withdraw)


print("Bot initalized.")

#Main loop, Check through messages and comments for requests
while True:
    time.sleep(1)
    try:
        for message in reddit.inbox.messages():
            #print(message.author)
            #print(message.subject)
            #print(message.body)


            #It's a new message, see what it says
            if message.new:
                if message.author is None:
                    continue
                reddit_username = message.author.name

                #Check if it is a deposit request
                if bot_api.is_deposit_request(message):
                    deposit = Deposit(reddit_username,message)
                    deposit_queue.put(deposit)
                    with bot_db_lock:
                        bot_db.add_deposit_request(deposit)
                    #reply = "Deposits are currently disabled until some issues can be sorted out. Thank you for your patience."
                    #message.reply(reply + message_links)
                    message.mark_read()

                #Check if it is a withdraw request
                elif bot_api.is_withdraw_request(message):

                    #Check how much they want to withdrawl
                    if bot_api.contains_iota_amount(message):
                        amount = bot_api.get_iota_amount(message)
                        with bot_db_lock:
                            valid = bot_db.check_balance(reddit_username,amount)
                        if valid:
                            #Find address
                            address = bot_api.get_message_address(message)
                            if address:
                                with bot_db_lock:
                                    bot_db.subtract_balance(reddit_username,amount)
                                transfer = Withdraw(reddit_username,message,address,amount)
                                withdraw_queue.put(transfer)
                                with bot_db_lock:
                                   bot_db.add_withdraw_request(transfer)
                                reply = "Your withdraw has been received and is being processed. Please be patient the withdraw process may take up to a few hours."
                                message.reply(reply + message_links)
                                message.mark_read()
                            else:
                                reply = "You must put the address you want to withdraw to in your message"
                                message.reply(reply + message_links)
                                message.mark_read()
                        else:
                            with bot_db_lock:
                                balance = bot_db.get_user_balance(reddit_username)
                            reply = "Sorry, you don't have {1} IOTA in your account. You currently have {0} IOTA.".format(balance, amount)
                            message.reply(reply + message_links)
                            message.mark_read()
                    else:
                        reply = "You must put the amount of IOTA you want to withdraw in your message. Format: 1024 IOTA"
                        message.reply(reply + message_links)
                        message.mark_read()
    

                #Check if it is a balance request
                elif bot_api.is_balance_request(message):
                    with bot_db_lock:
                        balance = bot_db.get_user_balance(reddit_username)
                    reply = "Your current balance is: {0} iota.".format(balance)
                    message.reply(reply + message_links)
                    message.mark_read()

                elif bot_api.is_help_request(message):
                    message.reply(help_message + message_links)
                    message.mark_read()
        
                elif bot_api.is_donation_request(message):
                    reply = "Donations help keep this project alive! They help to cover server costs and development time. If you would like to support this project there are many options! Transfer cryptocurrency to one of the addresses below or simply tip the bot! Thank you for your support!\n\nIOTA: IYFJCTTLRIWUWAUB9ZLCRKVKAAQVWHWTENKVVZBXYUPU9YFTBMKFXYWXWESLWJSTBRADUSGVJPVJZCJEZ9IGYDKDJZ\n\nEthereum: 0x254EBc1863FD4eE5F4469b9A18505aF8de958812\n\nBitcoin: 18VhQTN9QcwJNQwMTb2H2AsvCaGsNfzKNK"
                    message.reply(reply+message_links)
                    message.mark_read()

                else:
                    message.reply(help_message + message_links)
                    message.mark_read()
    except:
        print("Message Thread Exception...")
