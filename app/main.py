# FastAPI Components to build the web app.
from fastapi import FastAPI, Request, Form # Imports FastAPI , Request for handling HTTP requests & Form to accept data submitted via POST Requests
from fastapi.responses import HTMLResponse, RedirectResponse # Specifies that a route returns HTML
from fastapi.staticfiles import StaticFiles # Serves Static Files Like CSS, JS & Images
from fastapi.templating import Jinja2Templates  # Imports Jinja2 template support

# Utilities & Database Connection Classes
from dotenv import load_dotenv # Loads secrets from .env.
from pathlib import Path # Provides object-oriented file system paths
from mongo.mongo import Co2 # Imports the Co2Connection Class for MongoDB  Schemas
from utilities.utils import AppUtils # Imports the data processing functions
from database.database import SessionLocal # Imports SQLAlchemy engine connected to the database, dependency function to provide DB Session and declarative Base for models to create tables

# Loads enviroment variables from .env file to retrieve sensitive data securely
load_dotenv() # Loads secrets

# Initializes FastAPI Web Application
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static") # Mounts the 'static' Files directory making it accessible via '/static' URL 
templates = Jinja2Templates(directory=Path(__file__).parent.parent/"templates")  # Sets up Jinja2Templates for dynamic HTML rendering from templates folder

# Database Initialization
mongo = Co2() # Initializes the earlier imported MongoDB handler class & creates an instance of the Co2 class

# Starta a new database session using SessionLocal using with to ensure session is properly opened and closed even if an error occurs
with SessionLocal() as db:
    items = AppUtils.get_data_grouped_by_category(db) # Returns a list of items grouped by category using the AppUtils defined method

# Inserts Items into Mongo DB co2 Database if documents empty
if mongo.co2.count_documents({}) == 0:
    mongo.insert_items(items) 

# DEMO PAGE ROUTES
# Route for the demopage ('/') that returns an HTML response displaying items
@app.get("/", response_class=HTMLResponse)
def demo(request: Request):

    # Calculates the total CO2 emission based on item's counts and CO2 per item
    total_co2 = sum(
        (item.get('co2', 0))
        for category in items
        for item in category['items'])
    
    equivalents = AppUtils.calculate_equivalents(total_co2)  # Calculates how mmuch C02 is equivalent to driving a car, riding a bus or flying in a plane using the AppUtils calculate session function

    context = {
        "request": request, # Passes the request for Jinja2 to access
        "items": items,  # Passes items data to be rendered
        "equivalents": equivalents, # C02 equivalent in different modes of transport
        "total_co2": total_co2, # Total C02 emitted based on selected items
    }
    # Renders the response
    response = templates.TemplateResponse("demo.html", context)
    return response 

# Route to handle form submissions of incrementing & decrementing counts on demo page
@app.post("/", response_class=HTMLResponse)
def update_count(request: Request, action: str = Form(...), item_name: str = Form(...)): # request:Request accesses headers & cookies while the Form(...) tells FastAPI value must come from a form field
    for category in items:
        for item in category['items']: # Loops through each item within the current category
            if item['name'] == item_name: # If the item's name macthes submitted form value
                 # Updates item's count based on the action
                if action == 'increment':
                    item['count'] += 1 
                elif action == 'decrement':
                    item['count'] = max(0, item['count'] - 1)
                
                # Recalculates the total CO2 savings for the item using base_co2 as the fixed value and co2 as the updated total
                item['co2'] = item['count'] * item['base_co2']
                break # Stops searching once the item is found and updates it

    # Redirects back to homepage after form submission to display updated data & to prevent resubission on refresh
    return RedirectResponse(url="/", status_code=303)

# Route to reset all items locally
@app.post("/reset", response_class=HTMLResponse)
def renew(request: Request):
    # Resets locally displayed items
    for category in items:
        for item in category['items']:
            item['count'] = 0 # Resets local count to 0
            item['co2'] = 0 # Resets local CO2 to 0  

    return RedirectResponse(url="/", status_code=303) # Redirects back to demo page

# Route for the homepage ('/main') that returns an HTML response displaying items
@app.get("/main", response_class=HTMLResponse)
def main(request: Request):

    # Personalized welcome text initialization
    user_name = request.cookies.get("user_name")
    welcome_message = request.cookies.get("welcome_message")

    global total_co2

    # Calculates the total CO2 emission based on item's counts and CO2 per item
    total_co2 = sum(
        (item.get('co2', 0))
        for category in items
        for item in category['items'])
    
    equivalents = AppUtils.calculate_equivalents(total_co2)  # Calculates how mmuch C02 is equivalent to driving a car, riding a bus or flying in a plane using the AppUtils calculate session function
    totals, session_count = AppUtils.calculate_total(mongo.get_all_sessions()) # Gets All Sessions Function loops through all stored sessions in the Database, then passes them to AppUtils, calculates total function to calculate cumulative totals and number of sessions
    updated_items = mongo.get_updated_items() # Fetches the latest items data from the MongoDB database
    rearranged_items = AppUtils.rearrange_updated_items(updated_items)  # Single Lists MongoDB items
    sorted_items = AppUtils.sort_updated_items(rearranged_items) # Sorts items by 'count' in descending order with most used items coming first

    context = {
        "request": request, # Passes the request for Jinja2 to access
        "items": items,  # Passes items data to be rendered
        "equivalents": equivalents, # C02 equivalent in different modes of transport
        "total_co2": total_co2, # Total C02 emitted based on selected items
        "totals": totals, # Cumulative totals of all sessions
        "session_count": session_count,  # Number of sessions stored
        "sorted_items": sorted_items, # Sorted list of updated items for display
        "welcome_message": welcome_message # Displays welcome text
    }
    # Renders the response
    response = templates.TemplateResponse("main.html", context)

    # Clears welcome text after first display
    if welcome_message:
        response.delete_cookie("welcome_message")
    return response 

