import geocoder
from geopy import Nominatim
import requests
import datetime
import time
import sqlite3
from os.path import expanduser


def query_database():
    knowledge_db = expanduser("~/Library/Application Support/Knowledge/knowledgeC.db")
    with sqlite3.connect(knowledge_db) as con:
        cur = con.cursor()

        query = """
        SELECT
            ZOBJECT.ZVALUESTRING AS "app", 
            (ZOBJECT.ZENDDATE - ZOBJECT.ZSTARTDATE) AS "usage",
            (ZOBJECT.ZSTARTDATE + 978307200) as "start_time", 
            (ZOBJECT.ZENDDATE + 978307200) as "end_time",
            (ZOBJECT.ZCREATIONDATE + 978307200) as "created_at", 
            ZOBJECT.ZSECONDSFROMGMT AS "tz",
            ZSOURCE.ZDEVICEID AS "device_id",
            ZMODEL AS "device_model"
        FROM
            ZOBJECT 
            LEFT JOIN
            ZSTRUCTUREDMETADATA 
            ON ZOBJECT.ZSTRUCTUREDMETADATA = ZSTRUCTUREDMETADATA.Z_PK 
            LEFT JOIN
            ZSOURCE 
            ON ZOBJECT.ZSOURCE = ZSOURCE.Z_PK 
            LEFT JOIN
            ZSYNCPEER
            ON ZSOURCE.ZDEVICEID = ZSYNCPEER.ZDEVICEID
        WHERE
            ZSTREAMNAME = "/app/usage"
        ORDER BY
            ZSTARTDATE DESC
        """
        cur.execute(query)

        return cur.fetchall()


class Entry:
    def __init__(self, message, feeling, rating):
        self.message = message
        self.feeling = feeling
        self.rating = rating

        g = geocoder.ip('me')
        self.location = str(g.latlng)
        self.lat = round(g.lat, 2)
        self.lng = round(g.lng, 2)
        geolocator = Nominatim(user_agent="pydiary")
        location = geolocator.reverse(g.latlng)
        if 'address' in location.raw:
            address = location.raw['address']
            self.location_name = address.get('city', '')
        else:
            self.location_name = "Not found"

        r = requests.get(f"https://api.open-meteo.com/v1/forecast?"
                         f"latitude={self.lat}"
                         f"&longitude={self.lng}"
                         f"&hourly=temperature_2m,cloud_cover"
                         f"&timezone=auto")
        self.temp = r.json()["hourly"]["temperature_2m"][0]
        self.cloud_cover = r.json()["hourly"]["cloud_cover"][0]

        self.date = datetime.datetime.date(datetime.datetime.now())
        self.time = datetime.datetime.now()

        self.day_screentime = 0
        self.day_communication = 0
        self.day_audio = 0
        self.day_productive = 0
        self.day_other = 0

        for i in query_database():
            if i[2] > time.mktime(self.date.timetuple()) + 25200:
                self.day_screentime += i[1]
                if (i[0] == 'com.hnc.Discord'
                        or i[0] == 'com.apple.MobileSMS'):
                    self.day_communication += i[1]
                elif (i[0] == 'com.apple.Music'
                      or i[0] == 'com.apple.podcasts'):
                    self.day_audio += i[1]
                elif (i[0] == 'com.jetbrains.pycharm.ce'
                      or i[0] == 'com.microsoft.VSCode'
                      or i[0] == 'org.blenderfoundation.blender'):
                    self.day_productive += i[1]
                else:
                    self.day_other += i[1]


def add_entry(content, feeling, rating,):
    print("Writing entry to database.")
    conn4 = sqlite3.connect("diary.db")
    cursor4 = conn4.cursor()
    entry = Entry(content, feeling, rating)
    cursor4.execute("INSERT INTO entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (entry.message, entry.feeling, entry.rating,
                     entry.location, str(entry.date), str(entry.time),
                     entry.day_screentime, entry.day_communication, entry.day_audio,
                     entry.day_productive, entry.day_other,
                     entry.temp, entry.cloud_cover, entry.location_name))
    conn4.commit()
    conn4.close()


