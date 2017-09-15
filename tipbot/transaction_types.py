import time

class Deposit:
    """
    This class represents a deposit request
    Parameters:
        reddit_username: The username of the user that made the deposit request
        message: The message in which the request originated
        address: The address to which the user must deposit(is None then the user must be assigned an address)
    """    

    def __init__(self, reddit_username, message, address=None):
        self.reddit_username = reddit_username
        self.message = message
        self.address = address
        self.deposit_time = time.time()
    
class Withdraw:
    """
    This class represents a withdraw request
    Parameters:
        reddit_username: The username of the user that made the withdraw request
        message: The message in which the request originated
        address: The address to send the iota to
        amount: The amount of iota to send
    """
       
    def __init__(self,reddit_username, message, address, amount):
        self.reddit_username = reddit_username
        self.message = message
        self.address = address
        self.amount = amount
        self.withdraw_time = time.time()
