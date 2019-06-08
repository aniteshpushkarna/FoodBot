import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "client-secret.json"

import dialogflow_v2 as dialogflow
dialogflow_session_client = dialogflow.SessionsClient()
PROJECT_ID = "asgbot-ygltqt"


from py_edamam import Edamam

e = Edamam(nutrition_appid='d015cb6b',
           nutrition_appkey='1ae1d390a264b8f9b580ff7b119b75c4',
           recipes_appid='4fb8ed0b',
           recipes_appkey='d5f40c775494439745fcb86bfd80f4e9',
           food_appid='5d30c9d4',
           food_appkey='336bc9809579d5d6704ea285298de11a')

def get_recipe(text):
    p = e.search_recipe(text)
    recipe_str = p['hits'][0]['recipe']['ingredientLines']
    recipe = str(p['q'])
    for row in recipe_str:
        recipe += '\n\n{}'.format(row)
    img = p['hits'][0]['recipe']['image']
    
    return recipe,img

#Mongo Db Code
import pymongo

def increment_db(text,col_name):
    client = pymongo.MongoClient("mongodb+srv://foodbot:foodbotpsw@cluster0-fdejn.mongodb.net/test?retryWrites=true&w=majority")
    mydb = client.test
    mycol = mydb[col_name]

    query = {'q':text}
    if mycol.count_documents(query) == 0:
        mycol.insert_one({'q':text,'count':1})
    else:
        count = int(mycol.find(query)[0]['count'])+1
        mycol.update_one({'q':text},{'$set':{'count':count}})

def get_max_query_db(col_name):
    client = pymongo.MongoClient("mongodb+srv://foodbot:foodbotpsw@cluster0-fdejn.mongodb.net/test?retryWrites=true&w=majority")
    mydb = client.test
    mycol = mydb[col_name]
    return mycol.find(sort=[('count',pymongo.DESCENDING)])[0]['q']

def detect_intent_from_text(text, session_id, language_code='en'):
    session = dialogflow_session_client.session_path(PROJECT_ID, session_id)
    text_input = dialogflow.types.TextInput(text=text, language_code=language_code)
    query_input = dialogflow.types.QueryInput(text=text_input)
    response = dialogflow_session_client.detect_intent(session=session, query_input=query_input)
    return response.query_result

def fetch_reply(msg,session_id):
    response = detect_intent_from_text(msg,session_id)
    
    if response.intent.display_name == 'get_recipe':
        if response.parameters['recipe'] != 'favorite':
            recipe , img = get_recipe(response.parameters['recipe'])
            #increment in db
            increment_db(response.parameters['recipe'],session_id+'recipe')

            return str(recipe),img
        else:
            q = get_max_query_db(session_id+'recipe')
            recipe,img = get_recipe(q)
            return str(recipe),img

    elif response.intent.display_name == 'get_nutrition':
        if response.parameters['food_type'] != 'favorite':
            l = e.search_food(response.parameters['food_type'])
            #increment in db
            increment_db(response.parameters['food_type'],session_id+'food')
            return l['text'],l['parsed'][0]['food']['image']
        else:
            q = get_max_query_db(session_id+'food')
            l = e.search_food(q)
            return l['text'],l['parsed'][0]['food']['image']
    else:
        return response.fulfillment_text