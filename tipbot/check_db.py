import sqlite3
import config

conn = sqlite3.connect(config.database_name)
db = conn.cursor()
data = db.execute("SELECT * FROM users").fetchall()
print('{0} Users:'.format(len(data)))
data = db.execute("SELECT * FROM depositRequests").fetchall()
print('{0} deposit requests'.format(len(data)))
data = db.execute("SELECT * FROM withdrawRequests").fetchall()
print('{0} withdraw requests'.format(len(data)))
data = db.execute("SELECT * FROM usedAddresses").fetchall()
print('{0} used addresses'.format(len(data)))
input("")
