import sqlite3

conn = sqlite3.connect("botData.db")
db = conn.cursor()
data = db.execute("SELECT * FROM users")
print(data.fetchall())
print("")
data = db.execute("SELECT * FROM depositRequests")
print(data.fetchall())
print("")
data = db.execute("SELECT * FROM withdrawRequests")
print(data.fetchall())
input("")
