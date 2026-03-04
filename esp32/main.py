from machine import Pin, SoftI2C
import dht
import time
import ssd1306
import network
import socket
import json
import urequests
from config import NETWORKS, API_URL
import ntptime

wifi = network.WLAN(network.STA_IF)
wifi.active(False)
time.sleep(1)
wifi.active(True)
time.sleep(1)

connected = False
for ssid, password in NETWORKS:
    print("Próbuję:", ssid)
    wifi.disconnect()
    time.sleep(0.5)
    wifi.connect(ssid, password)
    for _ in range(40):
        if wifi.isconnected():
            connected = True
            break
        time.sleep(0.5)
    if connected:
        print("Połączono z:", ssid)
        break

if connected:
    ip = wifi.ifconfig()[0]
    print("IP:", ip)
    try:
        ntptime.settime()
    except:
        print("NTP failed")
else:
    ip = "brak WiFi"
    print("Brak WiFi!")

i2c = SoftI2C(scl=Pin(22), sda=Pin(23))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
oled.text("Inicjalizacja...", 0, 0)
oled.show()

sensor = dht.DHT11(Pin(32))
sensor.measure()
print(sensor.temperature())

def read_sensor():
    sensor.measure()
    temp = sensor.temperature()
    hum = sensor.humidity()
    return temp, hum

def draw_degree(x, y):
    oled.pixel(x,   y,   1)
    oled.pixel(x+1, y,   1)
    oled.pixel(x,   y+1, 1)
    oled.pixel(x+1, y+1, 1)

def show_data(temp, hum, send_ok=False):
    oled.fill(0)
    oled.text("Temp:", 0, 0)
    temp_str = "{:.1f} ".format(temp)
    oled.text(temp_str, 40, 0)
    draw_degree(40 + len(temp_str) * 8, 0)
    oled.text("C", 40 + len(temp_str) * 8 + 6, 0)

    oled.text("Wilg:", 0, 20)
    oled.text("{:.0f}%".format(hum), 40, 20)

    status = "Online" if send_ok else "Offline"
    oled.text(status, 0, 50)
    oled.show()

def send_data(temp, hum):
    try:
        t = time.localtime()
        hour = (t[3] + 1) % 24
        timestamp = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
            t[0], t[1], t[2], hour, t[4], t[5]
        )
        data = json.dumps({
            "temperature": round(temp, 1),
            "humidity": round(hum, 1),
            "timestamp": timestamp
        })
        urequests.post(
            API_URL,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        return True
    except Exception as e:
        print("Błąd wysyłania:", e)
        return False

server = socket.socket()
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('', 80))
server.listen(5)
server.setblocking(False)
print("Serwer działa!")

last_read = 0
temp, hum = 0, 0

# --- Główna pętla ---
while True:
    if time.ticks_diff(time.ticks_ms(), last_read) > 60000:
        try:
            temp, hum = read_sensor()
            send_ok = send_data(temp, hum)
            show_data(temp, hum, send_ok)
            print("Temp: {:.1f}C  Wilg: {:.0f}%".format(temp, hum))
        except Exception as e:
            print("Błąd odczytu:", e)
        last_read = time.ticks_ms()

    try:
        conn, addr = server.accept()
        request = conn.recv(1024).decode()
        if "GET /temperature" in request:
            body = json.dumps({
                "temperature": temp,
                "humidity": hum,
                "unit": "C"
            })
            response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\n\r\n" + body
        else:
            response = "HTTP/1.1 404 Not Found\r\n\r\n"
        conn.send(response)
        conn.close()
    except:
        pass
