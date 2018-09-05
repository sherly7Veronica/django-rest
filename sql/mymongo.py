import pymongo

mymongo = pymongo.MongoClient('mongodb://localhost:27017/')

mydb = mymongo["mydatabase"]

mycol = mydb['customers']

mydict = { "name": "John", "address": "Highway 37" }
x = mycol.insert_one(mydict)

print(x.inserted_id)
