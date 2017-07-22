from __future__ import print_function
import urllib2
import json
import boto3

weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
weekdays_enum = list(enumerate(weekdays))

# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': "SessionSpeechlet - " + title,
            'content': "SessionSpeechlet - " + output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }


# --------------- Functions that control the skill's behavior ------------------

def get_welcome_response():
    session_attributes = {"hasAskedForMeals": False, "hasGivenPreference": False, "weekIndex": 0, "recipeListIndex": 0, "weekList": []}
    
    card_title = "Welcome"
    speech_output = "Hi, I'm Ramsay. Let's plan your meals for the week."
    reprompt_text = "Ask me what to cook so we can get started. " + speech_output
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))

def catch_invalid_intent():
    card_title = "Invalid intent"
    conditional_output = ""

    speech_output = "I didn't catch that." + conditional_output
    reprompt_text = None
    should_end_session = False
    return build_response(session['attributes'], build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))

def handle_session_end_request():
    card_title = "Session Ended"
    speech_output = "Thanks for using Ramsay in the kitchen. " \
                    "Have a nice day! "
    should_end_session = True
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))

def suggest_meals(intent, session):
    reprompt_text = "I didn't get that. . What kinds of foods do you like to eat? Tell me a single ingredient."
    
    card_title = "Prompt for Food Preference"
    speech_output = "What kinds of foods do you like to eat? Tell me a single ingredient."

    should_end_session = False
    
    session['attributes']['hasAskedForMeals'] = True
    return build_response(session['attributes'], build_speechlet_response(
        card_title, speech_output, None, should_end_session))

def set_food_preference(intent, session):
    reprompt_text = None
    
    foodPreference = intent['slots']['foodPreference']['value']
    speech_output = "I've saved your food preference. Here are some recipes. "

    
    food2forkKey = "7b63da247c98ee00e636fb5981667a7c"
    hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
       'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
       'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
       'Accept-Encoding': 'none',
       'Accept-Language': 'en-US,en;q=0.8',
       'Connection': 'keep-alive'}
    request = urllib2.Request("http://food2fork.com/api/search?key=" + food2forkKey + "&q=" + foodPreference, headers=hdr)
    
    session['attributes']['recipes'] = json.loads(urllib2.urlopen(request).read())['recipes']
    should_end_session = False
    session['attributes']['hasGivenPreference'] = True
    
    session['attributes']['weekIndex'] = 0
    make_list_for_week(intent, session)
    
    speech_output += "Would you like to eat " + session['attributes']['weekList'][0]['title'] + " for dinner on " + weekdays_enum[0][1]

    return build_response(session['attributes'], build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

def make_list_for_week(intent, session):
    weekIndex = session['attributes']['weekIndex']
    if weekIndex < 7 and weekIndex < len(session['attributes']['recipes']):
        session['attributes']['weekList'].append(session['attributes']['recipes'][session['attributes']['recipeListIndex']])
    session['attributes']['recipeListIndex'] += 1
    

def meal_validated(intent, session):
    reprompt_text = None
    speech_output = "Ok, I'll put you down for that meal on " + weekdays_enum[session['attributes']['weekIndex']][1] + ". ."
    should_end_session = False

    session['attributes']['weekIndex'] += 1
    weekIndex = session['attributes']['weekIndex']
    
    if weekIndex >= 7:
        return persist_to_db(intent, session)
    else:
        make_list_for_week(intent, session)
        speech_output += " Let's go to the next day. Would you like to eat " + session['attributes']['weekList'][weekIndex]['title'] + " for dinner on " + weekdays_enum[weekIndex][1]
        return build_response(session['attributes'], build_speechlet_response(intent['name'], speech_output, reprompt_text, should_end_session))
    
def meal_not_validated(intent, session):
    weekIndex = session['attributes']['weekIndex']
    reprompt_text = "Would you like to eat " + session['attributes']['weekList'][weekIndex]['title'] + " for dinner on " + weekdays_enum[weekIndex][1]
    speech_output = "Ok, I've removed that meal for you on " + weekdays_enum[session['attributes']['weekIndex']][1]
    should_end_session = False
    
    session['attributes']['weekList'].pop(weekIndex)
    make_list_for_week(intent, session)
    
    speech_output += " Would you like to eat " + session['attributes']['weekList'][weekIndex]['title'] + " for dinner on " + weekdays_enum[weekIndex][1]
    
    return build_response(session['attributes'], build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

def persist_to_db(intent, session):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    weeklyPreferences = dynamodb.Table('weekly_preferences')
    weeklyPreferences.put_item(Item={'id': 0, 
    'Monday': session['attributes']['weekList'][0]['recipe_id'], 
    'Tuesday': session['attributes']['weekList'][1]['recipe_id'],
    'Wednesday': session['attributes']['weekList'][2]['recipe_id'],
    'Thursday': session['attributes']['weekList'][3]['recipe_id'],
    'Friday': session['attributes']['weekList'][4]['recipe_id'],
    'Saturday': session['attributes']['weekList'][5]['recipe_id'],
    'Sunday': session['attributes']['weekList'][6]['recipe_id']})
    
    food2forkKey = "7b63da247c98ee00e636fb5981667a7c"
    hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
       'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
       'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
       'Accept-Encoding': 'none',
       'Accept-Language': 'en-US,en;q=0.8',
       'Connection': 'keep-alive'}
       
    recipes = dynamodb.Table('recipes')
    for i in range (0, 7) :
        request = urllib2.Request("http://food2fork.com/api/get?key=" + food2forkKey + "&rId=" + session['attributes']['weekList'][i]['recipe_id'], headers=hdr)
        recipes.put_item(Item={'recipeId': session['attributes']['weekList'][i]['recipe_id'], 
        'name': session['attributes']['weekList'][i]['title'],
        'ingredients': json.loads(urllib2.urlopen(request).read())['recipe']['ingredients']})
    
    reprompt_text = None
    speech_output = "Ok, I've saved your meal preferences. You can ask me to read them back to you, or you can go do something else now."
    should_end_session = False
    return build_response(session['attributes'], build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))
    
