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

print("\n==== reserve 预约表 ====")
for row in cur.execute("SELECT * FROM reserve"):
    print(row)

print("\n==== borrow__record 借阅记录表 ====")
for row in cur.execute("SELECT * FROM borrow_record"):
    print(row)

print("\n==== message_notify 消息通知表 ====")
for row in cur.execute("SELECT * FROM message_notify"):
    print(row)

conn.close()