# Route to handle form submissions of incrementing & decrementing counts
@app.post("/main", response_class=HTMLResponse)
def update_count(request: Request, action: str = Form(...), item_name: str = Form(...)): # request:Request accesses headers & cookies while the Form(...) tells FastAPI value must come from a form field
    for category in items:
        for item in category['items']: # Loops through each item within the current category
            if item['name'] == item_name: # If the item's name macthes submitted form value
                 # Updates item's count based on the action
                if action == 'increment':
                    item['count'] += 1 
                elif action == 'decrement':
                    item['count'] = max(0, item['count'] - 1)
                
                # Recalculates the total CO2 savings for the item using base_co2 as the fixed value and co2 as the updated total
                item['co2'] = item['count'] * item['base_co2']
                break # Stops searching once the item is found and updates it

    # Redirects back to homepage after form submission to display updated data & to prevent resubission on refresh
    return RedirectResponse(url="/main", status_code=303)

# Route to save items data to database and reset all items locally
@app.post("/main/reset", response_class=HTMLResponse)
def renew(request: Request):
    # Saves all items data from session to database before resetting
    try:
        exc_items = {} 

        # Update items and collects exchanged items
        for category in items:
            for item in category['items']:
                if item.get('count', 0) > 0 or item.get('co2', 0) > 0: # Tries to get 'CO2', if it doesn't exist, it returns 0 instead , to prevent crashes
                    mongo.update_item(category["category"], item["name"], item['count'], item['co2']) # Updates items count and CO2 by category using the MongoCO2 class defined function
                    
                    # Ensures a list exists for each category
                    if category['category'] not in exc_items:
                        exc_items[category["category"]] = []
                    
                    exc_items[category["category"]].append({
                        "name": item["name"],
                        "count": item["count"],
                        "co2": item["co2"]
                    })

        if total_co2 > 0:
            equivalents = AppUtils.calculate_equivalents(total_co2)  # Calculates how much C02 is equivalent to driving a car, riding a bus or flying in a plane using the AppUtils calculate session function
            mongo.insert_session(total_co2, equivalents, exc_items) # Inserts exchanged items and sessions for a participant

        # Resets locally displayed items
        for category in items:
            for item in category['items']:
                item['count'] = 0 # Resets local count to 0
                item['co2'] = 0 # Resets local CO2 to 0  

    except Exception as e:
        print(f"Error in /reset: {e}")
        raise e
    
    return RedirectResponse(url="/main", status_code=303) # Redirects back to mainpage

# Route to save events data to database and reset all items locally
@app.post("/main/logout", response_class=HTMLResponse)
def logout(request: Request):

    user_name = request.cookies.get("user_name") # Uses cookie to get user name

    # Checks if there were actual calculations during sessions
    totals, session_count = AppUtils.calculate_total(mongo.get_all_sessions()) # Gets All Sessions Function loops through all stored sessions in the Database, then passes them to AppUtils, calculates total function to calculate cumulative totals and number of sessions

    # If data was exchanged during the event, then its collected and saved into the logs event collection
    if session_count > 0:
        updated_items = mongo.get_updated_items() # Fetches the latest items data from the MongoDB database
        rearranged_items = AppUtils.rearrange_updated_items(updated_items)  # Single Lists MongoDB items
        sorted_items = AppUtils.sort_updated_items(rearranged_items) # Sorts items by 'count' in descending order with most used items coming first
        mongo.log_out(user_name, sessions=session_count, sorted_items=sorted_items, total=totals)
        mongo.reset_counts(items) # Resets items database count 
        mongo.clear_sessions() # Deletes all documents inside the sessions collection

    # Prepares redirect response and clears the cookie
    response = RedirectResponse(url="/", status_code=303) 
    response.delete_cookie("user_name") # Clears cookie
    return response # Redirects to landing page 
    
# SECURE ROUTES
# Route to reset item counts in database to zero
@app.get("/main/reset_DBS", response_class=HTMLResponse)
def reset_count(request: Request):
    mongo.reset_counts(items)
    return RedirectResponse(url="/main", status_code=303) # Redirects back to homepage after resetting counts

# Route to clear all exchange sessions from the database
@app.get("/main/clear_SOS", response_class=HTMLResponse)
def clear_sessions(request: Request):
    mongo.clear_sessions() # Deletes all documents inside the sessions collection
    return RedirectResponse(url="/main", status_code=303) # Redirects back to homepage after clearing sessions