def load_from_db(intent, session):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    weeklyPreferences = dynamodb.Table('weekly_preferences')
    
    listOfMeals = weeklyPreferences.get_item(Key={'id': 0})['Item']
    userQuery = intent['slots']['Weekorday']['value'].title().encode("ascii")
    
    reprompt_text = "I didn't catch that."
    speech_output = ""
    should_end_session = False

    recipes = dynamodb.Table('recipes')
    if userQuery == "Week" or userQuery == "week":
        for i in range(0, 7):
            mealName = recipes.get_item(Key={'recipeId': listOfMeals[weekdays_enum[i][1]]})['Item']
            speech_output += "You are eating " + mealName['name'] + " for dinner on " + weekdays_enum[i][1] + ". "
    else:
        mealName = recipes.get_item(Key={'recipeId': listOfMeals[userQuery]})['Item']
        speech_output += "You are eating " + mealName['name'] + " for dinner on " + userQuery + ". "
    
    return build_response(session['attributes'], build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))
        
def load_ingredients(intent, session):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    weeklyPreferences = dynamodb.Table('weekly_preferences')
    
    listOfMeals = weeklyPreferences.get_item(Key={'id': 0})['Item']
    userQuery = intent['slots']['ingredientsDay']['value'].title().encode("ascii")
    
    reprompt_text = "I didn't catch that."
    speech_output = "You need "
    should_end_session = False

    recipes = dynamodb.Table('recipes')
    mealIngredients = recipes.get_item(Key={'recipeId': listOfMeals[userQuery]})['Item']
    for i in range(len(mealIngredients['ingredients'])):
        speech_output += mealIngredients['ingredients'][i] + ", , , "
    speech_output += " for dinner on " + userQuery + ". "
    
    return build_response(session['attributes'], build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))
    
    
# --------------- Events ------------------

def on_session_started(session_started_request, session):
    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch
    return get_welcome_response()


def on_intent(intent_request, session):
    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    if intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    else:
        return ramsay_flow(intent, session)

def ramsay_flow(intent, session):

    intent_name = intent['name']

    if intent_name == "SuggestMeals":
        if session['attributes']['hasAskedForMeals']:
            conditional_output = " We already did that. Let's plan some meals for you."
            return redirect_flow(intent, session, conditional_output)
        else:
            return suggest_meals(intent, session)
    elif intent_name == "SetFoodPreference":
        if not session['attributes']['hasAskedForMeals']:
            conditional_output = " Ask me for some meal ideas, and we'll get started."
            return redirect_flow(intent, session, conditional_output)
        else:
            return set_food_preference(intent, session)
    elif intent_name == "MealValidated":
        return meal_validated(intent, session)
    elif intent_name == "MealNotValidated":
        return meal_not_validated(intent, session)
    elif intent_name == "LoadWeek":
        return load_from_db(intent, session)
    elif intent_name == "LoadIngredients":
        return load_ingredients(intent, session)
    else:
        return catch_invalid_intent(intent, session)

def redirect_flow(intent, session, conditional_output):
    reprompt_text = None
    speech_output = "Oops, " + conditional_output
    should_end_session = False
    
    return build_response(session['attributes'], build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

def on_session_ended(session_ended_request, session):
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    reprompt_text = None
    speech_output = "I'm leaving the kitchen now. . Goodbye."
    should_end_session = True
    return build_response(session['attributes'], build_speechlet_response(
        "Goodbye", speech_output, reprompt_text, should_end_session))


# --------------- Main handler ------------------

def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    if (event['session']['application']['applicationId'] != "amzn1.ask.skill.c82faa2f-942e-4a96-99e7-2f7768140b28"):
        raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']}, event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])
