import smtplib
from email.message import EmailMessage
from twilio.rest import Client
import paho.mqtt.client as mqtt  #For MQTT communication
import sqlite3  #For database operations
import time  #For time-related functions
import datetime  #For timestamp handling

#email config
EMAIL_ADDRESS = "x"
EMAIL_PASSWORD = "x"
EMAIL_RECIPIENT = "x"
#SMS credentials (twilio)
ACCOUNT_SID =  x
AUTH_TOKEN = x
TWILIO_NUMBER = x   #TWILIO phone number
TARGET_NUMBER = x  #target

#MQTT broker configuration settings
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
#MQTT topics for verification process
MQTT_TOPIC_VERIFY = "passcodes/verify"
MQTT_TOPIC_ID = "passcodes/id"
MQTT_TOPIC_RESULT = "passcodes/result"
#MQTT topics for registration process
MQTT_TOPIC_REGISTER_PASSCODE = "passcodes/registerPassCode"
MQTT_TOPIC_REGISTER_RESULT = "passcodes/registerResult"

#database filename
DB_FILE = "passcodes.db"

current_id = None  #stores the current ID for verification

def sendEmail(user_id, timestamp):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM passcodes WHERE id = ?", (user_id,))
    result = cursor.fetchone()[0]
    conn.close()

    msg = EmailMessage()
    msg.set_content(f"{result} entered the house at {timestamp}.")
    msg['Subject'] = 'House entry notification'
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = EMAIL_RECIPIENT

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
            print(f"[EMAIL] notification sent for ID {result}")
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send notification: {e}")

def sendSms(user_id, timestamp):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM passcodes WHERE id = ?", (user_id,))
    result = cursor.fetchone()[0]
    conn.close()

    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    message = client.messages.create(
        body=f"{result} entered the house at {timestamp}",
        from_=TWILIO_NUMBER,
        to=TARGET_NUMBER
    )
    print(f"[TWILIO] SMS sent: SID {message.sid}")

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    #subscribe to verification topics
    client.subscribe(MQTT_TOPIC_VERIFY)
    client.subscribe(MQTT_TOPIC_ID)
    #subscribe to registration topic
    client.subscribe(MQTT_TOPIC_REGISTER_PASSCODE)

def on_message(client, userdata, msg):
    global current_id
    try:
        topic = msg.topic
        payload = msg.payload.decode()

        #handle ID message for verification
        if topic == MQTT_TOPIC_ID:
            received_id = int(payload)
            if 1 <= received_id <= 127:
                current_id = received_id
                print(f"Received ID: {current_id}")
            else:
                print(f"Invalid ID received: {received_id}")
        #handle verification message (when a passcode is sent for verification)
        elif topic == MQTT_TOPIC_VERIFY:
            passcode_to_verify = payload
            #check if both passcode and ID are available
            if passcode_to_verify and current_id is not None:
                print(f"Verifying passcode: {passcode_to_verify} for ID: {current_id}")
                #open database connection
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                #retrieve the stored passcode for the given user ID
                cursor.execute("SELECT passcode FROM passcodes WHERE id = ?", (current_id,))
                result = cursor.fetchone()

                if result:
                    #extract stored passcodee
                    stored_passcode = result[0]
                    #Compare the received passcode with the stored one
                    is_match = (passcode_to_verify == stored_passcode)
                    #Publish the verification result (true/false) 
                    client.publish(MQTT_TOPIC_RESULT, "true" if is_match else "false")
                    print(f"Passcode match for ID {current_id}: {is_match}")
                    if is_match:
                        #If passcode matches, update lastAccess timestamp
                        current_time = datetime.datetime.now().strftime("%H:%M:%S %Y-%m-%d")
                        cursor.execute("UPDATE passcodes SET lastAccess = ? WHERE id = ?", (current_time, current_id))
                        conn.commit()
                        print(f"Updated lastAccess timestamp for ID {current_id} to {current_time}")
                        #Send email and SMS notifications
                        sendEmail(current_id, current_time)
                        sendSms(current_id, current_time)
                else:
                    #ID exists in memory, but not found in database
                    client.publish(MQTT_TOPIC_RESULT, "false")
                    print(f"No passcode found for ID {current_id}")
                #Close database connection
                conn.close()
            elif current_id is None:
                #No ID was set prior to passcode being sent
                client.publish(MQTT_TOPIC_RESULT, "false")
                print("Verification attempted without setting ID first")
            elif not passcode_to_verify:
                #Passcode received was empty
                client.publish(MQTT_TOPIC_RESULT, "false")
                print("No passcode provided for verification")

        #handle registration passcode message (when a new passcode needs to be registered)
        elif topic == MQTT_TOPIC_REGISTER_PASSCODE:
            passcode_to_register = payload
            if passcode_to_register:
                print(f"Registering new passcode")
                #open database connection
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                try:
                    #find the current maximum ID in the database
                    cursor.execute("SELECT MAX(id) FROM passcodes")
                    max_id = cursor.fetchone()[0]
                    #Assign next available ID
                    new_id = 1 if max_id is None else max_id + 1
                    #Insert new user with passcode, created, and lastAccess timestamps (name is set by default to null)
                    cursor.execute("""
                        INSERT INTO passcodes (id, passcode, created, lastAccess) 
                        VALUES (?, ?, ?, ?)
                    """, (new_id, passcode_to_register, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                          datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
                    print(f"Registered new ID {new_id} with passcode")
                    #Notify registration success via MQTT
                    client.publish(MQTT_TOPIC_REGISTER_RESULT, f"true")
                    print(f"sucess")
                except sqlite3.Error as e:
                    #handle SQLite errors
                    print(f"Database error during registration: {e}")
                    client.publish(MQTT_TOPIC_REGISTER_RESULT, f"false:database_error")
                finally:
                 
                    conn.close()
            else:
                #empty or invalid
                client.publish(MQTT_TOPIC_REGISTER_RESULT, "false:empty_passcode")
                print("Empty passcode provided for registration")

    
    except Exception as e:
        print(f"Error processing message: {e}")
        #Fallback MQTT failure response for different scenarios
        if topic.startswith("passcodes/verify"):
            client.publish(MQTT_TOPIC_RESULT, "false")
        elif topic.startswith("passcodes/register"):
            client.publish(MQTT_TOPIC_REGISTER_RESULT, f"false:error_{str(e)}")

def main():
    #configure MQTT client
    client = mqtt.Client()
    client.on_connect = on_connect  #set connect callback
    client.on_message = on_message  #set message callback

    try:
        #client.tls_set(ca_certs="/etc/mosquitto/certs/ca.crt")

        #connect to local MQTT broker
        client.connect(MQTT_BROKER, MQTT_PORT, 60)  #60 is the keepalive interval (in seconds)
        print("Starting MQTT verification service...")
        #loops infinitely to process incoming messages 
        client.loop_forever()
    except Exception as e:
        print(f"Failed to connect to MQTT broker: {e}")

#entry point of the script
if __name__ == "__main__":
    main()
