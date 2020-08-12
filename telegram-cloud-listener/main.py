#!/usr/bin/env python
# coding: utf-8

import os, re, hashlib, datetime, logging
import telebot

import google.auth
from googleapiclient.discovery import build


sheet_credentials, project = google.auth.default(scopes=['https://www.googleapis.com/auth/spreadsheets'])
service = build('sheets', 'v4', cache_discovery=False)
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CHAT_ID = os.getenv("CHAT_ID")

bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_KEY"))

def write_google_sheet_col_headers(latest_tracker_message):
    spreadsheet_id = os.getenv("SPREADSHEET_ID")
    end_col = chr(ord('a') + len(latest_tracker_message)).upper()
    range_name = 'Sheet1!A1:{}1'.format(end_col)
    response = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    if not response.get("values"):
        body = {"values":latest_tracker_message.keys()}
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id, range=range_name,
            valueInputOption="USER_ENTERED",
            body=body).execute()
        logging.info("COLUMN HEADERS FIRST WRITE TO SPREADSHEET {}".format(spreadsheet_id))



def update_google_sheet_tracker(latest_tracker_message):
    tracker_message_arr = [[v for k,v in latest_tracker_message.items() if k!="attributes"]]
    range_name = "Sheet1"
    write_google_sheet_col_headers(latest_tracker_message)
    update_google_sheet_with_message(tracker_message_arr, range_name)

def update_google_sheet_with_message(values_as_arr, range_name): 
    # values = [
    # [
    #     # Cell values ...
    # ],
    # # Additional rows ...
    # ]
    body = {
        'values': values_as_arr
    }
    spreadsheet_id = os.getenv("SPREADSHEET_ID")

    result = service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id, range=range_name,
        valueInputOption="USER_ENTERED",
        body=body).execute()
    logging.info('{0} cells appended.'.format(result \
                                        .get('updates') \
                                        .get('updatedCells')))


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):

    bot.reply_to(message, u"Congats! You've made your first bot!")

#@bot.message_handler(regexp=command_regex_config["tracker"])
@bot.message_handler(commands=["t","track","tracker"])
def tracker_message_handler(message):
    

    from_user = message.from_user
    chat_info = message.chat
    if chat_info.chat_id == CHAT_ID:
        
        dash_message_id = str(datetime.datetime.now()) + str(from_user.id)
        dash_message_id = hashlib.md5(dash_message_id.encode('utf-8')).hexdigest()
        
        latest_tracker_message =   {
                            "message_id": dash_message_id,
                            "chat_id":chat_info.id,
                            "type": "tracker",
                            "status": "Unassigned",
                            "title": "Unassigned",
                            "user_id":from_user.id,
                            "user_name":"{} {}".format(from_user.first_name,from_user.last_name),
                            "datetime_logged":str(datetime.datetime.now()),
                            "message_date":message.date,
                            "input_datetime":str(datetime.datetime.now()), 
                            "content": "Unassigned",
                            "magnitude":30, 
                            "units":"$",
                            "estimate": "NA"
                        }

        
        regexp = re.compile(r"(\$[0-9]?[0-9]\.?[0-9]?[0-9]?)|[0-9]?[0-9]\.[0-9][0-9]", flags=re.IGNORECASE)
        regex_search_result = regexp.search(message.text) 

        if regex_search_result:

            latest_tracker_message["status"] = "Spend"
            magnitude = regex_search_result.group(1)
            try:
                latest_tracker_message["magnitude"] = float(re.sub("[a-z]|[A-Z]|\\$","",magnitude))
                latest_tracker_message["estimate"] = "$ {}".format(re.sub("[a-z]|[A-Z]|\\$","",magnitude))

            except Exception as e:
                print(e)

            description = message.text.replace(magnitude, "").replace("/t",'').strip()

            latest_tracker_message["title"] = description
            latest_tracker_message["content"] = description
                
            update_google_sheet_tracker(latest_tracker_message)
            bot.reply_to(message, "Great! I've logged that amount for you")
    else: 
        pass
        #TODO set up some logic here to send a notification on GCP that someone else is messaging your bot               



def process_telegram_messages(req):
    #bot.set_webhook(url=WEBHOOK)
    request_body_dict = req.get_json()
    update = telebot.types.Update.de_json(request_body_dict)
    bot.process_new_messages([update.message])