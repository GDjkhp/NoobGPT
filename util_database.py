import pymongo, os
myclient = pymongo.MongoClient(os.getenv('MONGO'))