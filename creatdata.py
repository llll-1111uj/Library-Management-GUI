import sqlite3, csv

conn = sqlite3.connect(r"Database/Database.db")
cur = conn.cursor()

# 清空表所有数据
cur.execute("DELETE FROM Books;")
conn.commit()

count_ok = 0
with open("library_books.csv", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for idx, r in enumerate(reader, start=1):
        try:
            bid = int(r["图书ID"])
            cur.execute('''
INSERT INTO Books(book_id,name,author) VALUES(?,?,?)
''', (bid, r["书名"], r["作者"]))
            count_ok += 1
        except Exception as e:
            print(f"第{idx}行插入失败，ID:{r['图书ID']}，错误：{e}")

conn.commit()
cnt = cur.execute("SELECT COUNT(*) FROM Books").fetchone()[0]
print(f"成功插入 {count_ok} 行，数据库Books表总记录数：{cnt}")
