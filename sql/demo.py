import mysql.connector


mydb = mysql.connector.connect(
    host="localhost",
)

mycursor = mydb.cursor()

sql = "CREATE TABLE customers"

mycursor.execute(sql)

mydb.commit()

print(mydb)
