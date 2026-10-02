import sqlite3

conn = sqlite3.connect("Database/Database.db")
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cur.fetchall()
print("数据库里所有表：", tables)

# 注意！这里是 Users，不是 customer
print("\n===== Users 用户账号表 =====")
for row in cur.execute("SELECT * FROM Users"):
    print(row)

print("\n===== Books图书表 =====")
for row in cur.execute("SELECT * FROM Books"):
    print(row)

conn.close()