def get_entries_for_data(data_type, operator, value):
    conn2 = sqlite3.connect('diary.db')
    cursor2 = conn2.cursor()

    cursor2.execute(f"SELECT * FROM entries WHERE {data_type}{operator}?", (value,))
    entries = cursor2.fetchall()

    conn2.close()
    return entries


def get_entries_containing(string):
    conn2 = sqlite3.connect('diary.db')
    cursor2 = conn2.cursor()

    cursor2.execute(f"SELECT * FROM entries WHERE instr(message, ?) > 0;", (string,))
    entries = cursor2.fetchall()

    conn2.close()
    return entries


def nice_display(entries):
    for entry in entries:
        print("Message: ", entry[0])
        print("Feeling: ", entry[1])
        print("Rating: ", entry[2])
        print("Date/time: ", entry[5])
        print("Location: ", entry[13])
        print("Location Coordinates: ", entry[3])
        print("Weather: ", entry[11])
        print("Cloud cover: ", entry[12])
        print("Day Screen Time: ", datetime.timedelta(seconds=entry[6]))
        print("Day Communication: ", datetime.timedelta(seconds=entry[7]))
        print("Day Audio: ", datetime.timedelta(seconds=entry[8]))
        print("Day Productive: ", datetime.timedelta(seconds=entry[9]))
        print("Day Other: ", datetime.timedelta(seconds=entry[10]))
        print("\n-------------------\n")


def get_sec(time_str):
    h, m, s = time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)


def main():
    conn = sqlite3.connect("diary.db")
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE if NOT EXISTS entries
    (message TEXT, feeling TEXT, rating INTEGER, location TEXT, date TEXT, time TEXT, day_screentime INTEGER,
    day_communication INTEGER, day_audio INTEGER, day_productive INTEGER, day_other INTEGER, 
    temp INTEGER, cloud_cover INTEGER, location_name TEXT)
    ''')
    conn.commit()
    conn.close()
    
    while True:
        print("1. Write")
        print("2. Read")
        print("3. Exit")
        ans = input()
        if ans == "1":
            print("(x to cancel)")
            print("MESSAGE:")
            ans = input()
            if ans == "x":
                continue
            else:
                message = ans
            print("FEELING:")
            ans = input()
            if ans == "x":
                continue
            else:
                feeling = ans
            print("RATING:")
            ans = input()
            if ans == "x":
                continue
            else:
                rating = ans
            add_entry(message, feeling, rating)
        elif ans == "2":
            print("1. Search by data")
            print("2. Search by string")
            print("3. Show all")
            ans = input()
            if ans == "1":
                print("Input data type. (text input)")
                print("message")
                print("feeling")
                print("rating")
                print("time")
                print("date")
                print("temperature")
                print("cloud_cover")
                print("location")
                print("location_name")
                print("day_screen_time")
                print("day_communication")
                print("day_audio")
                print("day_productive")
                print("day_other")
                data_type = str.casefold(input())
                if ":" in data_type and "-" not in data_type:
                    data_type = get_sec(data_type)
                print("Input operator. (text input)")
                print("<")
                print("=")
                print(">")
                print("etc.")
                operator = str.casefold(input())
                print("Input value.")
                value = input()
                nice_display(get_entries_for_data(data_type, operator, value))
            elif ans == "2":
                print("Search all entries containing string:")
                ans = input()
                nice_display(get_entries_containing(ans))
            else:
                conn3 = sqlite3.connect('diary.db')
                c = conn3.cursor()
                c.execute("SELECT * FROM entries")
                entries = c.fetchall()
                nice_display(entries)
                conn3.close()
        else:
            break


if __name__ == "__main__":
    main()
